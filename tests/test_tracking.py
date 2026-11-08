"""Unit and integration tests for logistics shipments and delivery tracking."""
import pytest
from services import tracking_service
from services.tracking_service import DELIVERY_STATUS_TRANSITIONS
from extensions import db
from models import Order, Shipment, User


def test_delivery_status_transitions_constants():
    """Verify delivery state machine transition rules dictionary is defined."""
    assert "pending" in DELIVERY_STATUS_TRANSITIONS
    assert "picked_up" in DELIVERY_STATUS_TRANSITIONS["pending"]
    assert "in_transit" in DELIVERY_STATUS_TRANSITIONS["picked_up"]
    assert "out_for_delivery" in DELIVERY_STATUS_TRANSITIONS["in_transit"]


def test_public_tracking_page_renders_cleanly(client):
    """Render a shipment loaded from persistent tracking records."""
    # Create an eligible order before registering its shipment.
    from flask import current_app
    app = current_app._get_current_object()
    with app.app_context():
        user = User(email="tracking-page@example.com")
        user.set_password("test-password")
        db.session.add(user)
        db.session.flush()
        order = Order(user_id=user.id, status="processing", total=0)
        db.session.add(order)
        db.session.commit()
        tracking_service.create_shipment(order.id, "Test Carrier", "TRK-TEST12345")

    response = client.get("/track/TRK-TEST12345")
    assert response.status_code == 200
    assert b"TRK-TEST12345" in response.data
    assert b"Test Carrier" in response.data


def test_tracking_events_validate_transitions_and_persist(app):
    with app.app_context():
        user = User(email="tracking-events@example.com")
        user.set_password("test-password")
        db.session.add(user)
        db.session.flush()
        order = Order(user_id=user.id, status="processing", total=0)
        db.session.add(order)
        db.session.commit()

        shipment = tracking_service.create_shipment(order.id, "FedEx", "TRK-100")
        assert shipment.status == "pending"
        assert shipment.eta is not None
        assert len(shipment.events) == 1
        with pytest.raises(ValueError, match="Invalid shipment status transition"):
            tracking_service.add_event("TRK-100", "in_transit")

        event = tracking_service.add_event("TRK-100", "picked_up", location="Farm")
        assert event.location == "Farm"
        assert tracking_service.get_shipment_by_tracking("TRK-100").status == "picked_up"
        with pytest.raises(ValueError, match="Invalid shipment status transition"):
            tracking_service.add_event("TRK-100", "picked_up")


def test_shipment_rejects_duplicate_tracking_and_order(app):
    with app.app_context():
        user = User(email="tracking-duplicate@example.com")
        user.set_password("test-password")
        db.session.add(user)
        db.session.flush()
        order = Order(user_id=user.id, status="paid", total=0)
        db.session.add(order)
        db.session.commit()
        tracking_service.create_shipment(order.id, "UPS", "TRK-DUP")
        with pytest.raises(ValueError, match="already has a shipment"):
            tracking_service.create_shipment(order.id, "UPS", "TRK-OTHER")
        another_order = Order(user_id=user.id, status="paid", total=0)
        db.session.add(another_order)
        db.session.commit()
        with pytest.raises(ValueError, match="already in use"):
            tracking_service.create_shipment(another_order.id, "UPS", "TRK-DUP")


def test_carrier_webhook_requires_token_and_validates_event(client, app):
    unauthorized = client.post("/webhook/carrier", json={
        "tracking_number": "TRK-MISSING", "status": "picked_up",
    })
    assert unauthorized.status_code == 401

    app.config["CARRIER_WEBHOOK_TOKEN"] = "test-token"
    invalid_event = client.post("/webhook/carrier", json={
        "tracking_number": "TRK-MISSING", "status": "picked_up",
    }, headers={"X-Carrier-Token": "test-token"})
    assert invalid_event.status_code == 400
