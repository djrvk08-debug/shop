"""Catalog, search, seeding, aggregate, and admin workflow coverage."""
from datetime import datetime, timezone
from decimal import Decimal
import pytest
from sqlalchemy import text

from extensions import db
from models import Order, OrderItem, Product, User
from services import analytics_service, search_service
from tests.conftest import authenticate


def test_catalog_search_autocomplete_and_idempotent_seed(app, client, runner):
    first_init = runner.invoke(args=["init-db"])
    second_init = runner.invoke(args=["init-db"])
    assert first_init.exit_code == 0
    assert second_init.exit_code == 0
    with app.app_context():
        assert Product.query.count() == 8
        assert Product.query.filter_by(pack_size="200g").count() >= 5
        pearl_id = Product.query.filter_by(name="Pearl Oyster Mushrooms").first().id
        assert search_service.search_catalog("oyster")
        assert pearl_id in search_service.search_catalog("pearl")
        assert "Pearl Oyster Mushrooms" in search_service.autocomplete_query("pearl")

    home = client.get("/")
    assert home.status_code == 200
    assert b"Pearl Oyster Mushrooms" in home.data
    search_response = client.get("/search?q=porcini")
    assert search_response.status_code == 200
    assert b"Sun-Dried Shiitake &amp; Porcini Mix" in search_response.data
    suggestion_response = client.get("/autocomplete?q=shi")
    assert suggestion_response.status_code == 200
    assert "Fresh Shiitake Mushrooms" in suggestion_response.get_json()["suggestions"]


def test_catalog_sort_pagination_and_product_detail(app, client):
    with app.app_context():
        db.session.add_all([
            Product(name=f"Catalog Item {number:02}", price=number + 1, pack_size="100g", stock=10)
            for number in range(14)
        ])
        db.session.commit()
        product_id = Product.query.filter_by(name="Catalog Item 00").first().id

    second_page = client.get("/products?page=2")
    assert second_page.status_code == 200
    assert b"Product pages" in second_page.data
    detail = client.get(f"/product/{product_id}")
    assert detail.status_code == 200
    assert b"Catalog Item 00" in detail.data
    assert client.get("/product/99999").status_code == 404
    assert client.get("/products?sort=invalid").status_code == 400


def test_admin_pages_and_product_creation_use_database_records(app, client):
    with app.app_context():
        admin = User(mobile="+919876543224", mobile_verified=True, is_admin=True)
        admin.set_password("admin-pass")
        customer = User(mobile="+919876543225", mobile_verified=True)
        customer.set_password("customer-pass")
        db.session.add_all([admin, customer])
        db.session.flush()
        product = Product(name="Admin Catalog Product", price=Decimal("42.50"), pack_size="100g", stock=7)
        order = Order(user_id=customer.id, status="processing", total=Decimal("42.50"))
        db.session.add_all([product, order])
        db.session.flush()
        db.session.add(OrderItem(order_id=order.id, product_id=product.id, quantity=1,
                                 unit_price=product.price))
        db.session.commit()
        admin_id = admin.id

    authenticate(client, admin_id)
    for path, expected in [
        ("/admin/", b"Admin Catalog Product"),
        ("/admin/products", b"Admin Catalog Product"),
        ("/admin/orders", b"+919876543225"),
        ("/admin/users", b"+919876543225"),
        ("/admin/shipments", b"No shipments found."),
    ]:
        response = client.get(path)
        assert response.status_code == 200
        assert expected in response.data

    response = client.post("/admin/products/new", data={
        "name": "Created Through Admin", "price": "51.25", "pack_size": "100g", "stock": "12",
        "thumbnail_url": "https://images.example.test/harvest.jpg",
    })
    assert response.status_code == 302
    with app.app_context():
        created = Product.query.filter_by(name="Created Through Admin").one()
        assert created.price == Decimal("51.25")
        assert created.pack_size == "100g"
        assert created.stock == 12
        assert created.thumbnail_url == "https://images.example.test/harvest.jpg"
        created_id = created.id
    assert b'https://images.example.test/harvest.jpg' in client.get("/").data
    detail = client.get(f"/product/{created_id}")
    assert b'https://images.example.test/harvest.jpg' in detail.data


def test_product_thumbnail_url_is_optional_and_rejects_unsafe_scheme(app):
    with app.app_context():
        product = search_service.create_product("No Thumbnail", 10, "100g", 1)
        assert product.thumbnail_url is None

        with pytest.raises(ValueError, match="HTTP or HTTPS URL"):
            search_service.create_product(
                "Unsafe Thumbnail", 10, "100g", 1, "javascript:alert(1)"
            )


def test_init_db_adds_thumbnail_column_to_existing_product_table(app, runner):
    with app.app_context():
        db.drop_all()
        with db.engine.begin() as connection:
            connection.execute(text(
                "CREATE TABLE products (id INTEGER PRIMARY KEY, name VARCHAR(255) NOT NULL, "
                "price NUMERIC(10, 2) NOT NULL, stock INTEGER NOT NULL)"
            ))

    result = runner.invoke(args=["init-db"])
    assert result.exit_code == 0
    with app.app_context(), db.engine.connect() as connection:
        columns = {row[1] for row in connection.execute(text("PRAGMA table_info(products)"))}
        assert "thumbnail_url" in columns
        assert "pack_size" in columns


def test_analytics_use_ordered_sales_records(app):
    with app.app_context():
        user = User(mobile="+919876543226", mobile_verified=True)
        user.set_password("test-password")
        product = Product(name="Analytics Mushroom", price=10, stock=10)
        db.session.add_all([user, product])
        db.session.flush()
        order = Order(user_id=user.id, status="delivered", total=Decimal("30.00"),
                      created_at=datetime.now(timezone.utc))
        db.session.add(order)
        db.session.flush()
        db.session.add(OrderItem(order_id=order.id, product_id=product.id, quantity=3,
                                 unit_price=Decimal("10.00")))
        db.session.commit()

        top = analytics_service.best_sellers(1)
        daily = analytics_service.sales_by_day(1)
        assert top == [{"product_id": product.id, "product_name": product.name, "total_sold": 3}]
        assert daily[0]["total_orders"] == 1
        assert Decimal(daily[0]["total_revenue"]) == Decimal("30.00")
        assert analytics_service.orders_by_status()["delivered"] == 1
