"""Unit and integration tests for order lifecycle and checkout workflow."""
import pytest
from services import order_service
from services.order_service import ORDER_STATUS_TRANSITIONS


def test_order_status_transitions_constants():
    """Verify order state machine transition rules dictionary is defined."""
    assert "pending" in ORDER_STATUS_TRANSITIONS
    assert "paid" in ORDER_STATUS_TRANSITIONS["pending"]
    assert "cancelled" in ORDER_STATUS_TRANSITIONS["pending"]
    assert "cancelled" in ORDER_STATUS_TRANSITIONS


def test_order_service_stubs_raise_not_implemented():
    """Verify order service function stubs raise NotImplementedError prior to implementation."""
    # TODO: Replace with concrete checkout and state transition test assertions
    with pytest.raises(NotImplementedError):
        order_service.checkout(user_id=1, cart={1: 2})

    with pytest.raises(NotImplementedError):
        order_service.change_status(order_id=1, new_status="paid")
