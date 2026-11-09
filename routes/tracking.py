"""Delivery tracking blueprint for customer status inquiries and carrier webhook ingestion."""
import hmac
from flask import Blueprint, current_app, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from services import order_service
from services import tracking_service

tracking_bp = Blueprint("tracking", __name__)


@tracking_bp.route("/track")
@login_required
def my_orders():
    """List the signed-in customer's order details and delivery progress."""
    orders = order_service.get_user_orders(current_user.id)
    return render_template("store/my_tracking.html", orders=orders)


@tracking_bp.route("/track/<string:tracking_number>")
def track_shipment(tracking_number: str):
    """Keep legacy tracking links on the single combined orders and tracking page."""
    return redirect(url_for("tracking.my_orders"))


@tracking_bp.route("/webhook/carrier", methods=["POST"])
def carrier_webhook():
    """Ingest tracking updates pushed from logistics carriers."""
    webhook_token = current_app.config.get("CARRIER_WEBHOOK_TOKEN")
    provided_token = request.headers.get("X-Carrier-Token", "")
    if not webhook_token or not hmac.compare_digest(provided_token, webhook_token):
        return jsonify({"error": "Unauthorized carrier webhook"}), 401
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"error": "Invalid JSON payload"}), 400

    required = ("tracking_number", "status")
    if not isinstance(payload, dict) or any(not isinstance(payload.get(key), str) for key in required):
        return jsonify({"error": "tracking_number and status are required"}), 400
    try:
        tracking_service.add_event(
            payload["tracking_number"], payload["status"],
            location=payload.get("location"), note=payload.get("note"),
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    return jsonify({"status": "received"}), 200
