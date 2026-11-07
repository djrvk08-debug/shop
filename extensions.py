"""Extensions module initializes shared Flask extension instances."""
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

# SQLAlchemy database instance
db = SQLAlchemy()

# Flask-Login authentication manager instance
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"

# TODO: Initialize Flask-WTF CSRFProtect instance if form-wide CSRF tokens are configured
# TODO: Initialize Flask-Migrate for managing database schema migrations
