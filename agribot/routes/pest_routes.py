"""Pest Detection API routes."""
import os
import logging
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from services.watsonx_service import generate, build_farming_prompt
from models import db, PestDetection
from config import AGENT_INSTRUCTIONS, UPLOAD_FOLDER, ALLOWED_EXTENSIONS

pest_bp = Blueprint("pest", __name__)
logger  = logging.getLogger(__name__)


def _allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in {"jpg", "jpeg", "png", "webp"}


@pest_bp.route("/detect", methods=["POST"])
def detect():
    crop_name = request.form.get("crop_name", "unknown crop")
    symptoms  = request.form.get("symptoms", "")

    # Save uploaded image if provided
    image_path = ""
    if "image" in request.files:
        f = request.files["image"]
        if f and _allowed(f.filename):
            fname = secure_filename(f.filename)
            image_path = os.path.join(UPLOAD_FOLDER, fname)
            f.save(image_path)

    question = (
        f"A farmer has a crop health problem with {crop_name}.\n"
        f"Observed symptoms: {symptoms or 'not specified'}.\n\n"
        "Please provide:\n"
        "1. Most likely disease or pest identification\n"
        "2. Organic treatment methods\n"
        "3. Chemical treatment options (with dosage)\n"
        "4. Prevention methods for future crops\n"
        "5. When to seek expert help"
    )

    prompt = build_farming_prompt(
        user_message=question,
        agent_instructions=AGENT_INSTRUCTIONS,
    )
    try:
        result = generate(prompt, max_tokens=700)
    except Exception as exc:
        logger.error("Pest detection error: %s", exc)
        return jsonify({"error": str(exc)}), 503

    record = PestDetection(
        image_path=image_path, crop_name=crop_name, result=result,
    )
    db.session.add(record)
    db.session.commit()
    return jsonify({"diagnosis": result, "id": record.id})
