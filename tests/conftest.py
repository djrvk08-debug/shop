"""Pytest configuration and shared test fixtures using an in-memory database."""
import os
import sys
from pathlib import Path
import pytest

# Ensure project root is available on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from config import TestingConfig
from extensions import db


@pytest.fixture
def app():
    """Create and configure an application instance using TestingConfig."""
    app_instance = create_app(TestingConfig)

    with app_instance.app_context():
        db.create_all()
        # TODO: Seed initial test data (e.g. test categories, sample products, test users)
        yield app_instance
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Provide a test client for issuing HTTP requests."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Provide a CLI runner for testing Flask custom CLI commands."""
    return app.test_cli_runner()
