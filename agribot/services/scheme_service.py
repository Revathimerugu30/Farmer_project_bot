"""Deterministic Government Scheme Finder backed by local official-source data."""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from services.scheme_intent import detect_language, extract_farmer_profile, is_scheme_query, normalize_query
from services.scheme_validator import validate_dataset

DATA_DIR = Path(__file__).parent.parent / "data" / "schemes"


@lru_cache(maxsize=1)
def load_schemes() -> tuple[dict[str, Any], ...]:
    records: list[dict[str, Any]] = []
    for filename in ("central_schemes.json", "telangana_schemes.json"):
        with (DATA_DIR / filename).open(encoding="utf-8") as handle:
            loaded = json.load(handle)
        if not isinstance(loaded, list):
            raise ValueError(f"{filename} must contain a JSON array")
        records.extend(loaded)
    validate_dataset(records)
    return tuple(records)


def _text(record: dict[str, Any]) -> str:
    eligibility = record.get("eligibility") or {}
    return " ".join([
        str(record.get("scheme_name", "")), str(record.get("description", "")),
        " ".join(map(str, record.get("benefits", []))),
        " ".join(map(str, record.get("keywords", []))),
        " ".join(map(str, eligibility.get("crop", []))),
        " ".join(map(str, eligibility.get("other_conditions", []))),
    ]).casefold()


def _status(record: dict[str, Any], profile: dict[str, Any]) -> tuple[str, str]:
    eligibility = record.get("eligibility") or {}
    state = str(profile.get("state", "")).casefold()
    allowed_states = {str(value).casefold() for value in eligibility.get("state", [])}
    if allowed_states and state and "all india" not in allowed_states and state not in allowed_states:
        return "Does not appear to match the listed criteria", "This scheme lists a different state or region."
    if allowed_states and "all india" not in allowed_states and not state:
        return "More information required", "Your state is required to verify this scheme's geographic condition."
    required_fields = []
    if eligibility.get("land_size") and "land_size" not in profile:
        required_fields.append("landholding")
    if eligibility.get("gender") and "gender" not in profile:
        required_fields.append("gender")
    if required_fields:
        return "More information required", "Your " + " and ".join(required_fields) + " information is required to verify this condition."
    if allowed_states and state:
        return "Likely eligible", f"The scheme is listed for {profile['state']} farmers and matches the information provided."
    return "May be eligible", "The scheme appears relevant, but final eligibility must be confirmed on the official website."


def find_schemes(query: str, language: str = "English", limit: int = 10) -> dict[str, Any]:
    selected_language = detect_language(query, language)
    normalized = normalize_query(query, selected_language)
    profile = extract_farmer_profile(query, normalized)
    query_text = f"{query} {normalized}".casefold()
    state = profile.get("state", "").casefold()
    scored: list[tuple[int, dict[str, Any], str, str]] = []
    for record in load_schemes():
        eligibility = record.get("eligibility") or {}
        allowed_states = {str(value).casefold() for value in eligibility.get("state", [])}
        if record.get("level") == "State" and state and state not in allowed_states:
            continue
        if record.get("level") == "State" and not state and not any(
            str(value).casefold() in query_text for value in eligibility.get("state", [])
        ):
            continue
        if "insurance" in query_text and "insurance" not in _text(record):
            continue
        if "irrigation" in query_text and not ({"irrigation", "water", "drip", "sprinkler"} & set(_text(record).split())):
            continue
        score = 0
        searchable = _text(record)
        if state and (record.get("level") == "Central" or state in allowed_states):
            score += 30
        if profile.get("crop") and profile["crop"].casefold() in searchable:
            score += 25
        query_stop_words = {
            "the", "and", "for", "from", "what", "which", "are", "with", "available",
            "government", "scheme", "schemes", "farmer", "farmers", "help", "can",
        }
        query_words = {
            word for word in re.findall(r"[a-z0-9-]+", query_text)
            if len(word) > 2 and word not in query_stop_words
        }
        score += min(20, len(query_words & set(re.findall(r"[a-z0-9-]+", searchable))) * 3)
        if record.get("level") == "State" and state:
            score += 10
        intent_words = {
            word for word in re.findall(r"[a-z0-9-]+", query_text)
            if word not in {
                "government", "scheme", "schemes", "farmer", "farmers", "me", "my",
                "for", "the", "and", "from", "what", "which", "are", "with", "available",
            }
        }
        if score or (is_scheme_query(query) and not intent_words and record.get("level") == "Central"):
            status, reason = _status(record, profile)
            scored.append((score, record, status, reason))
    scored.sort(key=lambda item: (-item[0], item[1]["level"], item[1]["scheme_name"]))
    results = []
    for score, record, status, reason in scored[:limit]:
        results.append({**record, "eligibility_status": status, "eligibility_reason": reason, "match_score": score})
    return {
        "language": selected_language,
        "normalized_query": normalized,
        "farmer_profile": profile,
        "schemes": results,
        "message": _localized_message(selected_language, bool(results)),
    }


def _localized_message(language: str, has_results: bool) -> str:
    messages = {
        "English": "These government schemes may be relevant based on the information provided." if has_results else "No matching schemes were found from the currently verified scheme dataset.",
        "Telugu": "మీరు ఇచ్చిన వివరాల ఆధారంగా ఈ ప్రభుత్వ పథకాలు మీకు సంబంధితంగా ఉండవచ్చు." if has_results else "ప్రస్తుతం ధృవీకరించిన పథకాల డేటాసెట్‌లో సరిపోలే పథకాలు కనుగొనబడలేదు.",
        "Hindi": "आपकी दी गई जानकारी के आधार पर ये सरकारी योजनाएं प्रासंगिक हो सकती हैं।" if has_results else "वर्तमान सत्यापित योजना डेटासेट में कोई मिलती-जुलती योजना नहीं मिली।",
        "Tamil": "நீங்கள் வழங்கிய தகவலின் அடிப்படையில் இந்த அரசு திட்டங்கள் தொடர்புடையதாக இருக்கலாம்." if has_results else "தற்போது சரிபார்க்கப்பட்ட திட்டத் தரவுத்தொகுப்பில் பொருத்தமான திட்டங்கள் எதுவும் இல்லை.",
        "Kannada": "ನೀವು ನೀಡಿದ ಮಾಹಿತಿಯ ಆಧಾರದ ಮೇಲೆ ಈ ಸರ್ಕಾರಿ ಯೋಜನೆಗಳು ಸಂಬಂಧಿತವಾಗಿರಬಹುದು." if has_results else "ಪ್ರಸ್ತುತ ಪರಿಶೀಲಿಸಿದ ಯೋಜನಾ ದತ್ತಾಂಶದಲ್ಲಿ ಹೊಂದಾಣಿಕೆಯ ಯೋಜನೆಗಳು ಕಂಡುಬಂದಿಲ್ಲ.",
        "Malayalam": "നിങ്ങൾ നൽകിയ വിവരങ്ങളുടെ അടിസ്ഥാനത്തിൽ ഈ സർക്കാർ പദ്ധതികൾ പ്രസക്തമായേക്കാം." if has_results else "നിലവിൽ പരിശോധിച്ച പദ്ധതി ഡാറ്റാസെറ്റിൽ പൊരുത്തപ്പെടുന്ന പദ്ധതികൾ കണ്ടെത്തിയില്ല.",
    }
    return messages.get(language, messages["English"])
