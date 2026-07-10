"""
IBM Watsonx.ai Service
Handles model selection, fallback, and text generation.

Confirmed working on au-syd Lite plan (tested 2026-07):
  meta/llama-3-3-70b-instruct  — primary model
  ibm/granite-8b-code-instruct — fallback

SDK: ibm-watsonx-ai >= 1.1.2

DEBUGGING:
  All errors are logged with full tracebacks.
  Set FLASK_DEBUG=true in .env to see the real IBM error in the chat bubble.
"""
import re
import logging
import traceback
import warnings
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy-initialized — app starts even if SDK is missing
_client           = None
_active_model_id: Optional[str]  = None

# Errors that should be cached (credentials/project wrong → don't retry on every message)
_HARD_ERROR: Optional[str] = None

# Errors that should NOT be cached (SDK missing → cleared after install)
_SOFT_ERROR: Optional[str] = None

# ── Model format detection ────────────────────────────────────────────────────
_LLAMA_MODELS   = frozenset({
    "meta-llama/llama-3-3-70b-instruct",
    "meta-llama/llama-3-1-8b",
    "meta-llama/llama-3-1-70b-gptq",
})
_GRANITE_INSTRUCT = frozenset({
    "ibm/granite-3-8b-instruct",
    "ibm/granite-3-2b-instruct",
    "ibm/granite-13b-instruct-v2",
    "ibm/granite-13b-chat-v2",
})


def _validate_api_key(key: str) -> None:
    """Raise ValueError with an actionable message if the key looks wrong."""
    if not key:
        raise ValueError(
            "IBM_API_KEY is not set.\n"
            "  → Copy .env.example to .env and fill in your real IBM Cloud API key.\n"
            "  → Get one at: https://cloud.ibm.com/iam/apikeys"
        )
    if key in ("PASTE_YOUR_REAL_IBM_CLOUD_API_KEY_HERE",):
        raise ValueError(
            "IBM_API_KEY is still the placeholder value from .env.example.\n"
            "  → Replace it with your real IBM Cloud API key.\n"
            "  → Get one at: https://cloud.ibm.com/iam/apikeys"
        )
    if re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", key):
        raise ValueError(
            "IBM_API_KEY looks like a UUID — that is NOT a valid IBM Cloud IAM API key.\n"
            "  IBM IAM keys are long alphanumeric strings (e.g. 'AbCdEf1234...').\n"
            "  → Generate a real key at: https://cloud.ibm.com/iam/apikeys\n"
            "  → Then update IBM_API_KEY in your .env file."
        )


def _validate_project_id(pid: str) -> None:
    if not pid:
        raise ValueError(
            "IBM_PROJECT_ID is not set.\n"
            "  → Find it in Watsonx.ai → your project → Manage tab → General → Project ID."
        )
    if pid in ("PASTE_YOUR_WATSONX_PROJECT_ID_HERE",):
        raise ValueError(
            "IBM_PROJECT_ID is still the placeholder value.\n"
            "  → Replace it with your real Watsonx.ai Project ID."
        )


def _get_client():
    """
    Return a cached ModelInference client.

    Caching strategy:
      _HARD_ERROR — credential/project errors: cached permanently until reset_client().
      _SOFT_ERROR — SDK missing / transient: NOT cached; retried on every call.
    """
    global _client, _active_model_id, _HARD_ERROR, _SOFT_ERROR

    if _client is not None:
        return _client

    # Re-raise permanent credential errors immediately (don't retry every message)
    if _HARD_ERROR:
        raise RuntimeError(_HARD_ERROR)

    # ── Import SDK ─────────────────────────────────────────────────────────────
    try:
        from ibm_watsonx_ai import Credentials
        from ibm_watsonx_ai.foundation_models import ModelInference
    except ImportError as exc:
        _SOFT_ERROR = str(exc)
        raise RuntimeError(
            "ibm-watsonx-ai SDK is not installed.\n"
            "  Run: pip install ibm-watsonx-ai>=1.1.2"
        ) from exc

    from config import (
        IBM_API_KEY, IBM_PROJECT_ID, IBM_WATSONX_URL,
        WATSONX_MODEL_ID, SUPPORTED_MODELS,
    )

    # ── Validate credentials ───────────────────────────────────────────────────
    try:
        _validate_api_key(IBM_API_KEY)
        _validate_project_id(IBM_PROJECT_ID)
    except ValueError as exc:
        _HARD_ERROR = str(exc)
        logger.error("[AgriBot] ❌  Credential validation failed:\n%s", str(exc))
        raise RuntimeError(str(exc)) from exc

    logger.info("[AgriBot] Connecting to %s (project: %s…)", IBM_WATSONX_URL, IBM_PROJECT_ID[:8])

    credentials = Credentials(url=IBM_WATSONX_URL, api_key=IBM_API_KEY)

    # Build candidate list: env model first, then fallbacks
    candidates = []
    if WATSONX_MODEL_ID and WATSONX_MODEL_ID not in candidates:
        candidates.append(WATSONX_MODEL_ID)
    for m in SUPPORTED_MODELS:
        if m not in candidates:
            candidates.append(m)

    logger.info("[AgriBot] Trying models in order: %s", candidates)

    last_error: Optional[Exception] = None
    for model_id in candidates:
        logger.info("[AgriBot] → Trying: %s", model_id)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")   # suppress deprecation/lifecycle warnings during probe
                model = ModelInference(
                    model_id=model_id,
                    credentials=credentials,
                    project_id=IBM_PROJECT_ID,
                )
                probe = model.generate_text(
                    prompt="hello",
                    params={"max_new_tokens": 1},
                )

            logger.info("[AgriBot] ✅  Probe OK for %s (response_type=%s)", model_id, type(probe).__name__)
            _active_model_id = model_id
            _client          = model
            print(f"[AgriBot] [OK] Active model : {model_id}", flush=True)
            print(f"[AgriBot]      URL           : {IBM_WATSONX_URL}", flush=True)
            return _client

        except Exception as exc:
            err_str = str(exc)
            tb_str  = traceback.format_exc()

            # ── Hard fail: credentials / project wrong ─────────────────────────
            auth_keywords = (
                "BXNIM0415E", "could not be found", "authentication failed",
                "unauthorized", "401", "invalid api", "invalid_api",
            )
            if any(kw.lower() in err_str.lower() for kw in auth_keywords):
                msg = (
                    f"IBM Cloud authentication failed.\n\n"
                    f"Error: {err_str}\n\n"
                    f"Fix:\n"
                    f"  1. Open agribot/.env\n"
                    f"  2. Set IBM_API_KEY to a valid key → https://cloud.ibm.com/iam/apikeys\n"
                    f"  3. Confirm IBM_PROJECT_ID → your Watsonx.ai project → Manage tab\n"
                    f"  4. Confirm IBM_WATSONX_URL = https://au-syd.ml.cloud.ibm.com\n"
                    f"  5. Restart Flask"
                )
                _HARD_ERROR = msg
                logger.error(
                    "[AgriBot] ❌  Auth error on model %s:\n%s\n\nTraceback:\n%s",
                    model_id, err_str, tb_str,
                )
                raise RuntimeError(msg) from exc

            # ── Soft fail: model not available for this project ────────────────
            logger.warning(
                "[AgriBot] [WARN] Model %s not available: %s\n  Full traceback:\n%s",
                model_id, err_str, tb_str,
            )
            last_error = exc

    # ── All candidates exhausted ───────────────────────────────────────────────
    msg = (
        f"No supported model is available for this Watsonx.ai project.\n\n"
        f"Tried: {candidates}\n"
        f"Last error: {last_error}\n\n"
        f"Checklist:\n"
        f"  • IBM_WATSONX_URL = https://au-syd.ml.cloud.ibm.com\n"
        f"  • Watsonx.ai project must be in the Sydney (au-syd) region\n"
        f"  • Foundation models must be enabled in your project\n"
        f"  • IBM Cloud Lite plan must have Watsonx.ai access\n"
        f"  • Verify available models at: https://dataplatform.cloud.ibm.com"
    )
    # Do NOT set _HARD_ERROR here — model availability can change; let it retry
    logger.error(
        "[AgriBot] ❌  All models exhausted.\n%s\nLast traceback:\n%s",
        msg, traceback.format_exc(),
    )
    raise RuntimeError(msg)


def get_active_model_id() -> str:
    """Return currently active model ID. Triggers lazy init if needed."""
    try:
        _get_client()
        return _active_model_id or "unknown"
    except Exception as exc:
        logger.error("[AgriBot] get_active_model_id failed: %s", exc)
        return "unavailable"


def reset_client() -> None:
    """
    Clear the cached client and all error state.
    Call after fixing .env — next request will re-initialize.
    """
    global _client, _active_model_id, _HARD_ERROR, _SOFT_ERROR
    _client          = None
    _active_model_id = None
    _HARD_ERROR      = None
    _SOFT_ERROR      = None
    logger.info("[AgriBot] Client state reset — will re-initialize on next request.")


def generate(
    prompt: str,
    max_tokens: int = 800,
    temperature: float = 0.7,
    stop_sequences: Optional[list] = None,
) -> str:
    """
    Generate text from the active model.
    Raises RuntimeError with the full IBM error so callers can log/display it.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        client = _get_client()

    params: dict = {
        "max_new_tokens": max_tokens,
        "temperature": temperature,
        "repetition_penalty": 1.1,
    }
    if stop_sequences:
        params["stop_sequences"] = stop_sequences

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            response = client.generate_text(prompt=prompt, params=params)

        logger.debug("[AgriBot] generate_text response type=%s", type(response).__name__)

        if isinstance(response, str):
            return response.strip()
        if isinstance(response, dict):
            results = response.get("results", [])
            if results:
                return results[0].get("generated_text", "").strip()
            logger.warning("[AgriBot] Unexpected response keys: %s", list(response.keys()))
        return str(response).strip()

    except Exception as exc:
        tb_str = traceback.format_exc()
        logger.error(
            "[AgriBot] ❌  generate_text() failed.\n"
            "  model     : %s\n"
            "  exception : %s\n"
            "  traceback :\n%s",
            _active_model_id, str(exc), tb_str,
        )
        raise RuntimeError(
            f"IBM Watsonx.ai generation failed (model: {_active_model_id}).\n"
            f"Error: {exc}"
        ) from exc


def build_farming_prompt(
    user_message: str,
    context: str = "",
    chat_history: list = None,
    weather_info: str = "",
    soil_info: str = "",
    agent_instructions: str = "",
) -> str:
    """
    Build the prompt in the correct format for the active model.
    
    Llama 3 models use:  <|begin_of_text|><|start_header_id|>…<|eot_id|>
    Granite instruct:    <|system|>…<|end|>
    Other models:        Plain text with clear role labels
    """
    model = _active_model_id or ""

    if model in _LLAMA_MODELS or "llama" in model.lower():
        return _llama3_prompt(user_message, context, chat_history, weather_info, soil_info, agent_instructions)
    elif model in _GRANITE_INSTRUCT or "granite" in model.lower():
        return _granite_prompt(user_message, context, chat_history, weather_info, soil_info, agent_instructions)
    else:
        # Safe generic format that works for any text-completion model
        return _generic_prompt(user_message, context, chat_history, weather_info, soil_info, agent_instructions)


def _llama3_prompt(user_message, context, chat_history, weather_info, soil_info, agent_instructions) -> str:
    """Llama 3 instruct format."""
    # Build system content
    system_parts = [agent_instructions]
    if context:
        system_parts.append(f"Relevant agricultural knowledge:\n{context}")
    if weather_info:
        system_parts.append(f"Current weather data:\n{weather_info}")
    if soil_info:
        system_parts.append(f"Farmer soil data:\n{soil_info}")
    system_content = "\n\n".join(system_parts)

    parts = [
        "<|begin_of_text|>",
        f"<|start_header_id|>system<|end_header_id|>\n\n{system_content}<|eot_id|>",
    ]

    if chat_history:
        for turn in chat_history[-6:]:
            role    = turn.get("role", "user")
            content = turn.get("content", "")
            parts.append(f"<|start_header_id|>{role}<|end_header_id|>\n\n{content}<|eot_id|>")

    parts.append(f"<|start_header_id|>user<|end_header_id|>\n\n{user_message}<|eot_id|>")
    parts.append("<|start_header_id|>assistant<|end_header_id|>\n\n")
    return "".join(parts)


def _granite_prompt(user_message, context, chat_history, weather_info, soil_info, agent_instructions) -> str:
    """Granite instruct format."""
    parts = [f"<|system|>\n{agent_instructions}\n<|end|>"]
    if context:
        parts.append(f"<|system|>\nRelevant agricultural knowledge:\n{context}\n<|end|>")
    if weather_info:
        parts.append(f"<|system|>\nCurrent weather data:\n{weather_info}\n<|end|>")
    if soil_info:
        parts.append(f"<|system|>\nFarmer soil data:\n{soil_info}\n<|end|>")
    if chat_history:
        for turn in chat_history[-6:]:
            tag = "user" if turn.get("role") == "user" else "assistant"
            parts.append(f"<|{tag}|>\n{turn.get('content','')}\n<|end|>")
    parts.append(f"<|user|>\n{user_message}\n<|end|>")
    parts.append("<|assistant|>")
    return "\n".join(parts)


def _generic_prompt(user_message, context, chat_history, weather_info, soil_info, agent_instructions) -> str:
    """Plain-text prompt for base / unknown models."""
    lines = [f"SYSTEM: {agent_instructions}"]
    if context:
        lines.append(f"\nKNOWLEDGE:\n{context}")
    if weather_info:
        lines.append(f"\nWEATHER:\n{weather_info}")
    if soil_info:
        lines.append(f"\nSOIL:\n{soil_info}")
    if chat_history:
        lines.append("\nCONVERSATION:")
        for turn in chat_history[-6:]:
            role = turn.get("role","user").upper()
            lines.append(f"{role}: {turn.get('content','')}")
    lines.append(f"\nUSER: {user_message}")
    lines.append("ASSISTANT:")
    return "\n".join(lines)
