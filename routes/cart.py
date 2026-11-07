"""Shopping cart and checkout routing blueprint."""
from decimal import Decimal

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from extensions import db
from models import Product

cart_bp = Blueprint("cart", __name__, url_prefix="/cart")


@cart_bp.route("/")
def view_cart():
    """Display the current user's session shopping cart."""
    # TODO: Fetch cart dict from session.get('cart', {})
    # TODO: Delegate product resolution and pricing to cart_service.get_cart_items
    return render_template("store/cart.html")


@cart_bp.route("/add", methods=["POST"])
def add_to_cart():
    """Add a product item to the shopping cart session."""
    product_id = request.form.get("product_id", type=int)
    quantity = max(request.form.get("quantity", type=int) or 1, 1)
    if product_id is None:
        return jsonify(error="A product is required."), 400

    product = db.session.get(Product, product_id)
    unit_price = product.price if product is not None else request.form.get("unit_price", type=Decimal)
    if unit_price is None:
        return jsonify(error="Product price is unavailable."), 400

    cart = dict(session.get("cart", {}))
    key = str(product_id)
    existing = cart.get(key, {})
    if isinstance(existing, int):
        existing = {"quantity": existing, "unit_price": str(unit_price)}
    cart[key] = {
        "quantity": int(existing.get("quantity", 0)) + quantity,
        "unit_price": str(unit_price),
    }
    session["cart"] = cart

    item_count = sum(item["quantity"] for item in cart.values())
    cart_total = sum(
        Decimal(item["unit_price"]) * item["quantity"] for item in cart.values()
    )
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify(cart_total=f"{cart_total:.2f}", item_count=item_count)

    flash("Item added to cart.", "success")
    return redirect(url_for("cart.view_cart"))


@cart_bp.route("/update", methods=["POST"])
def update_cart():
    """Update item quantity in the cart session."""
    # TODO: Extract product_id and new quantity from request.form
    # TODO: Delegate mutation to cart_service.update_item
    flash("Cart updated.", "info")
    return redirect(url_for("cart.view_cart"))


@cart_bp.route("/remove", methods=["POST"])
def remove_from_cart():
    """Remove an item completely from the session cart."""
    # TODO: Extract product_id from request.form
    # TODO: Delegate item removal to cart_service.remove_item
    flash("Item removed from cart.", "info")
    return redirect(url_for("cart.view_cart"))


@cart_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    """Handle order checkout process and final submission."""
    if request.method == "POST":
        # TODO: Call order_service.checkout(current_user.id, session.get('cart', {}))
        # TODO: Handle payment processing and clear cart upon completion
        flash("Order placed successfully.", "success")
        return redirect(url_for("store.home"))

    return render_template("store/checkout.html")
