"""Application factory module configuring and assembling the Flask application."""
import os
import click
from flask import Flask, send_from_directory
from config import Config, config_by_name
from extensions import db, login_manager
from models import User
from routes.admin import admin_bp
from routes.auth import auth_bp
from routes.cart import cart_bp
from routes.store import store_bp
from routes.tracking import tracking_bp


def create_app(config_class=None) -> Flask:
    """Create and configure a Flask application instance with blueprints, extensions, and CLI commands.

    :param config_class: Optional configuration class override.
    :return: Configured Flask application instance.
    """
    app = Flask(__name__)

    # Select configuration
    if config_class is None:
        env_name = os.environ.get("FLASK_ENV", "development").lower()
        config_class = config_by_name.get(env_name, Config)

    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Register blueprints
    app.register_blueprint(store_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(tracking_bp)
    app.register_blueprint(admin_bp)

    @app.get("/service-worker.js")
    def service_worker():
        """Serve the worker from the site root so it can control all pages."""
        return send_from_directory(app.static_folder, "service-worker.js", mimetype="application/javascript")

    # Ensure instance directory exists
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    # Register CLI commands
    @app.cli.command("init-db")
    def init_db_command():
        """Create all database tables."""
        db.create_all()
        click.echo("Initialized database tables.")

    @app.cli.command("create-admin")
    @click.option("--email", default=None, help="Admin email address.")
    @click.option("--password", default=None, help="Admin password.")
    def create_admin_command(email, password):
        """Create admin user if it does not already exist."""
        admin_email = email or os.environ.get("ADMIN_EMAIL", "admin@example.com")
        admin_pass = password or os.environ.get("ADMIN_PASSWORD", "admin123")
        existing_user = User.query.filter_by(email=admin_email).first()
        if existing_user:
            click.echo(f"Admin user '{admin_email}' already exists.")
        else:
            admin_user = User(email=admin_email, is_admin=True)
            admin_user.set_password(admin_pass)
            db.session.add(admin_user)
            db.session.commit()
            click.echo(f"Created admin user: {admin_email}")

    # TODO: Register custom error handlers (400, 403, 404, 500)
    # TODO: Register template context processors (e.g. cart item count, current year)
    # TODO: Register database migration commands if required

    return app


# Application instance for CLI invocation via `flask --app app run`
app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
