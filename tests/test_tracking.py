"""Unit and integration tests for logistics shipments and delivery tracking."""
import pytest
from services import tracking_service
from services.tracking_service import DELIVERY_STATUS_TRANSITIONS


def test_delivery_status_transitions_constants():
    """Verify delivery state machine transition rules dictionary is defined."""
    assert "pending" in DELIVERY_STATUS_TRANSITIONS
    assert "picked_up" in DELIVERY_STATUS_TRANSITIONS["pending"]
    assert "in_transit" in DELIVERY_STATUS_TRANSITIONS["picked_up"]
    assert "out_for_delivery" in DELIVERY_STATUS_TRANSITIONS["in_transit"]


def test_public_tracking_page_renders_cleanly(client):
    """Confirm the public tracking lookup page returns HTTP 200."""
    response = client.get("/track/TRK-TEST12345")
    assert response.status_code == 200
    assert b"TRK-TEST12345" in response.data


def test_tracking_service_stubs_raise_not_implemented():
    """Verify tracking service stubs raise NotImplementedError prior to implementation."""
    # TODO: Replace with concrete shipment creation and checkpoint test assertions
    with pytest.raises(NotImplementedError):
        tracking_service.create_shipment(order_id=1, carrier="FedEx", tracking_number="TRK-100")

    with pytest.raises(NotImplementedError):
        tracking_service.add_event(tracking_number="TRK-100", status="picked_up")
