"""Unit and integration tests for authentication login, registration, and session management."""
import pytest
from models import User


def test_login_page_renders_cleanly(client):
    """Confirm the login page loads with HTTP 200 and auth form elements."""
    response = client.get("/auth/login")
    assert response.status_code == 200
    assert b"Sign In" in response.data
    assert b"Email Address" in response.data
    assert b"Password" in response.data


def test_admin_login_success_and_redirect(client, app):
    """Verify admin login redirects to the admin dashboard."""
    with app.app_context():
        admin = User.query.filter_by(email="admin@example.com").first()
        if not admin:
            admin = User(email="admin@example.com", is_admin=True)
            admin.set_password("admin123")
            from extensions import db
            db.session.add(admin)
            db.session.commit()

    response = client.post(
        "/auth/login",
        data={"email": "admin@example.com", "password": "admin123"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "/admin" in response.headers["Location"]

    # Following redirect should show admin overview
    follow_resp = client.get(response.headers["Location"])
    assert follow_resp.status_code == 200
    assert b"Morning Operations Overview" in follow_resp.data


def test_login_invalid_password_fails(client, app):
    """Verify incorrect password shows an error and does not log in."""
    with app.app_context():
        admin = User.query.filter_by(email="admin@example.com").first()
        if not admin:
            admin = User(email="admin@example.com", is_admin=True)
            admin.set_password("admin123")
            from extensions import db
            db.session.add(admin)
            db.session.commit()

    response = client.post(
        "/auth/login",
        data={"email": "admin@example.com", "password": "wrongpassword"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Invalid email or password" in response.data


def test_login_with_safe_next_url(client, app):
    """Verify login redirects to requested safe relative next URL."""
    with app.app_context():
        admin = User.query.filter_by(email="admin@example.com").first()
        if not admin:
            admin = User(email="admin@example.com", is_admin=True)
            admin.set_password("admin123")
            from extensions import db
            db.session.add(admin)
            db.session.commit()

    response = client.post(
        "/auth/login?next=/cart/",
        data={"email": "admin@example.com", "password": "admin123"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"] == "/cart/"


def test_customer_registration_success(client, app):
    """Verify customer registration creates user and establishes authenticated session."""
    response = client.post(
        "/auth/register",
        data={
            "email": "freshshopper@example.com",
            "password": "shopperpass123",
            "confirm_password": "shopperpass123",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Welcome to Dharti Mushrooms" in response.data

    with app.app_context():
        user = User.query.filter_by(email="freshshopper@example.com").first()
        assert user is not None
        assert user.is_admin is False
        assert user.check_password("shopperpass123") is True


def test_registration_password_mismatch_fails(client):
    """Verify registration rejects mismatched password confirmation."""
    response = client.post(
        "/auth/register",
        data={
            "email": "mismatch@example.com",
            "password": "password123",
            "confirm_password": "different123",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Passwords do not match" in response.data


def test_logout(client, app):
    """Verify logging out clears session and redirects to home."""
    with app.app_context():
        admin = User.query.filter_by(email="admin@example.com").first()
        if not admin:
            admin = User(email="admin@example.com", is_admin=True)
            admin.set_password("admin123")
            from extensions import db
            db.session.add(admin)
            db.session.commit()

    client.post("/auth/login", data={"email": "admin@example.com", "password": "admin123"})
    logout_resp = client.get("/auth/logout", follow_redirects=True)
    assert logout_resp.status_code == 200
    assert b"You have been signed out successfully" in logout_resp.data

    # Accessing admin should now be 403 Forbidden
    admin_resp = client.get("/admin/")
    assert admin_resp.status_code == 403
