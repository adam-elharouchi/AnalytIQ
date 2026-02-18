"""
AI proxy blueprint.

Routes:
  POST /api/ai/chat
"""

import logging
import os
import threading
import time

import requests
from flask import Blueprint, g, jsonify, request

import config
from auth_helpers import require_auth
from extensions import csrf_exempt, limiter

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
            return jsonify({
                "error": f"Request payload too large. Maximum {config.MAX_AI_MESSAGE_LENGTH // 1024}KB allowed."
            }), 413

        contents = data.get("contents", [])
        if len(contents) > config.MAX_AI_CONVERSATION_MESSAGES:
            return jsonify({
                "error": f"Conversation too long. Maximum {config.MAX_AI_CONVERSATION_MESSAGES} messages allowed."
            }), 400

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return jsonify({"error": "Server configuration error: AI API Key missing"}), 500

        if _gemini_breaker.is_open():
            return jsonify({
                "error": "AI service is temporarily unavailable. Please try again in a minute."
            }), 503

        model = data.get("model", "gemini-2.5-flash")
        allowed_models = [
            "gemini-3-pro-preview",
            "gemini-3-flash-preview",
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-3-pro-image-preview",
        ]

        if model not in allowed_models:
            model = "gemini-2.5-flash"

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
