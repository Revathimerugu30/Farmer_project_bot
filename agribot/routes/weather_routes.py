"""Weather API routes."""
from flask import Blueprint, request, jsonify
from services.weather_service import get_weather

weather_bp = Blueprint("weather", __name__)


@weather_bp.route("/current", methods=["GET"])
def current():
    try:
        lat = float(request.args["lat"])
        lon = float(request.args["lon"])
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Latitude and longitude are required"}), 400

    try:
        return jsonify(get_weather(lat, lon))
    except Exception as exc:
        return jsonify({"error": f"Weather provider unavailable: {exc}"}), 503
