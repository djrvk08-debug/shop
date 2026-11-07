"""Delivery tracking blueprint for customer status inquiries and carrier webhook ingestion."""
from flask import Blueprint, abort, jsonify, render_template, request

tracking_bp = Blueprint("tracking", __name__)


@tracking_bp.route("/track/<string:tracking_number>")
def track_shipment(tracking_number: str):
    """Render public delivery progress tracking page for a given tracking number."""
    # TODO: Query tracking_service.get_shipment_by_tracking(tracking_number)
    # TODO: If shipment not found, abort(404) or render search error
    return render_template("store/track.html", tracking_number=tracking_number)


@tracking_bp.route("/webhook/carrier", methods=["POST"])
def carrier_webhook():
    """Ingest tracking updates pushed from logistics carriers."""
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"error": "Invalid JSON payload"}), 400

    # TODO: Verify carrier signature/token for security
    # TODO: Delegate checkpoint event creation to tracking_service.add_event
    return jsonify({"status": "received"}), 200
