"""Crop Recommendation API routes."""
import logging
from flask import Blueprint, request, jsonify
from services.watsonx_service import generate, build_farming_prompt
from models import db, CropRecommendation
from config import AGENT_INSTRUCTIONS

crop_bp = Blueprint("crop", __name__)
logger  = logging.getLogger(__name__)


@crop_bp.route("/recommend", methods=["POST"])
def recommend():
    data     = request.get_json(silent=True) or {}
    season   = data.get("season", "")
    soil     = data.get("soil", "")
    location = data.get("location", "")
    rainfall = data.get("rainfall", "")

    if not any([season, soil, location]):
        return jsonify({"error": "At least one parameter required"}), 400

    question = (
        f"Recommend the top 5 crops for a farmer with these conditions:\n"
        f"- Season: {season}\n"
        f"- Soil type: {soil}\n"
        f"- Location/Region: {location}\n"
        f"- Expected rainfall: {rainfall}\n\n"
        "For each crop provide: expected yield, water requirement, and market demand."
    )

    prompt = build_farming_prompt(
        user_message=question,
        agent_instructions=AGENT_INSTRUCTIONS,
    )
    try:
        result = generate(prompt, max_tokens=700)
    except Exception as exc:
        logger.error("Crop recommendation error: %s", exc)
        return jsonify({"error": str(exc)}), 503

    record = CropRecommendation(
        season=season, soil=soil, location=location,
        rainfall=rainfall, result=result,
    )
    db.session.add(record)
    db.session.commit()
    return jsonify({"recommendation": result, "id": record.id})
