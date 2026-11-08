"""Application configuration classes for different runtime environments."""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)
DEFAULT_DB_URI = "sqlite:///" + os.path.join(BASE_DIR, "instance", "shop.db")


class Config:
    """Base configuration with default settings and environment fallbacks."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    CARRIER_WEBHOOK_TOKEN = os.environ.get("CARRIER_WEBHOOK_TOKEN")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = False
    TESTING = False

    # TODO: Add mail/SMS configuration (SMTP_SERVER, NOTIFICATION_WEBHOOK_URL)
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
