"""Unit and integration tests for order lifecycle and checkout workflow."""
import pytest
from services import order_service
from services.order_service import ORDER_STATUS_TRANSITIONS
from extensions import db
from models import Order, OrderItem, Product, User


def test_order_status_transitions_constants():
    """Verify order state machine transition rules dictionary is defined."""
    assert "pending" in ORDER_STATUS_TRANSITIONS
    assert "paid" in ORDER_STATUS_TRANSITIONS["pending"]
    assert "cancelled" in ORDER_STATUS_TRANSITIONS["pending"]
    assert "cancelled" in ORDER_STATUS_TRANSITIONS


def test_checkout_creates_order_and_decrements_inventory(app):
    with app.app_context():
        user = User(mobile="+919876543227", mobile_verified=True)
        user.set_password("test-password")
        product = Product(name="Order Mushroom", price=25, stock=5)
        db.session.add_all([user, product])
        db.session.commit()

        order = order_service.checkout(user.id, {str(product.id): 2})

        assert order.status == "pending"
        assert order.total == 50
        assert len(order.items) == 1
        assert order.items[0].unit_price == 25
        assert db.session.get(Product, product.id).stock == 3


def test_checkout_insufficient_stock_rolls_back_everything(app):
    with app.app_context():
        user = User(mobile="+919876543228", mobile_verified=True)
        user.set_password("test-password")
        available = Product(name="Available Mushroom", price=10, stock=5)
        scarce = Product(name="Scarce Mushroom", price=20, stock=1)
        db.session.add_all([user, available, scarce])
        db.session.commit()

        with pytest.raises(ValueError, match="Insufficient stock"):
            order_service.checkout(user.id, {available.id: 2, scarce.id: 2})

        assert Order.query.count() == 0
        assert OrderItem.query.count() == 0
        assert db.session.get(Product, available.id).stock == 5
        assert db.session.get(Product, scarce.id).stock == 1


def test_order_status_transition_validation_and_retrieval(app):
    with app.app_context():
        user = User(mobile="+919876543229", mobile_verified=True)
        user.set_password("test-password")
        db.session.add(user)
        db.session.flush()
        order = Order(user_id=user.id, total=0)
        db.session.add(order)
        db.session.commit()

        with pytest.raises(ValueError, match="Invalid order status"):
            order_service.change_status(order.id, "delivered")
        paid = order_service.change_status(order.id, "paid")
        assert paid.status == "paid"
        assert order_service.get_order(order.id).id == order.id
        assert order_service.get_user_orders(user.id)[0].id == order.id
