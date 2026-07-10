"""Soil Analysis API routes."""
import logging
from flask import Blueprint, request, jsonify
from services.watsonx_service import generate, build_farming_prompt
from models import db, SoilAnalysis
from config import AGENT_INSTRUCTIONS

soil_bp = Blueprint("soil", __name__)
logger  = logging.getLogger(__name__)


@soil_bp.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True) or {}
    soil_type  = data.get("soil_type", "")
    ph         = data.get("ph", "")
    nitrogen   = data.get("nitrogen", "")
    phosphorus = data.get("phosphorus", "")
    potassium  = data.get("potassium", "")

    if not soil_type:
        return jsonify({"error": "Soil type is required"}), 400

    soil_info = (
        f"Soil Type: {soil_type}, pH: {ph}, "
        f"Nitrogen: {nitrogen} kg/ha, Phosphorus: {phosphorus} kg/ha, "
        f"Potassium: {potassium} kg/ha"
    )
    question = (
        f"Given this soil profile: {soil_info}, provide:\n"
        "1. Top 3 suitable crops\n"
        "2. Fertilizer recommendations\n"
        "3. Irrigation advice\n"
        "4. Soil improvement suggestions"
    )

    prompt = build_farming_prompt(
        user_message=question,
        soil_info=soil_info,
        agent_instructions=AGENT_INSTRUCTIONS,
    )
    try:
        result = generate(prompt, max_tokens=600)
    except Exception as exc:
        logger.error("Soil analysis error: %s", exc)
        return jsonify({"error": str(exc)}), 503

    record = SoilAnalysis(
        soil_type=soil_type, ph=float(ph) if ph else None,
        nitrogen=float(nitrogen) if nitrogen else None,
        phosphorus=float(phosphorus) if phosphorus else None,
        potassium=float(potassium) if potassium else None,
        result=result,
    )
    db.session.add(record)
    db.session.commit()
    return jsonify({"analysis": result, "id": record.id})


@soil_bp.route("/history", methods=["GET"])
def history():
    rows = SoilAnalysis.query.order_by(SoilAnalysis.created_at.desc()).limit(20).all()
    return jsonify([r.to_dict() for r in rows])
