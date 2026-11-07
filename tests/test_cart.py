"""Unit and integration tests for shopping cart functionality and routes."""
import pytest
from services import cart_service
from extensions import db
from models import Product


def test_cart_page_renders_cleanly(client):
    """Confirm the shopping cart page returns HTTP 200."""
    response = client.get("/cart/")
    assert response.status_code == 200
    assert b"Shopping Cart" in response.data


def test_cart_service_stubs_raise_not_implemented():
    """Verify service function stubs raise NotImplementedError prior to implementation."""
    # TODO: Replace with concrete unit tests once cart_service business logic is implemented
    with pytest.raises(NotImplementedError):
        cart_service.add_item({}, product_id=1, quantity=2)

    with pytest.raises(NotImplementedError):
        cart_service.update_item({1: 2}, product_id=1, quantity=3)

    with pytest.raises(NotImplementedError):
        cart_service.remove_item({1: 2}, product_id=1)

    with pytest.raises(NotImplementedError):
        cart_service.total({1: 2})


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


def test_add_demo_homepage_item_without_catalog_row(client):
    """Hardcoded homepage products can still use their displayed price."""
    response = client.post(
        "/cart/add",
        data={"product_id": 8, "quantity": 1, "unit_price": "180"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 200
    assert response.get_json() == {"cart_total": "180.00", "item_count": 1}
