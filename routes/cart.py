"""Shopping cart and checkout routing blueprint."""
from decimal import Decimal

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from services import cart_service
from services import order_service
from services import tracking_service

cart_bp = Blueprint("cart", __name__, url_prefix="/cart")


@cart_bp.route("/")
def view_cart():
    """Display the current user's session shopping cart."""
    try:
        items = cart_service.get_cart_items(session.get("cart", {}))
        cart_total = cart_service.total(session.get("cart", {}))
    except ValueError as error:
        flash(str(error), "warning")
        items, cart_total = [], Decimal("0.00")
    return render_template("store/cart.html", cart_items=items, cart_total=cart_total)


@cart_bp.route("/add", methods=["POST"])
def add_to_cart():
    """Add a product item to the shopping cart session."""
    product_id = request.form.get("product_id", type=int)
    quantity = request.form.get("quantity", default="1")
    try:
        if product_id is None:
            raise ValueError("A product is required.")
        updated_cart = cart_service.add_item(dict(session.get("cart", {})), product_id, int(quantity))
        session["cart"] = {str(key): value for key, value in updated_cart.items()}
        item_count = sum(updated_cart.values())
        cart_total = cart_service.total(session["cart"])
    except (ValueError, TypeError) as error:
        message = str(error) or "A valid quantity is required."
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify(error=message), 400
        flash(message, "warning")
        return redirect(request.referrer or url_for("store.home"))
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify(cart_total=f"{cart_total:.2f}", item_count=item_count)

    flash("Item added to cart.", "success")
    return redirect(url_for("cart.view_cart"))


@cart_bp.route("/update", methods=["POST"])
def update_cart():
    """Update item quantity in the cart session."""
    product_id = request.form.get("product_id", type=int)
    quantity = request.form.get("quantity", type=int)
    try:
        if product_id is None or quantity is None:
            raise ValueError("Product and quantity are required.")
        updated_cart = cart_service.update_item(dict(session.get("cart", {})), product_id, quantity)
        session["cart"] = {str(key): value for key, value in updated_cart.items()}
        flash("Cart updated.", "info")
    except ValueError as error:
        flash(str(error), "warning")
    return redirect(url_for("cart.view_cart"))


@cart_bp.route("/remove", methods=["POST"])
def remove_from_cart():
    """Remove an item completely from the session cart."""
    product_id = request.form.get("product_id", type=int)
    updated_cart = cart_service.remove_item(dict(session.get("cart", {})), product_id)
    session["cart"] = {str(key): value for key, value in updated_cart.items()}
    flash("Item removed from cart.", "info")
    return redirect(url_for("cart.view_cart"))


@cart_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    """Handle order checkout process and final submission."""
    if request.method == "POST":
        try:
            order = order_service.checkout(current_user.id, session.get("cart", {}))
        except ValueError as error:
            flash(str(error), "warning")
            return redirect(url_for("cart.view_cart"))
        tracking_service.create_shipment(
            order.id, "Dharti Farm Delivery", f"DF-{order.id:06d}"
        )
        session.pop("cart", None)
        flash(f"Order #{order.id} placed successfully.", "success")
        return redirect(url_for("cart.order_confirmation", order_id=order.id))

    try:
        items = cart_service.get_cart_items(session.get("cart", {}))
        cart_total = cart_service.total(session.get("cart", {}))
    except ValueError as error:
        flash(str(error), "warning")
        return redirect(url_for("cart.view_cart"))
    return render_template("store/checkout.html", cart_items=items, cart_total=cart_total)


@cart_bp.route("/orders/<int:order_id>")
@login_required
def order_confirmation(order_id):
    """Show confirmation only to the customer who placed the order."""
    order = order_service.get_order(order_id)
    if order is None or order.user_id != current_user.id:
        abort(404)
    return render_template(
        "store/order_success.html", order=order,
        milestones=tracking_service.get_milestones(order.shipment) if order.shipment else None,
    )
