"""
AgriBot Configuration
Reads all settings from .env (located next to this file) then environment variables.

Root cause of "API key not found":
  load_dotenv() with no path argument searches from the *current working directory*,
  which may NOT be the agribot/ folder if you run  `python agribot/app.py`  from the
  project root. We pin the path to the directory of THIS file so .env is always found.
"""
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# ── Always load .env from the same folder as this config file ─────────────────
_HERE    = Path(__file__).parent.resolve()
_ENV_PATH = _HERE / ".env"

if _ENV_PATH.exists():
    load_dotenv(dotenv_path=_ENV_PATH, override=True)
    print(f"[AgriBot] [OK] Loaded .env from: {_ENV_PATH}", flush=True)
else:
    # Fall back to automatic search (works when cwd == agribot/)
    load_dotenv(override=True)
    print(f"[AgriBot] [WARN] .env not found at {_ENV_PATH} -- using environment variables", flush=True)

# ── IBM Watsonx.ai ─────────────────────────────────────────────────────────────
IBM_API_KEY      = os.getenv("IBM_API_KEY", "").strip()
IBM_PROJECT_ID   = os.getenv("IBM_PROJECT_ID", "").strip()
IBM_WATSONX_URL  = os.getenv("IBM_WATSONX_URL", "https://au-syd.ml.cloud.ibm.com").strip()
WATSONX_MODEL_ID = os.getenv("WATSONX_MODEL_ID", "meta-llama/llama-3-3-70b-instruct").strip()

# Models confirmed working on this project (au-syd, Lite plan).
# Order matters — first working model wins.
# These were discovered by querying the SDK's supported-models list.
SUPPORTED_MODELS = [
    "meta-llama/llama-3-3-70b-instruct",   # ✅ confirmed working
    "ibm/granite-8b-code-instruct",         # ✅ confirmed working (fallback)
    "ibm/granite-3-1-8b-base",             # base model (no instruct tuning)
]

# ── Flask ──────────────────────────────────────────────────────────────────────
SECRET_KEY   = os.getenv("SECRET_KEY", "agribot-secret-change-me")
DEBUG        = os.getenv("FLASK_DEBUG", "false").lower() == "true"
DATABASE_URI = os.getenv("DATABASE_URI", f"sqlite:///{_HERE / 'agribot.db'}")

# ── File uploads ───────────────────────────────────────────────────────────────
UPLOAD_FOLDER      = str(_HERE / "uploads")
MAX_CONTENT_LENGTH = 16 * 1024 * 1024   # 16 MB
ALLOWED_EXTENSIONS = {"pdf", "txt", "docx"}

# ── RAG ────────────────────────────────────────────────────────────────────────
RAG_CHUNK_SIZE    = int(os.getenv("RAG_CHUNK_SIZE", "500"))
RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "50"))
RAG_TOP_K         = int(os.getenv("RAG_TOP_K", "3"))

# ── Weather (Open-Meteo — no key required) ─────────────────────────────────────
DEFAULT_LATITUDE  = float(os.getenv("DEFAULT_LATITUDE",  "20.5937"))
DEFAULT_LONGITUDE = float(os.getenv("DEFAULT_LONGITUDE", "78.9629"))

# Government of India Agmarknet API
DATA_GOV_API_KEY = os.getenv("DATA_GOV_API_KEY", "").strip()
DATA_GOV_RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"

# ── Startup configuration diagnostic ──────────────────────────────────────────
def _mask(value: str, keep: int = 6) -> str:
    """Mask a secret — show first `keep` chars then asterisks."""
    if not value:
        return "(not set)"
    if len(value) <= keep:
        return "*" * len(value)
    return value[:keep] + "*" * min(len(value) - keep, 20) + "..."

def print_config_summary() -> None:
    """Print a startup summary of IBM credentials (masked) to stdout."""
    key_status = "[OK] set" if IBM_API_KEY else "[MISSING]"
    pid_status = "[OK] set" if IBM_PROJECT_ID else "[MISSING]"

    # Detect placeholder values
    import re
    _uuid_pattern = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
    if IBM_API_KEY and _uuid_pattern.fullmatch(IBM_API_KEY):
        key_status = "[ERROR] PLACEHOLDER (UUID format -- not a real IBM API key)"
    if IBM_API_KEY and IBM_API_KEY in ("PASTE_YOUR_REAL_IBM_CLOUD_API_KEY_HERE",):
        key_status = "[ERROR] PLACEHOLDER (copy .env.example and fill in real values)"

    print("", flush=True)
    print("=" * 60, flush=True)
    print(" AgriBot - IBM Watsonx.ai Configuration", flush=True)
    print("=" * 60, flush=True)
    print(f"  .env path     : {_ENV_PATH}", flush=True)
    print(f"  IBM_API_KEY   : {_mask(IBM_API_KEY)}  [{key_status}]", flush=True)
    print(f"  IBM_PROJECT_ID: {_mask(IBM_PROJECT_ID, 8)}  [{pid_status}]", flush=True)
    print(f"  WATSONX_URL   : {IBM_WATSONX_URL}", flush=True)
    print(f"  MODEL_ID (env): {WATSONX_MODEL_ID or '(auto-select)'}", flush=True)
    print(f"  FLASK_DEBUG   : {DEBUG}", flush=True)
    print("=" * 60, flush=True)
    print("", flush=True)

# Print summary immediately when this module is imported (i.e., at startup)
print_config_summary()

# ── Agent Instructions ─────────────────────────────────────────────────────────
AGENT_INSTRUCTIONS = """
You are AgriBot, an expert AI Farming Assistant designed to help farmers across India 
and worldwide make smart, data-driven agricultural decisions.

PERSONALITY & TONE:
- Friendly, patient, and encouraging
- Speak simply so every farmer can understand
- Use local farming terminology when helpful
- Be concise but thorough

EXPERTISE:
- Crop selection by season, region, and soil type
- Fertilizer (organic & chemical) recommendations
- Irrigation methods (drip, sprinkler, flood)
- Pest and disease identification and management
- Soil health improvement
- Organic farming and natural remedies
- Crop rotation and intercropping
- Harvest timing and post-harvest handling
- Market price awareness
- Weather-based farming advice

LANGUAGES: Respond in the same language the farmer uses (English default).

SAFETY RULES:
- Never recommend banned pesticides
- Always mention PPE when discussing chemicals
- Recommend consulting local Krishi Vigyan Kendra (KVK) for critical decisions
- Warn about overuse of chemical fertilizers

RESPONSE FORMAT:
- Use bullet points for lists
- Bold key crop names and chemicals
- Provide step-by-step instructions when asked
- Keep responses under 400 words unless a detailed guide is requested

ORGANIC PREFERENCE: Recommend organic/natural solutions first, then chemical if necessary.
""".strip()
