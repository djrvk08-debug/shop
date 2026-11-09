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


def test_tracking_links_open_the_combined_orders_page(client):
    """Legacy tracking links no longer open a separate tracking page."""
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

    client.post("/auth/login", data={
        "email": "tracking-page@example.com", "password": "test-password"
    })
    response = client.get("/track/TRK-TEST12345")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/track")
    response = client.get("/track")
    assert response.status_code == 200
    assert b"TRK-TEST12345" in response.data
    assert b"Order #" in response.data
    assert b"Pending" in response.data
    assert b"Delivery progress" not in response.data
    assert b"Track delivery" not in response.data


def test_legacy_navigation_tracking_number_opens_my_orders(client):
    response = client.get("/track/TRK-TEST12345")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/track")


def test_my_tracking_lists_only_the_signed_in_users_orders(client, app):
    with app.app_context():
        customer = User(email="my-tracking@example.com")
        customer.set_password("test-password")
        other_customer = User(email="other-tracking@example.com")
        other_customer.set_password("test-password")
        db.session.add_all([customer, other_customer])
        db.session.flush()
        own_order = Order(user_id=customer.id, status="pending", total=12)
        other_order = Order(user_id=other_customer.id, status="pending", total=99)
        db.session.add_all([own_order, other_order])
        db.session.commit()
        tracking_service.create_shipment(own_order.id, "Farm Delivery", "DF-MY-ORDER")
        tracking_service.create_shipment(other_order.id, "Farm Delivery", "DF-OTHER-ORDER")
        own_order_id = own_order.id
        other_order_id = other_order.id

    client.post("/auth/login", data={
        "email": "my-tracking@example.com", "password": "test-password"
    })
    response = client.get("/track")
    assert response.status_code == 200
    assert f"Order #{own_order_id}".encode() in response.data
    assert b"DF-MY-ORDER" in response.data
    assert f"Order #{other_order_id}".encode() not in response.data
    assert b"DF-OTHER-ORDER" not in response.data


def test_shipment_milestones_advance_from_harvested_to_delivered(app):
    with app.app_context():
        user = User(email="milestone-tracking@example.com")
        user.set_password("test-password")
        db.session.add(user)
        db.session.flush()
        order = Order(user_id=user.id, status="processing", total=0)
        db.session.add(order)
        db.session.commit()

        tracking_service.create_shipment(order.id, "Farm Delivery", "TRK-MILESTONES")
        shipment = tracking_service.get_shipment_by_tracking("TRK-MILESTONES")
        assert [step["current"] for step in tracking_service.get_milestones(shipment)] == [False, False, False]

        tracking_service.add_event("TRK-MILESTONES", "harvested", location="Dharti Farm")
        shipment = tracking_service.get_shipment_by_tracking("TRK-MILESTONES")
        assert [step["complete"] for step in tracking_service.get_milestones(shipment)] == [True, False, False]
        assert [step["current"] for step in tracking_service.get_milestones(shipment)] == [False, True, False]

        tracking_service.add_event("TRK-MILESTONES", "dispatched", location="Farm dispatch")
        shipment = tracking_service.get_shipment_by_tracking("TRK-MILESTONES")
        assert [step["complete"] for step in tracking_service.get_milestones(shipment)] == [True, True, False]
        assert [step["current"] for step in tracking_service.get_milestones(shipment)] == [False, False, True]

        tracking_service.add_event("TRK-MILESTONES", "delivered", location="Customer")
        shipment = tracking_service.get_shipment_by_tracking("TRK-MILESTONES")
        assert [step["complete"] for step in tracking_service.get_milestones(shipment)] == [True, True, True]


def test_admin_can_update_customer_visible_milestones(client, app):
    with app.app_context():
        user = User(email="shipment-admin@example.com", is_admin=True)
        user.set_password("test-password")
        db.session.add(user)
        db.session.flush()
        order = Order(user_id=user.id, status="processing", total=0)
        db.session.add(order)
        db.session.commit()
        shipment = tracking_service.create_shipment(order.id, "Farm Delivery", "TRK-ADMIN-MILESTONES")
        shipment_id = shipment.id

    client.post("/auth/login", data={
        "email": "shipment-admin@example.com", "password": "test-password"
    })
    for status in ("harvested", "dispatched", "delivered"):
        response = client.post(f"/admin/shipments/{shipment_id}/status", data={"status": status})
        assert response.status_code == 302

    redirect_response = client.get("/track/TRK-ADMIN-MILESTONES")
    assert redirect_response.status_code == 302
    tracking_page = client.get("/track")
    assert tracking_page.status_code == 200
    assert b"Delivered" in tracking_page.data
    assert b"Delivered" in tracking_page.data


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
