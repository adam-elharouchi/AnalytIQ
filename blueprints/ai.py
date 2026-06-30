"""
AI proxy blueprint.

Routes:
  POST /api/ai/chat
  GET  /api/ai/models
"""

import logging
import threading
import time

import requests
from flask import Blueprint, g, jsonify, request

import config
from core.auth import require_auth
from core.extensions import csrf_exempt, limiter

logger = logging.getLogger(__name__)


class _CircuitBreaker:
    """Open after THRESHOLD consecutive Gemini failures; auto-reset after RECOVERY_SECS."""

    _THRESHOLD = 5
    _RECOVERY_SECS = 60

    def __init__(self):
        self._lock = threading.Lock()
        self._failures = 0
        self._opened_at = 0.0
        self._open = False

    def is_open(self):
        with self._lock:
            if self._open:
                if time.monotonic() - self._opened_at >= self._RECOVERY_SECS:
                    self._open = False  # half-open: allow one probe
                    return False
                return True
            return False

    def record_success(self):
        with self._lock:
            self._failures = 0
            self._open = False

    def record_failure(self):
        with self._lock:
            self._failures += 1
            if self._failures >= self._THRESHOLD:
                self._open = True
                self._opened_at = time.monotonic()


_gemini_breaker = _CircuitBreaker()

bp = Blueprint("ai", __name__)


def _get_ai_user_id():
    """Rate-limit key: authenticated user_id (set by @require_auth via g.user_id)."""
    return getattr(g, "user_id", None) or "anonymous"


def _apply_ai_rate_limits(f):
    """Apply per-user rate limits; no-op when Flask-Limiter is unavailable."""
    if limiter is None:
        return f
    f = limiter.limit("100 per hour", key_func=_get_ai_user_id)(f)
    f = limiter.limit("20 per minute", key_func=_get_ai_user_id)(f)
    return f


@bp.route("/api/ai/chat", methods=["POST"])
@csrf_exempt
@require_auth
@_apply_ai_rate_limits
def proxy_ai_chat():
    """Secure proxy for Gemini Chat API."""
    try:
        data = request.json or {}

        # Input validation first (before API key check — no external dependency needed)
        payload_bytes = request.content_length or 0
        if payload_bytes > config.MAX_AI_MESSAGE_LENGTH:
            return (
                jsonify(
                    {
                        "error": f"Request payload too large. Maximum {config.MAX_AI_MESSAGE_LENGTH // 1024}KB allowed."
                    }
                ),
                413,
            )

        contents = data.get("contents", [])
        if len(contents) > config.MAX_AI_CONVERSATION_MESSAGES:
            return (
                jsonify(
                    {
                        "error": f"Conversation too long. Maximum {config.MAX_AI_CONVERSATION_MESSAGES} messages allowed."
                    }
                ),
                400,
            )

        api_key = config.GEMINI_API_KEY
        if not api_key:
            return jsonify({"error": "Server configuration error: AI API Key missing"}), 500

        if _gemini_breaker.is_open():
            return (
                jsonify(
                    {
                        "error": "AI service is temporarily unavailable. Please try again in a minute."
                    }
                ),
                503,
            )

        model = data.get("model", "gemini-flash-latest")
        if not isinstance(model, str) or not model.startswith("gemini-"):
            model = "gemini-flash-latest"

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models"
            f"/{model}:generateContent?key={api_key}"
        )

        google_payload = {
            "contents": data.get("contents", []),
            "generationConfig": data.get("generationConfig", {}),
        }

        response = requests.post(
            url,
            json=google_payload,
            headers={"Content-Type": "application/json"},
            timeout=60,
        )

        if not response.ok:
            _gemini_breaker.record_failure()
            return jsonify(response.json()), response.status_code

        _gemini_breaker.record_success()
        return jsonify(response.json())

    except requests.exceptions.Timeout:
        _gemini_breaker.record_failure()
        logger.error("Gemini request timed out")
        return jsonify({"error": "AI service timed out. Please try again."}), 504
    except requests.exceptions.RequestException as e:
        _gemini_breaker.record_failure()
        logger.error("Gemini request failed: %s", e, exc_info=True)
        return jsonify({"error": "AI service is temporarily unavailable. Please try again."}), 503
    except Exception as e:
        logger.error("Unexpected error in AI chat: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


# ---------------------------------------------------------------------------
# Model discovery
# ---------------------------------------------------------------------------

_MODELS_CACHE: dict = {"data": None, "fetched_at": 0.0}
_MODELS_CACHE_TTL = 300  # 5 minutes

_FALLBACK_MODELS = [
    {"id": "gemini-flash-latest", "display_name": "Gemini Flash (latest)"},
    {"id": "gemini-3.5-flash",    "display_name": "Gemini 3.5 Flash"},
    {"id": "gemini-3.1-pro",      "display_name": "Gemini 3.1 Pro"},
    {"id": "gemini-3.1-flash-lite","display_name": "Gemini 3.1 Flash-Lite"},
    {"id": "gemini-2.5-pro",      "display_name": "Gemini 2.5 Pro"},
    {"id": "gemini-2.5-flash",    "display_name": "Gemini 2.5 Flash"},
]


def _fetch_gemini_models(api_key: str) -> list:
    """Call Gemini models.list and return chat-capable models, newest first."""
    resp = requests.get(
        "https://generativelanguage.googleapis.com/v1beta/models",
        params={"key": api_key},
        timeout=10,
    )
    resp.raise_for_status()
    raw = resp.json().get("models", [])
    models = []
    for m in raw:
        name = m.get("name", "")          # "models/gemini-3.5-flash"
        model_id = name.removeprefix("models/")
        if not model_id.startswith("gemini-"):
            continue
        if "generateContent" not in m.get("supportedGenerationMethods", []):
            continue
        models.append({
            "id": model_id,
            "display_name": m.get("displayName", model_id),
        })
    # Sort: latest aliases first, then by id descending
    aliases = [m for m in models if m["id"].endswith("-latest")]
    versioned = sorted(
        [m for m in models if not m["id"].endswith("-latest")],
        key=lambda m: m["id"],
        reverse=True,
    )
    return aliases + versioned


@bp.route("/api/ai/models", methods=["GET"])
@csrf_exempt
@require_auth
def list_ai_models():
    """Return available Gemini models, cached for 5 minutes."""
    now = time.monotonic()
    if _MODELS_CACHE["data"] and now - _MODELS_CACHE["fetched_at"] < _MODELS_CACHE_TTL:
        return jsonify({"models": _MODELS_CACHE["data"], "cached": True})

    api_key = config.GEMINI_API_KEY
    if not api_key:
        return jsonify({"models": _FALLBACK_MODELS, "cached": False, "source": "fallback"})

    try:
        models = _fetch_gemini_models(api_key)
        _MODELS_CACHE["data"] = models
        _MODELS_CACHE["fetched_at"] = now
        return jsonify({"models": models, "cached": False})
    except Exception as e:
        logger.warning("Failed to fetch Gemini model list: %s", e)
        return jsonify({"models": _FALLBACK_MODELS, "cached": False, "source": "fallback"})
