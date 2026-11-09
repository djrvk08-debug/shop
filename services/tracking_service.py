"""Shipment tracking service managing carrier logistics, delivery rules, and timeline events."""
from datetime import datetime
from datetime import timedelta, timezone
from typing import Any
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from extensions import db
from models import Order, Shipment, TrackingEvent

# State machine defining valid delivery progression transitions
DELIVERY_STATUS_TRANSITIONS: dict[str, list[str]] = {
    "pending": ["harvested", "picked_up", "cancelled"],
    "harvested": ["dispatched", "picked_up", "cancelled"],
    "dispatched": ["in_transit", "out_for_delivery", "failed_attempt", "exception", "delivered"],
    "picked_up": ["in_transit", "cancelled"],
    "in_transit": ["out_for_delivery", "failed_attempt", "exception"],
    "failed_attempt": ["in_transit", "returned_to_sender"],
    "exception": ["in_transit", "returned_to_sender"],
    "out_for_delivery": ["delivered", "failed_attempt"],
    "delivered": [],
    "returned_to_sender": [],
    "cancelled": [],
}


def get_milestones(shipment: Any) -> list[dict[str, Any]]:
    """Return harvested, dispatched, and delivered milestones for a shipment."""
    reached_statuses = {event.status for event in shipment.events}
    reached_statuses.add(shipment.status)
    harvested = bool(reached_statuses & {
        "harvested", "dispatched", "picked_up", "in_transit", "out_for_delivery",
        "failed_attempt", "exception", "delivered",
    })
    dispatched = bool(reached_statuses & {
        "dispatched", "picked_up", "in_transit", "out_for_delivery", "failed_attempt",
        "exception", "delivered",
    })
    delivered = "delivered" in reached_statuses
    complete = [harvested, dispatched, delivered]
    stopped = shipment.status in {"pending", "cancelled", "returned_to_sender"}
    current_index = None if stopped else next((i for i, is_done in enumerate(complete) if not is_done), 2)
    return [
        {"label": label, "complete": is_done, "current": index == current_index}
        for index, (label, is_done) in enumerate(zip(("Harvested", "Dispatched", "Delivered"), complete))
    ]


def create_shipment(
    order_id: int, carrier: str, tracking_number: str, eta: datetime | None = None
) -> Any:
    """Create a new shipment record for an existing order.

    :param order_id: Associated order ID.
    :param carrier: Name of the logistics carrier (e.g. FedEx, UPS, DHL).
    :param tracking_number: Unique tracking barcode/number.
    :param eta: Estimated arrival date/time.
    :return: Created Shipment model instance.
    :raises ValueError: If tracking_number is not unique or order already has a shipment.
    """
    carrier = carrier.strip() if isinstance(carrier, str) else ""
    tracking_number = tracking_number.strip() if isinstance(tracking_number, str) else ""
    if not carrier or len(carrier) > 100:
        raise ValueError("A valid carrier is required.")
    if not tracking_number or len(tracking_number) > 100:
        raise ValueError("A valid tracking number is required.")
    order = db.session.get(Order, order_id)
    if order is None or order.status not in {"pending", "paid", "processing"}:
        raise ValueError("Shipment requires an existing open order.")
    if Shipment.query.filter_by(order_id=order_id).first():
        raise ValueError("This order already has a shipment.")
    if Shipment.query.filter_by(tracking_number=tracking_number).first():
        raise ValueError("Tracking number is already in use.")
    shipment = Shipment(order_id=order_id, carrier=carrier, tracking_number=tracking_number,
                        status="pending", eta=eta)
    db.session.add(shipment)
    db.session.flush()
    db.session.add(TrackingEvent(shipment_id=shipment.id, status="pending", note="Shipment created"))
    if shipment.eta is None:
        shipment.eta = calculate_eta(shipment.id)
    try:
        db.session.commit()
    except IntegrityError as error:
        db.session.rollback()
        raise ValueError("Tracking number is already in use.") from error
    return shipment


def add_event(
    tracking_number: str, status: str, location: str | None = None, note: str | None = None
) -> Any:
    """Append a checkpoint event to a shipment timeline, rejecting duplicates and invalid status moves.

    :param tracking_number: Unique carrier tracking code.
    :param status: New delivery status being reported.
    :param location: Optional checkpoint location (e.g. City, State).
    :param note: Optional context or carrier status description.
    :return: Created TrackingEvent instance.
    :raises ValueError: If shipment not found, status move invalid, or identical event is duplicate.
    """
    if not isinstance(status, str) or status not in DELIVERY_STATUS_TRANSITIONS:
        raise ValueError("Invalid shipment status.")
    shipment = Shipment.query.filter_by(tracking_number=tracking_number).first()
    if shipment is None:
        raise ValueError("Shipment not found.")
    if status not in DELIVERY_STATUS_TRANSITIONS[shipment.status]:
        raise ValueError(f"Invalid shipment status transition: {shipment.status} to {status}.")
    location = location.strip() if isinstance(location, str) else None
    note = note.strip() if isinstance(note, str) else None
    if location and len(location) > 255:
        raise ValueError("Location must be 255 characters or fewer.")
    if note and len(note) > 2000:
        raise ValueError("Note must be 2000 characters or fewer.")
    event = TrackingEvent(shipment_id=shipment.id, status=status,
                          location=location or None, note=note or None)
    shipment.status = status
    db.session.add(event)
    db.session.commit()
    if shipment.order.user:
        from services.notify_service import queue_notification
        queue_notification(
            recipient=shipment.order.user.email, channel="email",
            subject=f"Shipment {shipment.tracking_number} update",
            message=f"Shipment status is now {status.replace('_', ' ')}.",
            context={"tracking_number": shipment.tracking_number, "status": status},
            idempotency_key=f"shipment:{shipment.id}:status:{status}",
        )
    return event


def get_shipment_by_tracking(tracking_number: str) -> Any:
    """Look up shipment details along with chronological tracking events.

    :param tracking_number: Shipment tracking code.
    :return: Shipment model instance with events loaded.
    """
    return Shipment.query.options(selectinload(Shipment.events)).filter_by(
        tracking_number=tracking_number
    ).first()


def calculate_eta(shipment_id: int) -> datetime | None:
    """Recalculate or project expected delivery ETA based on checkpoint history and carrier.

    :param shipment_id: Primary key of the shipment.
    :return: Estimated arrival datetime or None.
    """
    shipment = db.session.get(Shipment, shipment_id)
    if shipment is None or shipment.status in {"delivered", "cancelled", "returned_to_sender"}:
        return None
    base = shipment.created_at or datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    estimates = {
        "pending": timedelta(days=3),
        "picked_up": timedelta(days=2),
        "in_transit": timedelta(days=1),
        "out_for_delivery": timedelta(hours=4),
        "failed_attempt": timedelta(days=1),
        "exception": timedelta(days=2),
    }
    return base + estimates.get(shipment.status, timedelta(days=2))
