"""Weather API routes."""
from flask import Blueprint, request, jsonify
from services.weather_service import get_weather
from config import DEFAULT_LATITUDE, DEFAULT_LONGITUDE

weather_bp = Blueprint("weather", __name__)


@weather_bp.route("/current", methods=["GET"])
def current():
    lat = float(request.args.get("lat", DEFAULT_LATITUDE))
    lon = float(request.args.get("lon", DEFAULT_LONGITUDE))
    return jsonify(get_weather(lat, lon))
