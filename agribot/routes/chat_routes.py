"""
Chat API routes.

Error-handling strategy:
  - Always log the FULL exception + traceback (exc_info=True).
  - In FLASK_DEBUG=true mode: return the real error string in the JSON response
    so developers can read it in the browser.
  - In production (DEBUG=false): return a friendly but specific message that
    distinguishes config errors (credentials) from transient errors, instead of
    the generic "AI service temporarily unavailable" catch-all.
  - Never crash — always return a JSON response the frontend can display.
"""
import traceback
import logging

from flask import Blueprint, request, jsonify, session, current_app

from services.watsonx_service import generate, build_farming_prompt
from services.weather_service  import get_weather, weather_to_text
from rag.rag_pipeline          import get_context_for_query
from models                    import db, ChatMessage
from config                    import (
    AGENT_INSTRUCTIONS, DEFAULT_LATITUDE, DEFAULT_LONGITUDE,
)

chat_bp = Blueprint("chat", __name__)
logger  = logging.getLogger(__name__)


# ── Error classifier ──────────────────────────────────────────────────────────
def _classify_error(exc: Exception) -> tuple[str, str]:
    """
    Return (user_message, error_type) based on the exception.

    user_message — shown in the chat bubble (or in JSON in debug mode).
    error_type   — sent to the frontend as metadata.
    """
    msg = str(exc)

    # ── Configuration / credential problems ───────────────────────────────────
    config_keywords = (
        "IBM_API_KEY", "IBM_PROJECT_ID", "placeholder", "not set",
        "UUID", "BXNIM0415E", "authentication", "could not be found",
        "credential", "unauthorized", "401",
        "PASTE_YOUR_REAL",
    )
    if any(kw.lower() in msg.lower() for kw in config_keywords):
        user_msg = (
            "⚙️ **IBM Watsonx.ai is not configured.**\n\n"
            "Please check the following in your `agribot/.env` file:\n"
            "- `IBM_API_KEY` must be a **real** IBM Cloud API key "
            "(generate at https://cloud.ibm.com/iam/apikeys)\n"
            "- `IBM_PROJECT_ID` must match your Watsonx.ai project\n"
            "- `IBM_WATSONX_URL` must be `https://au-syd.ml.cloud.ibm.com`\n\n"
            "After updating `.env`, restart the Flask server."
        )
        return user_msg, "config_error"

    # ── Model not available ────────────────────────────────────────────────────
    model_keywords = ("model", "not available", "not supported", "no supported")
    if any(kw.lower() in msg.lower() for kw in model_keywords):
        user_msg = (
            "🤖 **No Granite model is currently available.**\n\n"
            "AgriBot tried all supported IBM Granite models and none responded.\n\n"
            "Possible causes:\n"
            "- Your Watsonx.ai project is not in the **Sydney (au-syd)** region\n"
            "- Granite Foundation Models are not enabled in your project\n"
            "- IBM Cloud Lite quota has been exceeded for today\n\n"
            "Check your project at https://dataplatform.cloud.ibm.com"
        )
        return user_msg, "model_error"

    # ── Network / timeout ─────────────────────────────────────────────────────
    network_keywords = ("timeout", "connection", "network", "unreachable", "refused")
    if any(kw.lower() in msg.lower() for kw in network_keywords):
        user_msg = (
            "🌐 **Network error reaching IBM Watsonx.ai.**\n\n"
            "Could not connect to `https://au-syd.ml.cloud.ibm.com`.\n"
            "Please check your internet connection and try again."
        )
        return user_msg, "network_error"

    # ── Generic fallback — still better than the old message ──────────────────
    user_msg = (
        "❌ **AgriBot encountered an error.**\n\n"
        "The IBM Watsonx.ai service returned an unexpected error.\n"
        "Please check the terminal / server logs for the full traceback."
    )
    return user_msg, "ai_error"


@chat_bp.route("/message", methods=["POST"])
def message():
    data       = request.get_json(silent=True) or {}
    user_msg   = (data.get("message") or "").strip()
    session_id = session.get("session_id", data.get("session_id", "anon"))

    if not user_msg:
        return jsonify({"error": "Empty message"}), 400

    # ── Chat history ──────────────────────────────────────────────────────────
    history_rows = (
        ChatMessage.query
        .filter_by(session_id=session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(12)
        .all()
    )
    history = [{"role": r.role, "content": r.content} for r in reversed(history_rows)]

    # ── RAG context ───────────────────────────────────────────────────────────
    context = get_context_for_query(user_msg)

    # ── Weather context ───────────────────────────────────────────────────────
    lat = float(data.get("latitude",  DEFAULT_LATITUDE))
    lon = float(data.get("longitude", DEFAULT_LONGITUDE))
    try:
        weather_info = weather_to_text(get_weather(lat, lon))
    except Exception as w_exc:
        logger.warning("[AgriBot] Weather fetch failed (non-fatal): %s", w_exc)
        weather_info = ""

    # ── Soil context from request ─────────────────────────────────────────────
    soil_info = data.get("soil_info", "")

    # ── Build prompt ──────────────────────────────────────────────────────────
    prompt = build_farming_prompt(
        user_message=user_msg,
        context=context,
        chat_history=history,
        weather_info=weather_info,
        soil_info=soil_info,
        agent_instructions=AGENT_INSTRUCTIONS,
    )

    # ── Generate ──────────────────────────────────────────────────────────────
    try:
        answer = generate(prompt, max_tokens=700, temperature=0.7)

    except Exception as exc:
        tb_str = traceback.format_exc()

        # Always log the FULL traceback to the terminal
        logger.error(
            "[AgriBot] ❌  Chat generation failed.\n"
            "  session : %s\n"
            "  message : %.120s\n"
            "  error   : %s\n"
            "  traceback:\n%s",
            session_id,
            user_msg,
            str(exc),
            tb_str,
        )

        user_msg_friendly, error_type = _classify_error(exc)

        # In debug mode: include the raw error so the developer sees it in the chat
        if current_app.debug:
            debug_detail = (
                f"\n\n---\n**Debug info (FLASK_DEBUG=true):**\n"
                f"```\n{str(exc)[:1500]}\n```"
            )
            user_msg_friendly += debug_detail

        # Return as 503 but with a meaningful body — never the generic string
        return jsonify({
            "error": user_msg_friendly,
            "error_type": error_type,
            "debug_traceback": tb_str if current_app.debug else None,
        }), 503

    # ── Persist ───────────────────────────────────────────────────────────────
    try:
        db.session.add(ChatMessage(session_id=session_id, role="user",      content=user_msg))
        db.session.add(ChatMessage(session_id=session_id, role="assistant", content=answer))
        db.session.commit()
    except Exception as db_exc:
        logger.warning("[AgriBot] DB persist failed (non-fatal): %s", db_exc)

    return jsonify({"reply": answer, "session_id": session_id})


@chat_bp.route("/history", methods=["GET"])
def history():
    session_id = session.get("session_id", request.args.get("session_id", "anon"))
    rows = (
        ChatMessage.query
        .filter_by(session_id=session_id)
        .order_by(ChatMessage.created_at.asc())
        .limit(100)
        .all()
    )
    return jsonify([r.to_dict() for r in rows])


@chat_bp.route("/clear", methods=["POST"])
def clear():
    session_id = session.get("session_id", "anon")
    ChatMessage.query.filter_by(session_id=session_id).delete()
    db.session.commit()
    return jsonify({"status": "cleared"})


@chat_bp.route("/debug-config", methods=["GET"])
def debug_config():
    """
    Debug endpoint — only active in FLASK_DEBUG=true mode.
    Returns sanitised config info to help diagnose credential issues.
    """
    if not current_app.debug:
        return jsonify({"error": "Only available in debug mode"}), 403

    from config import IBM_API_KEY, IBM_PROJECT_ID, IBM_WATSONX_URL, WATSONX_MODEL_ID
    from services.watsonx_service import _active_model_id, _HARD_ERROR

    def mask(v, keep=6):
        if not v: return "(not set)"
        return v[:keep] + "…" if len(v) > keep else "***"

    return jsonify({
        "env_file_found":   (
            __import__("pathlib").Path(__file__).parent.parent / ".env"
        ).exists(),
        "IBM_API_KEY":      mask(IBM_API_KEY),
        "IBM_API_KEY_len":  len(IBM_API_KEY),
        "IBM_PROJECT_ID":   mask(IBM_PROJECT_ID, 8),
        "IBM_WATSONX_URL":  IBM_WATSONX_URL,
        "WATSONX_MODEL_ID": WATSONX_MODEL_ID or "(auto)",
        "active_model":     _active_model_id or "(not initialized)",
        "init_error":       _HARD_ERROR,
    })
