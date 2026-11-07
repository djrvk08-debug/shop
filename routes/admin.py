"""Admin dashboard blueprint for product catalog, orders, shipments, and user administration."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

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
    # TODO: Fetch metrics from analytics_service (sales_by_day, shipments_by_status, best_sellers)
    return render_template("admin/dashboard.html")


@admin_bp.route("/products")
def products():
    """Display product catalog management inventory view."""
    # TODO: Fetch product list with category and stock counts
    return render_template("admin/products.html")


@admin_bp.route("/products/new", methods=["GET", "POST"])
def product_create():
    """Create a new product in the store catalog."""
    if request.method == "POST":
        # TODO: Validate form input and create Product record
        flash("Product created successfully.", "success")
        return redirect(url_for("admin.products"))

    return render_template("admin/product_form.html")


@admin_bp.route("/orders")
def orders():
    """Display and manage customer purchase orders."""
    # TODO: Fetch orders with customer info and order items
    return render_template("admin/orders.html")


@admin_bp.route("/shipments")
def shipments():
    """Display and manage logistics shipments and fulfillment statuses."""
    # TODO: Fetch shipments with latest tracking checkpoint status
    return render_template("admin/shipments.html")


@admin_bp.route("/users")
def users():
    """Manage customer and staff administrator accounts."""
    # TODO: Fetch user listing with role toggling support
    return render_template("admin/dashboard.html")
