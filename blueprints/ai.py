"""
AI proxy blueprint.

Routes:
  POST /api/ai/chat
"""

import logging
import os

import requests
from flask import Blueprint, jsonify, request

from auth_helpers import require_auth
from extensions import csrf_exempt

logger = logging.getLogger(__name__)
bp = Blueprint("ai", __name__)


@bp.route("/api/ai/chat", methods=["POST"])
@csrf_exempt
@require_auth
def proxy_ai_chat():
    """Secure proxy for Gemini Chat API."""
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return jsonify({"error": "Server configuration error: AI API Key missing"}), 500

        data = request.json
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
            return jsonify(response.json()), response.status_code

        return jsonify(response.json())

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500
