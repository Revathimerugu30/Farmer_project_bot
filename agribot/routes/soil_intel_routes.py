"""
Soil Intelligence API
Advanced soil analysis: image upload + location + optional NPK/pH
→ AI-powered report with crop recommendations, fertilizer, irrigation, organic tips.
"""
import os
import base64
import logging
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

from services.watsonx_service import generate, build_farming_prompt
from models import db, SoilIntelligence
from config import AGENT_INSTRUCTIONS, UPLOAD_FOLDER

soil_intel_bp = Blueprint("soil_intel", __name__)
logger        = logging.getLogger(__name__)

ALLOWED_IMG = {"jpg", "jpeg", "png", "webp", "bmp"}

INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Delhi", "Jammu & Kashmir", "Ladakh", "Other",
]


def _allowed_img(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMG


def _image_to_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _describe_image_via_text_model(image_path: str, state: str, season: str) -> str:
    """
    Since Granite text models don't do vision, we ask the AI to reason about
    common soil characteristics for the given state/season and image color cues
    described by filename and context.  The response is clearly labelled as
    a TEXT-BASED ESTIMATE.
    """
    # Extract file extension as a proxy cue
    ext = os.path.splitext(image_path)[1].lower()

    prompt_parts = [
        f"<|system|>\n{AGENT_INSTRUCTIONS}\n<|end|>",
        "<|user|>",
        f"A farmer from {state} during the {season} season has uploaded a soil image (file: {os.path.basename(image_path)}).",
        "",
        "Based on typical soil conditions for this region and season, provide a structured soil visual analysis estimate.",
        "IMPORTANT: Clearly state this is a TEXT-BASED ESTIMATE, not a laboratory analysis.",
        "",
        "Provide:",
        "1. Likely soil texture (sandy/loamy/clayey/silty) for this region",
        "2. Typical soil color range and what it indicates (organic matter, iron content)",
        "3. Probable moisture level indicators",
        "4. Estimated soil organic matter level",
        "5. Common deficiencies for this region",
        "",
        "Keep response concise (under 200 words). Start with: 'VISUAL ESTIMATE (Not a lab test):'",
        "<|end|>",
        "<|assistant|>",
    ]
    return generate("\n".join(prompt_parts), max_tokens=300, temperature=0.5)


def _build_full_report(
    state: str,
    district: str,
    season: str,
    image_analysis: str,
    ph: str,
    nitrogen: str,
    phosphorus: str,
    potassium: str,
    has_image: bool,
) -> tuple[str, int]:
    """Build full recommendation report and return (report_text, confidence_score)."""

    # Calculate confidence based on available data
    confidence = 40  # base from state/season
    if district:     confidence += 10
    if has_image:    confidence += 15
    if ph:           confidence += 10
    if nitrogen:     confidence += 8
    if phosphorus:   confidence += 8
    if potassium:    confidence += 9
    confidence = min(confidence, 95)  # cap at 95 — never 100 without lab test

    npk_info = ""
    if any([ph, nitrogen, phosphorus, potassium]):
        npk_info = f"Provided soil test values — pH: {ph or 'not given'}, N: {nitrogen or 'not given'} kg/ha, P: {phosphorus or 'not given'} kg/ha, K: {potassium or 'not given'} kg/ha."

    question = f"""Provide a comprehensive Smart Soil Intelligence Report for a farmer with these details:

**Location:** {state}, {district or 'district not specified'}
**Season:** {season}
{f'**Soil Image Analysis:** {image_analysis}' if has_image else '**Note:** No soil image was uploaded.'}
{f'**Lab Values:** {npk_info}' if npk_info else '**Note:** No NPK/pH values provided.'}

Generate a structured report with these EXACT sections:

## 🌍 Estimated Soil Profile
- Soil type estimate and reasoning
- Confidence: {confidence}% (clearly state this is an AI estimate)

## 🌾 Top 5 Recommended Crops
For each crop: suitability reason, expected yield, sowing window

## 🧪 Fertilizer Recommendations
- Organic options (preferred)
- Chemical fallback with doses (kg/ha)
- Micronutrient advice if applicable

## 💧 Irrigation Suggestions
- Recommended method and schedule
- Water requirement estimate

## 🌿 Organic Farming Tips
- 3-5 specific organic practices for this soil/region

## 📅 Sowing Calendar
- Best sowing dates for top 3 crops

## ⚠️ Important Disclaimer
Remind the farmer this is an AI estimate and to visit their local Krishi Vigyan Kendra (KVK) or Soil Testing Lab for a certified analysis.

{"If data is insufficient for a confident recommendation, ask 2-3 specific follow-up questions." if confidence < 55 else ""}
"""

    prompt = build_farming_prompt(
        user_message=question,
        agent_instructions=AGENT_INSTRUCTIONS,
    )
    report = generate(prompt, max_tokens=900, temperature=0.6)
    return report, confidence


@soil_intel_bp.route("/analyze", methods=["POST"])
def analyze():
    state    = request.form.get("state", "").strip()
    district = request.form.get("district", "").strip()
    season   = request.form.get("season", "").strip()
    ph       = request.form.get("ph", "").strip()
    nitrogen = request.form.get("nitrogen", "").strip()
    phosphorus = request.form.get("phosphorus", "").strip()
    potassium  = request.form.get("potassium", "").strip()

    if not state or not season:
        return jsonify({"error": "State and Season are required fields."}), 400

    # Handle image upload
    image_path = ""
    has_image  = False
    if "image" in request.files:
        f = request.files["image"]
        if f and f.filename and _allowed_img(f.filename):
            fname      = secure_filename(f.filename)
            image_path = os.path.join(UPLOAD_FOLDER, f"soil_intel_{fname}")
            f.save(image_path)
            has_image = True

    try:
        # Step 1: Describe the soil image (text-based)
        image_analysis = ""
        if has_image:
            image_analysis = _describe_image_via_text_model(image_path, state, season)

        # Step 2: Build full report
        report, confidence = _build_full_report(
            state=state,
            district=district,
            season=season,
            image_analysis=image_analysis,
            ph=ph,
            nitrogen=nitrogen,
            phosphorus=phosphorus,
            potassium=potassium,
            has_image=has_image,
        )
    except Exception as exc:
        logger.error("Soil intelligence error: %s", exc)
        return jsonify({"error": str(exc)}), 503

    # Persist
    record = SoilIntelligence(
        image_path=image_path,
        state=state,
        district=district,
        season=season,
        ph=float(ph) if ph else None,
        nitrogen=float(nitrogen) if nitrogen else None,
        phosphorus=float(phosphorus) if phosphorus else None,
        potassium=float(potassium) if potassium else None,
        image_analysis=image_analysis,
        full_report=report,
        confidence=confidence,
    )
    db.session.add(record)
    db.session.commit()

    return jsonify({
        "id": record.id,
        "image_analysis": image_analysis,
        "report": report,
        "confidence": confidence,
        "has_image": has_image,
        "state": state,
        "district": district,
        "season": season,
    })


@soil_intel_bp.route("/history", methods=["GET"])
def history():
    rows = SoilIntelligence.query.order_by(
        SoilIntelligence.created_at.desc()
    ).limit(10).all()
    return jsonify([r.to_dict() for r in rows])


@soil_intel_bp.route("/states", methods=["GET"])
def states():
    return jsonify(INDIAN_STATES)
