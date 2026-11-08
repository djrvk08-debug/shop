"""Unit and integration tests for shopping cart functionality and routes."""
import pytest
from decimal import Decimal
from services import cart_service
from extensions import db
from models import Product


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
