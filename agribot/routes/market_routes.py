"""Market Prices API routes."""
from flask import Blueprint, request, jsonify
from services.market_service import get_market_prices, get_price_for_crop

market_bp = Blueprint("market", __name__)


@market_bp.route("/prices", methods=["GET"])
def prices():
    return jsonify(get_market_prices())


@market_bp.route("/price/<crop_name>", methods=["GET"])
def price(crop_name: str):
    item = get_price_for_crop(crop_name)
    if item:
        return jsonify(item)
    return jsonify({"error": f"Price not found for '{crop_name}'"}), 404
