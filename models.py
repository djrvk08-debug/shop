"""Database models defining the data layer schemas for the e-commerce shop."""
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
from extensions import db, login_manager


@login_manager.user_loader
def load_user(user_id: str):
    """Load user by primary key ID for Flask-Login session management."""
    # TODO: Add caching layer (e.g. Redis) if user lookups become a bottleneck
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    """User account entity for shoppers and staff administrators."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    # Kept optional for legacy/support data; mobile is the login identifier.
    email = db.Column(db.String(255), unique=True, nullable=True, index=True)
    mobile = db.Column(db.String(20), unique=True, nullable=True, index=True)
    mobile_verified = db.Column(db.Boolean, default=False, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    orders = db.relationship("Order", backref="user", lazy=True)
    otp_challenges = db.relationship("OTPChallenge", backref="user", lazy=True,
                                     cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        """Hash and set user password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify given plaintext password against stored password hash."""
        return check_password_hash(self.password_hash, password)

    # TODO: Add relationship to Order (orders = db.relationship('Order', backref='user', lazy='dynamic'))


class OTPChallenge(db.Model):
    """Hashed, single-use OTP challenge for mobile verification."""

    __tablename__ = "otp_challenges"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    mobile = db.Column(db.String(20), nullable=False, index=True)
    purpose = db.Column(db.String(20), nullable=False, index=True)
    code_hash = db.Column(db.String(64), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    attempt_count = db.Column(db.Integer, default=0, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False, index=True)
    request_ip = db.Column(db.String(45), nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class Product(db.Model):
    """Sellable item in store catalog."""

    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, index=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    pack_size = db.Column(db.String(50), nullable=False, default="200g")
    stock = db.Column(db.Integer, default=0, nullable=False)
    thumbnail_url = db.Column(db.String(2048), nullable=True)

    # TODO: Add description, SKU, and active status fields
    # TODO: Add relationship to OrderItem


class Order(db.Model):
    """Customer purchase order record."""

    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(50), default="pending", nullable=False, index=True)
    total = db.Column(db.Numeric(10, 2), default=0.0, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    items = db.relationship("OrderItem", backref="order", lazy=True, cascade="all, delete-orphan")
    shipment = db.relationship("Shipment", backref="order", uselist=False, lazy=True)


class OrderItem(db.Model):
    """Line item contained within a customer order."""

    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)

    product = db.relationship("Product", backref=db.backref("order_items", lazy=True))


class Shipment(db.Model):
    """Logistics shipment record associated with an order."""

    __tablename__ = "shipments"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    carrier = db.Column(db.String(100), nullable=False)
    tracking_number = db.Column(db.String(100), unique=True, nullable=False, index=True)
    status = db.Column(db.String(50), default="pending", nullable=False, index=True)
    eta = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    events = db.relationship("TrackingEvent", backref="shipment", lazy=True,
                              cascade="all, delete-orphan", order_by="TrackingEvent.created_at")


class TrackingEvent(db.Model):
    """Append-only audit log of shipment progress checkpoints."""

    __tablename__ = "tracking_events"

    id = db.Column(db.Integer, primary_key=True)
    shipment_id = db.Column(db.Integer, db.ForeignKey("shipments.id"), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(255), nullable=True)
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # TODO: Enforce strict append-only constraints and immutability rules
