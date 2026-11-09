"""Admin dashboard blueprint for product catalog, orders, shipments, and user administration."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy.orm import joinedload, selectinload
from extensions import db
from models import Order, OrderItem, Product, Shipment, User
from services import analytics_service, search_service, tracking_service

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.before_request
def require_admin():
    """Enforce administrator authorization before accessing any admin blueprint endpoint."""
    if not current_user.is_authenticated or not getattr(current_user, "is_admin", False):
        abort(403)


@admin_bp.route("/")
@admin_bp.route("/dashboard")
def dashboard():
    """Render the executive administration dashboard with summary metrics."""
    daily = analytics_service.sales_by_day(1)
    return render_template(
        "admin/dashboard.html", today_sales=daily[0]["total_revenue"] if daily else 0,
        today_order_count=daily[0]["total_orders"] if daily else 0,
        order_status_counts=analytics_service.orders_by_status(),
        shipment_status_counts=analytics_service.shipments_by_status(),
        best_sellers=analytics_service.best_sellers(5),
        orders_to_pack=Order.query.filter(Order.status.in_(["pending", "paid", "processing"])).count(),
        active_shipments=Shipment.query.filter(Shipment.status.in_(
            ["picked_up", "in_transit", "out_for_delivery"]
        )).count(),
        low_stock_products=Product.query.filter(Product.stock < 10).order_by(Product.stock).all(),
        recent_orders=Order.query.options(joinedload(Order.user), selectinload(Order.items).joinedload(OrderItem.product))
            .order_by(Order.created_at.desc()).limit(10).all(),
    )


@admin_bp.route("/products")
def products():
    """Display product catalog management inventory view."""
    products = Product.query.order_by(Product.name).all()
    return render_template("admin/products.html", products=products)


@admin_bp.route("/products/new", methods=["GET", "POST"])
def product_create():
    """Create a new product in the store catalog."""
    if request.method == "POST":
        try:
            product = search_service.create_product(
                request.form.get("name", ""), request.form.get("price", ""),
                request.form.get("pack_size", ""), request.form.get("stock", ""),
                request.form.get("thumbnail_url", ""),
            )
        except ValueError as error:
            flash(str(error), "danger")
        else:
            flash(f"{product.name} created successfully.", "success")
            return redirect(url_for("admin.products"))

    return render_template("admin/product_form.html")


@admin_bp.route("/orders")
def orders():
    """Display and manage customer purchase orders."""
    orders = Order.query.options(joinedload(Order.user), selectinload(Order.items).joinedload(OrderItem.product))\
        .order_by(Order.created_at.desc()).all()
    return render_template("admin/orders.html", orders=orders)


@admin_bp.route("/shipments")
def shipments():
    """Display and manage logistics shipments and fulfillment statuses."""
    shipments = Shipment.query.options(joinedload(Shipment.order), selectinload(Shipment.events))\
        .order_by(Shipment.created_at.desc()).all()
    return render_template(
        "admin/shipments.html", shipments=shipments,
        shipment_transitions={
            shipment.id: tracking_service.DELIVERY_STATUS_TRANSITIONS.get(shipment.status, [])
            for shipment in shipments
        },
    )


@admin_bp.route("/shipments/<int:shipment_id>/status", methods=["POST"])
def update_shipment_status(shipment_id):
    """Record an authorized shipment milestone and refresh the admin shipment list."""
    shipment = db.session.get(Shipment, shipment_id)
    if shipment is None:
        abort(404)
    try:
        tracking_service.add_event(
            shipment.tracking_number, request.form.get("status", ""),
            location=request.form.get("location"), note=request.form.get("note"),
        )
    except ValueError as error:
        flash(str(error), "danger")
    else:
        flash(f"Shipment #{shipment.id} status updated.", "success")
    return redirect(url_for("admin.shipments"))


@admin_bp.route("/users")
def users():
    """Manage customer and staff administrator accounts."""
    users = User.query.order_by(User.mobile).all()
    return render_template("admin/dashboard.html", users=users)
