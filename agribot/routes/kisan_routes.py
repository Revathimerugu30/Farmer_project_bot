"""Kisan Sahayak farmer schemes assistant routes."""
import os

import requests
from flask import Blueprint, jsonify, render_template, request

from kisan_sahayak.service import answer_query, corpus_status
from services.scheme_intent import is_scheme_query
from services.scheme_service import find_schemes

kisan_bp = Blueprint("kisan", __name__)


@kisan_bp.route("/")
def page():
    return render_template("kisan.html")


@kisan_bp.route("/ask", methods=["POST"])
def ask():
    payload = request.get_json(silent=True) or {}
    query = str(payload.get("query", "")).strip()
    language = str(payload.get("language", "English")).strip() or "English"
    if len(query) < 3:
        return jsonify({"error": "Please enter a farmer scheme question."}), 400
    if len(query) > 1000:
        return jsonify({"error": "Please keep the question under 1000 characters."}), 400
    if is_scheme_query(query):
        result = find_schemes(query, language)
        citations = [
            {
                "scheme": scheme["scheme_name"],
                "source": "official government website",
                "url": scheme["official_source_url"],
            }
            for scheme in result["schemes"]
        ]
        return jsonify({"answer": result["message"], "citations": citations, "scheme_results": result})
    return jsonify(answer_query(query, language))


@kisan_bp.route("/voice", methods=["POST"])
def voice():
    """Transcribe a browser recording with Sarvam Saaras when configured."""
    api_key = os.getenv("SARVAM_API_KEY", "").strip()
    audio = request.files.get("audio")
    language = str(request.form.get("language", "en-IN")).strip()
    if not api_key:
        return jsonify({"error": "SARVAM_API_KEY is not configured."}), 503
    if audio is None:
        return jsonify({"error": "No audio recording was received."}), 400
    try:
        response = requests.post(
            "https://api.sarvam.ai/speech-to-text",
            headers={"api-subscription-key": api_key},
            files={"file": (audio.filename or "kisan.webm", audio.stream, audio.mimetype or "audio/webm")},
            data={"model": "saaras:v3", "language_code": language},
            timeout=(8, 45),
        )
        response.raise_for_status()
        payload = response.json()
        return jsonify({"text": (payload.get("transcript") or payload.get("text") or "").strip()})
    except (requests.RequestException, ValueError) as exc:
        return jsonify({"error": f"Voice transcription failed: {exc}"}), 502


@kisan_bp.route("/status")
def status():
    return jsonify(corpus_status())
