"""Farmer Profile API routes."""
from flask import Blueprint, request, jsonify
from models import db, FarmerProfile

profile_bp = Blueprint("profile", __name__)


@profile_bp.route("", methods=["GET"])
@profile_bp.route("/", methods=["GET"])
def get_profile():
    p = FarmerProfile.query.order_by(FarmerProfile.id.desc()).first()
    if p:
        return jsonify(p.to_dict())
    return jsonify({})


@profile_bp.route("/save", methods=["POST"])
def save_profile():
    data = request.get_json(silent=True) or {}
    p = FarmerProfile.query.order_by(FarmerProfile.id.desc()).first()
    if not p:
        p = FarmerProfile()
        db.session.add(p)

    p.name       = data.get("name", p.name or "")
    p.village    = data.get("village", p.village or "")
    p.district   = data.get("district", p.district or "")
    p.state      = data.get("state", p.state or "")
    p.farm_size  = float(data["farm_size"]) if data.get("farm_size") else p.farm_size
    p.soil_type  = data.get("soil_type", p.soil_type or "")
    p.main_crop  = data.get("main_crop", p.main_crop or "")
    p.irrigation = data.get("irrigation", p.irrigation or "")

    db.session.commit()
    return jsonify({"status": "saved", "profile": p.to_dict()})
