"""
Database models and helper functions (SQLite via SQLAlchemy).
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class FarmerProfile(db.Model):
    __tablename__ = "farmer_profile"
    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(120), nullable=False)
    village       = db.Column(db.String(120))
    district      = db.Column(db.String(120))
    state         = db.Column(db.String(120))
    farm_size     = db.Column(db.Float)          # in acres
    soil_type     = db.Column(db.String(80))
    main_crop     = db.Column(db.String(120))
    irrigation    = db.Column(db.String(80))
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "village": self.village,
            "district": self.district, "state": self.state,
            "farm_size": self.farm_size, "soil_type": self.soil_type,
            "main_crop": self.main_crop, "irrigation": self.irrigation,
        }


class ChatMessage(db.Model):
    __tablename__ = "chat_message"
    id         = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), index=True)
    role       = db.Column(db.String(16))   # 'user' | 'assistant'
    content    = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
        }


class SoilAnalysis(db.Model):
    __tablename__ = "soil_analysis"
    id          = db.Column(db.Integer, primary_key=True)
    soil_type   = db.Column(db.String(80))
    ph          = db.Column(db.Float)
    nitrogen    = db.Column(db.Float)
    phosphorus  = db.Column(db.Float)
    potassium   = db.Column(db.Float)
    result      = db.Column(db.Text)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "soil_type": self.soil_type, "ph": self.ph,
            "nitrogen": self.nitrogen, "phosphorus": self.phosphorus,
            "potassium": self.potassium, "result": self.result,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class CropRecommendation(db.Model):
    __tablename__ = "crop_recommendation"
    id        = db.Column(db.Integer, primary_key=True)
    season    = db.Column(db.String(40))
    soil      = db.Column(db.String(80))
    location  = db.Column(db.String(120))
    rainfall  = db.Column(db.String(40))
    result    = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "season": self.season, "soil": self.soil,
            "location": self.location, "rainfall": self.rainfall, "result": self.result,
        }


class PestDetection(db.Model):
    __tablename__ = "pest_detection"
    id          = db.Column(db.Integer, primary_key=True)
    image_path  = db.Column(db.String(256))
    crop_name   = db.Column(db.String(120))
    result      = db.Column(db.Text)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "image_path": self.image_path,
            "crop_name": self.crop_name, "result": self.result,
        }


class SoilIntelligence(db.Model):
    __tablename__ = "soil_intelligence"
    id            = db.Column(db.Integer, primary_key=True)
    image_path    = db.Column(db.String(256))
    state         = db.Column(db.String(120))
    district      = db.Column(db.String(120))
    season        = db.Column(db.String(80))
    ph            = db.Column(db.Float, nullable=True)
    nitrogen      = db.Column(db.Float, nullable=True)
    phosphorus    = db.Column(db.Float, nullable=True)
    potassium     = db.Column(db.Float, nullable=True)
    image_analysis = db.Column(db.Text)   # AI visual description
    full_report    = db.Column(db.Text)   # Full recommendation
    confidence     = db.Column(db.Integer, default=0)  # 0-100
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "image_path": self.image_path,
            "state": self.state, "district": self.district,
            "season": self.season, "ph": self.ph,
            "nitrogen": self.nitrogen, "phosphorus": self.phosphorus,
            "potassium": self.potassium, "image_analysis": self.image_analysis,
            "full_report": self.full_report, "confidence": self.confidence,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
