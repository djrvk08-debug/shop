"""Application configuration classes for different runtime environments."""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)
DEFAULT_DB_URI = "sqlite:///" + os.path.join(BASE_DIR, "instance", "shop.db")


class Config:
    """Base configuration with default settings and environment fallbacks."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    CARRIER_WEBHOOK_TOKEN = os.environ.get("CARRIER_WEBHOOK_TOKEN")
    SMS_PROVIDER = os.environ.get("SMS_PROVIDER", "console")
    OTP_SECRET = os.environ.get("OTP_SECRET", SECRET_KEY)
    OTP_EXPIRY_SECONDS = 300
    OTP_RESEND_COOLDOWN_SECONDS = 45
    OTP_HOURLY_LIMIT = 5
    OTP_IP_HOURLY_LIMIT = 20
    OTP_VERIFY_HOURLY_LIMIT = 20
    OTP_VERIFY_IP_HOURLY_LIMIT = 50
    TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
    TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER")
    SMS_TEMPLATE_ID = os.environ.get("SMS_TEMPLATE_ID")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = False
    TESTING = False

    # TODO: Add session cookie security flags (SESSION_COOKIE_SECURE, REMEMBER_COOKIE_HTTPONLY)


class DevelopmentConfig(Config):
    """Development environment configuration using local SQLite."""

    DEBUG = True
    _raw_db_url = os.environ.get("DATABASE_URL")
    if _raw_db_url and _raw_db_url.startswith("sqlite:///instance/"):
        SQLALCHEMY_DATABASE_URI = DEFAULT_DB_URI
    elif _raw_db_url:
        SQLALCHEMY_DATABASE_URI = _raw_db_url
    else:
        SQLALCHEMY_DATABASE_URI = DEFAULT_DB_URI


class TestingConfig(Config):
    """Testing environment configuration using in-memory SQLite."""

    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    NOTIFICATION_SENDER = None


class ProductionConfig(Config):
    """Production environment configuration with hardened defaults."""

    DEBUG = False
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
