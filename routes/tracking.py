"""Delivery tracking blueprint for customer status inquiries and carrier webhook ingestion."""
import hmac
from flask import Blueprint, abort, current_app, jsonify, render_template, request
from services import tracking_service

tracking_bp = Blueprint("tracking", __name__)


@tracking_bp.route("/track/<string:tracking_number>")
def track_shipment(tracking_number: str):
    """Render public delivery progress tracking page for a given tracking number."""
    shipment = tracking_service.get_shipment_by_tracking(tracking_number)
    if shipment is None:
        abort(404)
    return render_template("store/track.html", tracking_number=tracking_number,
                           shipment=shipment,
                           eta=shipment.eta or tracking_service.calculate_eta(shipment.id))


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
