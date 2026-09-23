"""Market Prices API routes."""
from flask import Blueprint, request, jsonify
from services.market_service import get_live_market_prices

market_bp = Blueprint("market", __name__)


@market_bp.route("/live", methods=["GET"])
def live_prices():
    commodity = request.args.get("commodity", "Tomato").strip()
    state = request.args.get("state", "Telangana").strip()
    if not commodity or not state:
        return jsonify({"error": "commodity and state are required"}), 400
    try:
        return jsonify(get_live_market_prices(commodity, state))
    except Exception as exc:
        return jsonify({"error": f"Agmarknet request failed: {exc}"}), 502
