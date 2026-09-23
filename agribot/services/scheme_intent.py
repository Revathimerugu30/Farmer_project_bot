"""Language-independent scheme intent and farmer-detail extraction."""
from __future__ import annotations

import re
from typing import Any

SUPPORTED_LANGUAGES = ("English", "Telugu", "Hindi", "Tamil", "Kannada", "Malayalam")
LANGUAGE_CODES = {
    "English": "en-IN", "Telugu": "te-IN", "Hindi": "hi-IN", "Tamil": "ta-IN",
    "Kannada": "kn-IN", "Malayalam": "ml-IN",
}

_INTENT_TERMS = {
    "scheme", "schemes", "subsidy", "subsidies", "benefit", "benefits", "eligibility",
    "eligible", "apply", "application", "government scheme", "pm scheme",
    "योजना", "सब्सिडी", "किसान", "पात्र", "పథకం", "పథకాలు", "సబ్సిడీ", "రైతు", "వర్తిస్తాయి",
    "திட்டம்", "திட்டங்கள்", "மானியம்", "தகுதி", "ಯೋಜನೆ", "ಯೋಜನೆಗಳು", "ಸಬ್ಸಿಡಿ",
    "ಅರ್ಹ", "പദ്ധതി", "പദ്ധതികൾ", "സബ്സിഡി", "അർഹത",
}
_CROP_ALIASES = {
    "paddy": ("paddy", "rice", "ধান", "वり", "వరి", "నెల్లు", "நெல்", "ಭತ್ತ", "നെല്ല്"),
    "wheat": ("wheat", "गेहूं", "గోధుమ", "கோதுமை", "ಗೋಧಿ", "ഗോതമ്പ്"),
    "cotton": ("cotton", "कपास", "పత్తి", "பருத்தி", "ಹತ್ತಿ", "പരുത്തി"),
    "maize": ("maize", "corn", "मक्का", "మొక్కజొన్న", "மக்காச்சோளம்", "ಮೆಕ್ಕೆಜೋಳ", "ചോളം"),
    "pulses": ("pulse", "pulses", "दलहन", "పప్పు", "பருப்பு", "ಬೇಳೆ", "പയർ"),
}
_STATE_ALIASES = {"telangana": ("telangana", "తెలంగాణ", "तेलंगाना", "தெலங்கானா", "ತೆಲಂಗಾಣ", "തെലങ്കാന")}


def detect_language(text: str, selected: str | None = None) -> str:
    if selected in SUPPORTED_LANGUAGES and selected != "English":
        return selected
    for language, pattern in {
        "Telugu": r"[\u0C00-\u0C7F]", "Hindi": r"[\u0900-\u097F]", "Tamil": r"[\u0B80-\u0BFF]",
        "Kannada": r"[\u0C80-\u0CFF]", "Malayalam": r"[\u0D00-\u0D7F]",
    }.items():
        if re.search(pattern, text):
            return language
    return selected if selected in SUPPORTED_LANGUAGES else "English"


def is_scheme_query(text: str) -> bool:
    lowered = text.casefold()
    return any(term in lowered for term in _INTENT_TERMS)


def _contains(text: str, aliases: tuple[str, ...]) -> bool:
    lowered = text.casefold()
    return any(alias.casefold() in lowered for alias in aliases)


def extract_farmer_profile(text: str, normalized_text: str = "") -> dict[str, Any]:
    combined = f"{text} {normalized_text}".strip()
    profile: dict[str, Any] = {}
    for state, aliases in _STATE_ALIASES.items():
        if _contains(combined, aliases):
            profile["state"] = state.title()
            break
    for crop, aliases in _CROP_ALIASES.items():
        if _contains(combined, aliases):
            profile["crop"] = "Paddy" if crop == "paddy" else crop.title()
            break
    land_match = re.search(r"(?:\b|^)(\d+(?:\.\d+)?)\s*(?:acres?|acre|ఎకర\w*|एकड़|ஏக்கர்|ಎಕರೆ\w*|ഏക്കർ\w*)", combined, re.I)
    if land_match:
        profile["land_size"] = float(land_match.group(1))
        profile["land_unit"] = "acres"
    return profile


def normalize_query(query: str, language: str) -> str:
    """Reuse Kisan Sahayak's existing Sarvam translation helper when available."""
    if language == "English" or query.isascii():
        return query
    try:
        from kisan_sahayak.service import _retrieval_query
        return _retrieval_query(query, language)
    except Exception:
        return query
