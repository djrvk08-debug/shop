"""Mobile authentication, OTP, reset, and authorization coverage."""
from datetime import datetime, timedelta, timezone

import pytest

from extensions import db
from models import OTPChallenge, User
from services import otp_service


@pytest.fixture
def sent_codes(monkeypatch):
    codes = []
    monkeypatch.setattr(otp_service, "send_otp", lambda mobile, code: codes.append(code))
    return codes


def create_user(app, mobile="+919876543210", password="admin123", is_admin=False):
    with app.app_context():
        user = User(mobile=mobile, mobile_verified=True, is_admin=is_admin)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user.id


def complete_otp(client, code):
    response = client.post("/auth/verify-otp", data={"otp": code})
    assert response.status_code == 302
    return response


def test_auth_pages_use_mobile_and_otp(client):
    login = client.get("/auth/login")
    register = client.get("/auth/register")
    assert login.status_code == register.status_code == 200
    assert b"Mobile Number" in login.data
    assert b"Email Address" not in login.data
    assert b"autocomplete=\"one-time-code\"" not in login.data


def test_registration_requires_otp_before_authentication(client, app, sent_codes):
    response = client.post("/auth/register", data={
        "mobile": "09876543210", "password": "shopperpass123", "confirm_password": "shopperpass123",
    })
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/auth/verify-otp")
    assert client.get("/admin/").status_code == 403
    assert len(sent_codes) == 1
    complete_otp(client, sent_codes[-1])
    with app.app_context():
        user = User.query.filter_by(mobile="+919876543210").one()
        assert user.mobile_verified is True


def test_invalid_and_duplicate_mobile_registration(client, app, sent_codes):
    invalid = client.post("/auth/register", data={"mobile": "123", "password": "password", "confirm_password": "password"})
    assert invalid.status_code == 200
    create_user(app, "+919876543211")
    duplicate = client.post("/auth/register", data={"mobile": "919876543211", "password": "password", "confirm_password": "password"})
    assert duplicate.status_code == 200
    assert b"could not create" in duplicate.data.lower()


def test_login_requires_correct_otp_and_then_authenticates(client, app, sent_codes):
    create_user(app, "+919876543212")
    response = client.post("/auth/login", data={"mobile": "9876543212", "password": "admin123"})
    assert response.status_code == 302
    assert client.get("/admin/").status_code == 403
    assert client.post("/auth/verify-otp", data={"otp": "000000"}).status_code == 200
    complete_otp(client, sent_codes[-1])
    assert client.get("/cart/").status_code == 200


def test_login_invalid_credentials_are_generic(client, app):
    create_user(app, "+919876543213")
    response = client.post("/auth/login", data={"mobile": "9876543213", "password": "wrongpassword"})
    assert response.status_code == 200
    assert b"Invalid mobile number or password" in response.data


def test_otp_expired_reused_and_attempt_lockout(client, app, sent_codes):
    create_user(app, "+919876543214")
    client.post("/auth/login", data={"mobile": "9876543214", "password": "admin123"})
    with app.app_context():
        challenge = OTPChallenge.query.one()
        challenge.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.session.commit()
    assert client.post("/auth/verify-otp", data={"otp": sent_codes[-1]}).status_code == 200

    client.post("/auth/login", data={"mobile": "9876543214", "password": "admin123"})
    code = sent_codes[-1]
    for _ in range(4):
        client.post("/auth/verify-otp", data={"otp": "000000"})
    assert client.post("/auth/verify-otp", data={"otp": code}).status_code == 302
    assert client.post("/auth/verify-otp", data={"otp": code}).status_code == 302
    with app.app_context():
        assert OTPChallenge.query.order_by(OTPChallenge.id.desc()).first().used is True


def test_otp_resend_cooldown_and_hourly_rate_limit(client, app, sent_codes):
    app.config["OTP_RESEND_COOLDOWN_SECONDS"] = 60
    create_user(app, "+919876543215")
    client.post("/auth/login", data={"mobile": "9876543215", "password": "admin123"})
    assert client.post("/auth/resend-otp").status_code == 302


def test_otp_verify_is_rate_limited_by_mobile_and_ip(client, app, sent_codes):
    app.config["OTP_VERIFY_IP_HOURLY_LIMIT"] = 1
    app.config["OTP_VERIFY_HOURLY_LIMIT"] = 20
    create_user(app, "+919876543218")
    client.post("/auth/login", data={"mobile": "9876543218", "password": "admin123"})
    assert client.post("/auth/verify-otp", data={"otp": "000000"}).status_code == 200
    assert client.post("/auth/verify-otp", data={"otp": sent_codes[-1]}).status_code == 200
    app.config["OTP_RESEND_COOLDOWN_SECONDS"] = 0
    app.config["OTP_HOURLY_LIMIT"] = 1
    assert client.post("/auth/resend-otp").status_code == 302


def test_password_reset_uses_mobile_otp(client, app, sent_codes):
    create_user(app, "+919876543216")
    response = client.post("/auth/forgot-password", data={"mobile": "9876543216"})
    assert response.status_code == 302
    complete_otp(client, sent_codes[-1])
    response = client.post("/auth/reset-password", data={"password": "newpass123", "confirm_password": "newpass123"})
    assert response.status_code == 302
    with app.app_context():
        assert User.query.filter_by(mobile="+919876543216").one().check_password("newpass123")


def test_admin_routes_remain_protected(client, app, sent_codes):
    assert client.get("/admin/").status_code == 403
    create_user(app, "+919876543217", is_admin=True)
    client.post("/auth/login", data={"mobile": "9876543217", "password": "admin123"})
    assert client.get("/admin/").status_code == 403
    complete_otp(client, sent_codes[-1])
    assert client.get("/admin/").status_code == 200
