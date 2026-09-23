"""
AgriBot – Main Flask Application
AI Farming Assistant powered by IBM Watsonx.ai + Granite + RAG
"""
import os
import sys
import uuid
import logging
from pathlib import Path

# ── Ensure project root is on sys.path ────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, render_template, session, jsonify
from flask_sqlalchemy import SQLAlchemy

import config
from models import db
from routes.chat_routes       import chat_bp
from routes.weather_routes    import weather_bp
from routes.soil_routes       import soil_bp
from routes.soil_intel_routes import soil_intel_bp
from routes.crop_routes       import crop_bp
from routes.pest_routes       import pest_bp
from routes.market_routes     import market_bp
from routes.profile_routes    import profile_bp
from routes.rag_routes        import rag_bp
from routes.kisan_routes      import kisan_bp

logging.basicConfig(
    level=logging.DEBUG if config.DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
# Always show AgriBot-prefixed messages at DEBUG level regardless of global level
logging.getLogger("services.watsonx_service").setLevel(logging.DEBUG)
logging.getLogger("routes.chat_routes").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # ── Config ────────────────────────────────────────────────────────────────
    app.secret_key = config.SECRET_KEY
    app.config["SQLALCHEMY_DATABASE_URI"]        = config.DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_FOLDER"]                  = config.UPLOAD_FOLDER
    app.config["MAX_CONTENT_LENGTH"]             = config.MAX_CONTENT_LENGTH

    # ── DB ────────────────────────────────────────────────────────────────────
    db.init_app(app)
    with app.app_context():
        db.create_all()
        _seed_knowledge_base()

    # ── Blueprints ────────────────────────────────────────────────────────────
    app.register_blueprint(chat_bp,       url_prefix="/api/chat")
    app.register_blueprint(weather_bp,    url_prefix="/api/weather")
    app.register_blueprint(soil_bp,       url_prefix="/api/soil")
    app.register_blueprint(soil_intel_bp, url_prefix="/api/soil-intel")
    app.register_blueprint(crop_bp,       url_prefix="/api/crop")
    app.register_blueprint(pest_bp,       url_prefix="/api/pest")
    app.register_blueprint(market_bp,     url_prefix="/api/market")
    app.register_blueprint(profile_bp,    url_prefix="/api/profile")
    app.register_blueprint(rag_bp,        url_prefix="/api/rag")
    app.register_blueprint(kisan_bp,      url_prefix="/api/kisan")

    # ── Pages ─────────────────────────────────────────────────────────────────
    @app.route("/")
    def dashboard():
        if "session_id" not in session:
            session["session_id"] = str(uuid.uuid4())
        return render_template("dashboard.html")

    @app.route("/chat")
    def chat():
        return render_template("chat.html")

    @app.route("/weather")
    def weather():
        return render_template("weather.html")

    @app.route("/soil")
    def soil():
        return render_template("soil.html")

    @app.route("/crop")
    def crop():
        return render_template("crop.html")

    @app.route("/pest")
    def pest():
        return render_template("pest.html")

    @app.route("/market")
    def market():
        return render_template("market.html")

    @app.route("/profile")
    def profile():
        return render_template("profile.html")

    @app.route("/knowledge")
    def knowledge():
        return render_template("knowledge.html")

    @app.route("/kisan")
    def kisan():
        return render_template("kisan.html")

    @app.route("/soil-intel")
    def soil_intel():
        return render_template("soil_intel.html")

    # ── Health + Debug ─────────────────────────────────────────────────────────
    @app.route("/health")
    def health():
        from services.watsonx_service import get_active_model_id, _init_error
        return jsonify({
            "status": "ok" if get_active_model_id() != "unavailable" else "error",
            "model":  get_active_model_id(),
            "init_error": _init_error,
        })

    @app.route("/api/chat/reset-ai", methods=["POST"])
    def reset_ai():
        """Re-initialize Watsonx client (e.g. after fixing .env)."""
        from services.watsonx_service import reset_client
        reset_client()
        return jsonify({"status": "reset", "message": "AI client reset. Next request will re-initialize."})

    return app


def _seed_knowledge_base():
    """Index built-in agricultural knowledge text files."""
    from rag.rag_pipeline import index_document, list_documents, INDEX_DIR

    seed_dir = Path(__file__).parent / "rag" / "seeds"
    seed_dir.mkdir(parents=True, exist_ok=True)

    # Write seed files if they don't exist
    _write_seed_files(seed_dir)

    indexed = {d["source"] for d in list_documents()}
    for txt_file in seed_dir.glob("*.txt"):
        if str(txt_file) not in indexed:
            n = index_document(str(txt_file), source_name=txt_file.stem.replace("_", " ").title())
            logger.info("Seeded %d chunks from %s", n, txt_file.name)


def _write_seed_files(seed_dir: Path):
    files = {
        "crop_guide.txt": CROP_GUIDE,
        "fertilizer_guide.txt": FERTILIZER_GUIDE,
        "pest_management.txt": PEST_MANAGEMENT,
        "soil_health.txt": SOIL_HEALTH,
        "irrigation_guide.txt": IRRIGATION_GUIDE,
    }
    for fname, content in files.items():
        fpath = seed_dir / fname
        if not fpath.exists():
            fpath.write_text(content, encoding="utf-8")


# ── Seed Knowledge Content ────────────────────────────────────────────────────
CROP_GUIDE = """
CROP SELECTION GUIDE FOR INDIAN FARMERS

Kharif Season (June–October):
- Rice: Suitable for clayey, loamy soils with pH 5.5–7.0. Requires heavy rainfall (1000–2000 mm).
- Maize: Loamy soil, pH 5.8–7.0. Moderate rainfall. High nitrogen requirement.
- Cotton: Black (Regur) soil, pH 6.0–7.5. Long growing season.
- Soybean: Well-drained loamy soil, pH 6.0–6.5. Nitrogen-fixing crop.
- Groundnut: Sandy loam, pH 6.0–6.5. Good for Andhra Pradesh, Gujarat, Rajasthan.
- Bajra (Pearl Millet): Sandy soil, pH 6.0–7.5. Drought tolerant.
- Jowar (Sorghum): Medium black soil, pH 6.5–7.5. Semi-arid regions.

Rabi Season (November–March):
- Wheat: Loamy/clay loam soil, pH 6.0–7.5. Requires cool climate. Punjab, Haryana, UP.
- Mustard: Well-drained sandy loam, pH 6.0–7.5. Rajasthan, UP, MP.
- Chickpea (Gram): Well-drained loam, pH 6.0–8.0. Low water requirement.
- Barley: Light loamy, pH 6.5–7.8. Can tolerate saline conditions.
- Peas: Well-drained loam, pH 6.0–7.5. Cool humid climate.
- Potato: Sandy loam to loamy, pH 5.2–6.4. Requires well-drained soil.

Zaid Season (March–June):
- Watermelon: Sandy loam, pH 6.0–7.0. High temperature crops.
- Muskmelon: Sandy loam, pH 6.0–7.0.
- Cucumber: Well-drained loam, pH 5.5–6.8.
- Bitter Gourd: Loamy to clay loam, pH 6.0–6.7.
- Sunflower: Well-drained loam, pH 6.0–7.5. Can be grown in all seasons.

Crop Rotation Benefits:
- Rice → Wheat rotation is common in Punjab and Haryana.
- Legume crops (chickpea, soybean) fix nitrogen and benefit subsequent crops.
- Avoid growing same crop family consecutively to reduce pest buildup.

Seed Selection Tips:
- Use certified seeds from government agricultural departments.
- Hybrid seeds give higher yield but require more inputs.
- Open-pollinated varieties are better for saving seeds.
- Check for disease resistance when selecting varieties.
""".strip()

FERTILIZER_GUIDE = """
FERTILIZER GUIDE FOR INDIAN AGRICULTURE

Macronutrients:
- Nitrogen (N): Promotes leafy growth. Sources: Urea (46% N), CAN (25% N), DAP (18% N).
- Phosphorus (P): Root development, flowering. Sources: SSP (16% P), DAP (46% P2O5).
- Potassium (K): Disease resistance, fruit quality. Sources: MOP (60% K2O), SOP (50% K2O).

NPK Recommendations by Crop:
- Rice: N:P:K = 120:60:40 kg/ha. Split nitrogen into 3 doses.
- Wheat: N:P:K = 120:60:40 kg/ha. Apply P and K as basal dose.
- Maize: N:P:K = 180:80:60 kg/ha. High nitrogen feeder.
- Cotton: N:P:K = 150:75:75 kg/ha.
- Sugarcane: N:P:K = 250:100:120 kg/ha.
- Tomato: N:P:K = 150:100:120 kg/ha.

Organic Fertilizers:
- Vermicompost: 5–10 t/ha. Improves soil structure and microbial activity.
- FYM (Farm Yard Manure): 10–15 t/ha. Apply 2–3 weeks before sowing.
- Green Manuring: Dhaincha, Sunhemp. Plow in 45–50 days after sowing.
- Neem Cake: 200–400 kg/ha. Also acts as nematicide.
- Bone Meal: Good source of phosphorus for organic farming.
- Wood Ash: Source of potassium. Apply 2–4 t/ha.

Micronutrients:
- Zinc deficiency: Apply Zinc Sulphate 25 kg/ha. Common in rice-wheat system.
- Iron deficiency: Ferrous Sulphate 25 kg/ha. Common in alkaline soils.
- Boron: Borax 10 kg/ha for oilseeds and vegetables.
- Manganese: Manganese Sulphate for sandy soils.

Soil pH Correction:
- Acidic soil (pH < 6.0): Apply agricultural lime 2–4 t/ha.
- Alkaline soil (pH > 8.0): Apply gypsum 5–10 t/ha or elemental sulfur.

Biofertilizers:
- Rhizobium: For legume crops (chickpea, soybean). Seed treatment.
- Azotobacter: For non-legume crops. Nitrogen fixation.
- PSB (Phosphate Solubilizing Bacteria): Improves phosphorus availability.
- Mycorrhiza: Improves nutrient and water uptake.
""".strip()

PEST_MANAGEMENT = """
INTEGRATED PEST MANAGEMENT (IPM) GUIDE

Common Rice Pests:
- Brown Plant Hopper (BPH): Use resistant varieties. Spray Imidacloprid 17.8 SL @ 125 ml/ha.
  Organic: Spray NSKE (Neem Seed Kernel Extract) 5%.
- Stem Borer: Chlorpyrifos 20 EC @ 2 L/ha. Organic: Trichogramma cards release.
- Blast Disease: Tricyclazole 75 WP @ 600 g/ha. Avoid excess nitrogen.

Common Wheat Pests:
- Aphids: Dimethoate 30 EC @ 1 L/ha or Malathion 50 EC @ 1.5 L/ha.
  Organic: Neem oil spray 2 ml/L water.
- Yellow Rust: Propiconazole 25 EC @ 500 ml/ha. Use resistant varieties.
- Loose Smut: Seed treatment with Carboxin 37.5% + Thiram 37.5% @ 3 g/kg seed.

Vegetable Pests:
- Whitefly on Tomato: Imidacloprid 200 SL @ 0.5 ml/L water.
  Organic: Yellow sticky traps, Verticillium lecanii spray.
- Fruit Borer on Chilli: Spinosad 45 SC @ 0.5 ml/L or neem oil 3 ml/L.
- Diamondback Moth on Cabbage: Bt spray (Bacillus thuringiensis) @ 1 g/L.

Organic Pest Control Methods:
- Pheromone traps for monitoring and mass trapping.
- Border crops (marigold) to repel nematodes and attract pest predators.
- Neem-based sprays: Neem oil 5 ml/L + soap 1 ml/L as sticker.
- Trichoderma: Soil application for fungal diseases.
- Pseudomonas fluorescens: Seed treatment and foliar spray.

Disease Management:
- Downy Mildew: Metalaxyl + Mancozeb spray @ 2 g/L water.
- Powdery Mildew: Sulfur WP @ 3 g/L or Carbendazim @ 1 g/L.
- Bacterial Blight: Copper Oxychloride @ 3 g/L water. Remove infected plants.
- Root Rot: Drench Carbendazim @ 2 g/L in soil around roots.

Prevention Tips:
- Use disease-free, certified seeds.
- Crop rotation to break pest cycles.
- Maintain field hygiene; remove crop residue.
- Ensure proper drainage to prevent fungal diseases.
- Apply pesticides in early morning or evening to avoid bee mortality.
- Always wear protective equipment (gloves, mask) when applying chemicals.
""".strip()

SOIL_HEALTH = """
SOIL HEALTH MANAGEMENT GUIDE

Soil Types in India:
- Alluvial Soil: Found in Indo-Gangetic plains. Suitable for wheat, rice, sugarcane.
- Black Cotton Soil (Regur): Maharashtra, MP, Gujarat. Best for cotton, soybean.
- Red Laterite Soil: South India. Suitable for groundnut, pulses with fertilizers.
- Sandy Soil: Rajasthan, coastal areas. Needs organic matter and frequent irrigation.
- Clayey Soil: Holds water well. Suitable for rice. Needs drainage management.

Soil Testing:
- Test soil every 3 years. Collect samples from 0–15 cm depth.
- Parameters: pH, EC, N, P, K, Organic Carbon, micronutrients.
- Contact nearest Soil Testing Laboratory or use Soil Health Card scheme.

Soil pH Management:
- Ideal pH for most crops: 6.0–7.5
- pH < 5.5 (Acidic): Apply lime (CaCO3) @ 2–4 t/ha. Wait 2–3 weeks before sowing.
- pH > 8.5 (Alkaline/Saline): Apply gypsum @ 5–10 t/ha. Grow salt-tolerant crops.

Improving Soil Organic Carbon:
- Target: >0.8% organic carbon for good soil health.
- Add FYM, compost, or vermicompost annually.
- Practice mulching with crop residue.
- Grow green manure crops (Dhaincha, Sesbania).
- Minimum tillage reduces carbon loss.

Soil Conservation:
- Contour farming on slopes to reduce erosion.
- Windbreaks/shelter belts in arid regions.
- Cover crops during fallow period.
- Bund making and field leveling.

Water Conservation in Soil:
- Mulching reduces evaporation by 30–40%.
- Deep ploughing improves water infiltration.
- Add organic matter to improve water holding capacity.
""".strip()

IRRIGATION_GUIDE = """
IRRIGATION METHODS AND WATER MANAGEMENT

Irrigation Methods:
1. Drip Irrigation:
   - Water use efficiency: 90–95%.
   - Best for: Fruits, vegetables, orchards, sugarcane.
   - Subsidy available under PM Krishi Sinchai Yojana.
   - Cost: ₹50,000–1,50,000 per ha. ROI within 2–3 years.

2. Sprinkler Irrigation:
   - Water use efficiency: 70–80%.
   - Best for: Wheat, groundnut, vegetables, fodder crops.
   - Suitable for undulating terrain.
   - Cost: ₹20,000–60,000 per ha.

3. Flood Irrigation:
   - Water use efficiency: 40–50%.
   - Traditional method. High water use.
   - Still common for rice in India.

4. Furrow Irrigation:
   - Better than flood for row crops.
   - Suitable for maize, cotton, sugarcane.

Water Requirements by Crop:
- Rice: 1200–2000 mm total water requirement.
- Wheat: 400–500 mm. Irrigate at crown root initiation, tillering, jointing, flowering, grain filling.
- Maize: 500–700 mm. Critical stages: tasseling, silking.
- Sugarcane: 1500–2500 mm.
- Cotton: 700–1200 mm.
- Tomato: 400–600 mm.
- Groundnut: 400–600 mm.

Irrigation Scheduling:
- Irrigate based on soil moisture, not fixed schedule.
- Use tensiometer or feel method to check soil moisture.
- Critical irrigation stages vary by crop.
- Avoid waterlogging; ensure proper drainage.

Water Conservation Tips:
- Laser land leveling improves irrigation efficiency by 20–25%.
- Night irrigation reduces evaporation losses.
- Reuse drainage water for irrigation.
- Check-basin method for fruit orchards.
- Rainwater harvesting through farm ponds.
""".strip()


if __name__ == "__main__":
    app = create_app()

    # Print active model on startup
    from services.watsonx_service import get_active_model_id
    print(f"[AgriBot] Starting server…", flush=True)
    print(f"[AgriBot] IBM Watsonx URL : {config.IBM_WATSONX_URL}", flush=True)
    print(f"[AgriBot] Project ID      : {config.IBM_PROJECT_ID[:8]}…" if config.IBM_PROJECT_ID else "[AgriBot] ⚠  IBM_PROJECT_ID not set", flush=True)

    app.run(host="0.0.0.0", port=5000, debug=config.DEBUG)
