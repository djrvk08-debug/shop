"""Unit and integration tests for shopping cart functionality and routes."""
import pytest
from decimal import Decimal
from services import cart_service
from extensions import db
from models import Order, Product, Shipment, User
from tests.conftest import authenticate


def test_cart_page_renders_cleanly(client):
    """Confirm the shopping cart page returns HTTP 200."""
    response = client.get("/cart/")
    assert response.status_code == 200
    assert b"Shopping Cart" in response.data


def test_cart_service_uses_current_price_and_checks_stock(app):
    with app.app_context():
        product = Product(name="Cart Service Mushroom", price=Decimal("12.50"), stock=4)
        db.session.add(product)
        db.session.commit()

        cart = cart_service.add_item({}, product.id, 2)
        assert cart_service.total(cart) == Decimal("25.00")
        product.price = Decimal("15.00")
        db.session.commit()
        assert cart_service.total(cart) == Decimal("30.00")
        with pytest.raises(ValueError, match="Only 4 units"):
            cart_service.add_item(cart, product.id, 3)


def test_add_to_cart_returns_ajax_summary(client, app):
    """The add endpoint returns the authoritative total for the cart toast."""
    with app.app_context():
        db.session.add(Product(name="Toast Test Mushroom", price=240, stock=10))
        db.session.commit()

    response = client.post(
        "/cart/add",
        data={"product_id": 1, "quantity": 2, "unit_price": "240"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 200
    assert response.get_json() == {"cart_total": "480.00", "item_count": 2}


def test_add_missing_product_is_rejected_even_with_submitted_price(client):
    response = client.post(
        "/cart/add",
        data={"product_id": 8, "quantity": 1, "unit_price": "180"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 400
    assert "unavailable" in response.get_json()["error"]


def test_cart_update_and_remove_controls(client, app):
    """The cart quantity form and remove button update the session cart."""
    with app.app_context():
        product = Product(name="Cart Controls Mushroom", price=Decimal("12.50"), stock=5)
        db.session.add(product)
        db.session.commit()
        product_id = product.id

    assert client.post("/cart/add", data={"product_id": product_id, "quantity": 2}).status_code == 302
    response = client.post("/cart/update", data={"product_id": product_id, "quantity": 3})
    assert response.status_code == 302
    assert b'value="3"' in client.get("/cart/").data

    response = client.post("/cart/remove", data={"product_id": product_id})
    assert response.status_code == 302
    assert b"Your cart is empty" in client.get("/cart/").data


def test_checkout_button_requires_login(client):
    response = client.get("/cart/checkout")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_checkout_redirects_to_order_confirmation(client, app):
    with app.app_context():
        user = User(mobile="+919876543220", mobile_verified=True)
        user.set_password("test-password")
        product = Product(name="Confirmation Mushroom", price=Decimal("12.50"), stock=5)
        db.session.add_all([user, product])
        db.session.commit()
        product_id = product.id
        user_id = user.id

    authenticate(client, user_id)
    with client.session_transaction() as session:
        session["cart"] = {str(product_id): 2}

    response = client.post("/cart/checkout")
    assert response.status_code == 302
    assert "/cart/orders/" in response.headers["Location"]

    confirmation = client.get(response.headers["Location"])
    assert confirmation.status_code == 200
    assert b"Order placed successfully" in confirmation.data
    assert b"Confirmation Mushroom" in confirmation.data
    assert b"Order number" in confirmation.data
    assert b"25.00" in confirmation.data
    assert b"View my orders" in confirmation.data
    assert b"Harvested" in confirmation.data
    with client.session_transaction() as session:
        assert "cart" not in session


def test_order_confirmation_is_private_to_order_owner(client, app):
    with app.app_context():
        owner = User(mobile="+919876543221", mobile_verified=True)
        owner.set_password("test-password")
        other = User(mobile="+919876543222", mobile_verified=True)
        other.set_password("test-password")
        product = Product(name="Private Order Mushroom", price=10, stock=1)
        db.session.add_all([owner, other, product])
        db.session.commit()
        order = Order(user_id=owner.id, total=10)
        db.session.add(order)
        db.session.commit()
        order_id = order.id
        other_id = other.id

    authenticate(client, other_id)
    assert client.get(f"/cart/orders/{order_id}").status_code == 404


def test_order_confirmation_shows_on_the_way_after_shipment(client, app):
    with app.app_context():
        user = User(mobile="+919876543223", mobile_verified=True)
        user.set_password("test-password")
        db.session.add(user)
        db.session.flush()
        order = Order(user_id=user.id, status="shipped", total=Decimal("0.00"))
        db.session.add(order)
        db.session.flush()
        shipment = Shipment(order_id=order.id, carrier="Farm Delivery", tracking_number="TRK-ON-WAY",
                            status="dispatched")
        db.session.add(shipment)
        db.session.commit()
        order_id = order.id
        user_id = user.id

    authenticate(client, user_id)
    response = client.get(f"/cart/orders/{order_id}")
    assert response.status_code == 200
    assert b"Your order is on the way" in response.data
    assert b"aria-current=\"step\"" in response.data
    assert b"View my orders" in response.data
