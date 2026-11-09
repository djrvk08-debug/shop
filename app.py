"""Application factory module configuring and assembling the Flask application."""
import os
import click
from datetime import datetime, timezone
from flask import Flask, jsonify, render_template, request, send_from_directory, session
from sqlalchemy import inspect, text
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

    @app.context_processor
    def template_context():
        cart = session.get("cart", {})
        item_count = 0
        for value in cart.values() if isinstance(cart, dict) else []:
            try:
                item_count += int(value.get("quantity", 0) if isinstance(value, dict) else value)
            except (TypeError, ValueError):
                continue
        return {"cart_item_count": item_count, "current_year": datetime.now(timezone.utc).year}

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/error.html", status_code=404,
                               message="The requested page could not be found."), 404

    @app.errorhandler(400)
    def bad_request(error):
        return render_template("errors/error.html", status_code=400,
                               message="The request could not be processed."), 400

    @app.errorhandler(ValueError)
    def validation_error(error):
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify(error=str(error)), 400
        return render_template("errors/error.html", status_code=400, message=str(error)), 400

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template("errors/error.html", status_code=500,
                               message="An unexpected error occurred."), 500

    # Ensure instance directory exists
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    # Register CLI commands
    @app.cli.command("init-db")
    def init_db_command():
        """Create database tables and seed the initial catalog."""
        db.create_all()
        with db.engine.begin() as connection:
            user_inspector = inspect(connection)
            user_details = user_inspector.get_columns("users")
            user_columns = {column["name"] for column in user_details}
            if "mobile" not in user_columns:
                connection.execute(text("ALTER TABLE users ADD COLUMN mobile VARCHAR(20)"))
            if "mobile_verified" not in user_columns:
                connection.execute(text(
                    "ALTER TABLE users ADD COLUMN mobile_verified BOOLEAN NOT NULL DEFAULT 0"
                ))
            # SQLite cannot change a NOT NULL legacy email column in place. Keep
            # the column for support data, but rebuild the table so new mobile-only
            # registrations can leave it empty.
            email_column = next((column for column in user_details if column["name"] == "email"), None)
            if email_column and not email_column["nullable"]:
                connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
                connection.execute(text("DROP INDEX IF EXISTS ux_users_mobile"))
                connection.execute(text(
                    "CREATE TABLE users_new ("
                    "id INTEGER NOT NULL PRIMARY KEY, "
                    "email VARCHAR(255), "
                    "mobile VARCHAR(20), "
                    "mobile_verified BOOLEAN NOT NULL DEFAULT 0, "
                    "password_hash VARCHAR(255) NOT NULL, "
                    "is_admin BOOLEAN NOT NULL DEFAULT 0"
                    ")"
                ))
                connection.execute(text(
                    "INSERT INTO users_new "
                    "(id, email, mobile, mobile_verified, password_hash, is_admin) "
                    "SELECT id, email, mobile, mobile_verified, password_hash, is_admin FROM users"
                ))
                connection.execute(text("DROP TABLE users"))
                connection.execute(text("ALTER TABLE users_new RENAME TO users"))
                connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email)"))
                connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ux_users_mobile ON users (mobile)"
            ))
            product_columns = {column["name"] for column in inspect(connection).get_columns("products")}
            if "pack_size" not in product_columns:
                connection.execute(text(
                    "ALTER TABLE products ADD COLUMN pack_size VARCHAR(50) NOT NULL DEFAULT '200g'"
                ))
            if "thumbnail_url" not in product_columns:
                connection.execute(text(
                    "ALTER TABLE products ADD COLUMN thumbnail_url VARCHAR(2048)"
                ))
            if "category_id" in product_columns:
                # SQLite cannot drop a column that is still present in the table's
                # foreign-key definition, so rebuild the legacy products table.
                connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
                connection.execute(text(
                    "CREATE TABLE products_new ("
                    "id INTEGER NOT NULL PRIMARY KEY, "
                    "name VARCHAR(255) NOT NULL, "
                    "price NUMERIC(10, 2) NOT NULL, "
                    "pack_size VARCHAR(50) NOT NULL DEFAULT '200g', "
                    "stock INTEGER NOT NULL, thumbnail_url VARCHAR(2048)"
                    ")"
                ))
                connection.execute(text(
                    "INSERT INTO products_new (id, name, price, pack_size, stock, thumbnail_url) "
                    "SELECT id, name, price, COALESCE(pack_size, '200g'), stock, thumbnail_url FROM products"
                ))
                connection.execute(text("DROP TABLE products"))
                connection.execute(text("ALTER TABLE products_new RENAME TO products"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_products_name ON products (name)"))
            connection.execute(text("DROP TABLE IF EXISTS categories"))
        from services.search_service import seed_sample_data
        seed_sample_data()
        click.echo("Initialized database tables and sample catalog.")

    @app.cli.command("create-admin")
    @click.option("--mobile", default=None, help="Admin mobile number in +91XXXXXXXXXX format.")
    @click.option("--password", default=None, help="Admin password.")
    def create_admin_command(mobile, password):
        """Create admin user if it does not already exist."""
        from services.mobile_service import normalize_mobile
        admin_mobile = normalize_mobile(mobile or os.environ.get("ADMIN_MOBILE") or click.prompt("Admin mobile number"))
        admin_pass = password or os.environ.get("ADMIN_PASSWORD") or click.prompt(
            "Admin password", hide_input=True, confirmation_prompt=True
        )
        existing_user = User.query.filter_by(mobile=admin_mobile).first()
        if existing_user:
            click.echo(f"Admin user '{admin_mobile}' already exists.")
        else:
            admin_user = User(mobile=admin_mobile, mobile_verified=True, is_admin=True)
            admin_user.set_password(admin_pass)
            db.session.add(admin_user)
            db.session.commit()
            click.echo(f"Created admin user: {admin_mobile}")

    @app.cli.command("set-user-mobile")
    @click.option("--user-id", type=int, required=True, help="Existing user ID.")
    @click.option("--mobile", required=True, help="New mobile number in +91XXXXXXXXXX format.")
    def set_user_mobile_command(user_id, mobile):
        """Attach and verify a mobile number for a legacy user without one."""
        from services.mobile_service import normalize_mobile
        user = db.session.get(User, user_id)
        if user is None:
            raise click.ClickException("User not found.")
        normalized = normalize_mobile(mobile)
        duplicate = User.query.filter(User.mobile == normalized, User.id != user.id).first()
        if duplicate:
            raise click.ClickException("That mobile number is already in use.")
        user.mobile = normalized
        user.mobile_verified = True
        db.session.commit()
        click.echo(f"Updated user {user.id} with mobile {normalized}.")

    # TODO: Register custom error handlers (400, 403, 404, 500)
    # TODO: Register template context processors (e.g. cart item count, current year)
    # TODO: Register database migration commands if required

    return app


# Application instance for CLI invocation via `flask --app app run`
app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
