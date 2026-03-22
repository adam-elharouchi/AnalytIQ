"""
Behavioral tests: AI chat endpoint.

Covers payload cap (13A) and rate-limit plumbing (16A) without needing a
live Gemini API key.
"""
import json
import pytest
from unittest.mock import patch


@pytest.fixture
def client(app):
    return app.test_client()


def _auth_headers(user_id="u1", role="student"):
    return {"X-Test-User-ID": user_id, "X-Test-User-Role": role}


class TestAiChatPayloadCap:
    def test_oversized_body_returns_413(self, client):
        """Bodies larger than MAX_AI_MESSAGE_LENGTH (50 KB) get rejected before
        the Gemini call."""
        big_message = "x" * 60_000  # > 50 KB
        payload = json.dumps({"contents": [{"role": "user", "parts": [{"text": big_message}]}]})

        resp = client.post(
            "/api/ai/chat",
            data=payload,
            content_type="application/json",
            headers=_auth_headers(),
            content_length=len(payload),
        )
        assert resp.status_code == 413

    def test_too_many_messages_returns_400(self, client):
        """Conversations with > 100 messages are rejected."""
        messages = [{"role": "user", "parts": [{"text": "hi"}]}] * 101
        resp = client.post(
            "/api/ai/chat",
            json={"contents": messages},
            headers=_auth_headers(),
        )
        assert resp.status_code == 400
        body = resp.get_json()
        assert "Conversation too long" in body.get("error", "")

    def test_missing_api_key_returns_500(self, client):
        """When GEMINI_API_KEY is absent the handler returns 500 with a clear error."""
        with patch("config.GEMINI_API_KEY", None):
            resp = client.post(
                "/api/ai/chat",
                json={"contents": [{"role": "user", "parts": [{"text": "hello"}]}]},
                headers=_auth_headers(),
            )
        assert resp.status_code == 500

    def test_unauthenticated_returns_401(self, client):
        resp = client.post(
            "/api/ai/chat",
            json={"contents": [{"role": "user", "parts": [{"text": "hi"}]}]},
        )
        assert resp.status_code == 401


class TestAiChatRateLimitConfig:
    def test_rate_limit_key_func_uses_user_id(self):
        """The _get_ai_user_id helper reads g.user_id, not a global key."""
        from blueprints.ai import _get_ai_user_id
        from flask import g

        # Simulate an app context with g.user_id set
        import app as app_module
        with app_module.app.app_context():
            g.user_id = "rate-limit-test-user"
            assert _get_ai_user_id() == "rate-limit-test-user"
