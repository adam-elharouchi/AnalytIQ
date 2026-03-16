"""
tests/test_ai_routes.py — Behavioral tests for AI proxy route.

Covers:
  POST /api/ai/chat
    - Success path (mock Gemini response)
    - Missing messages (empty contents)
    - Payload too large (413)
    - Too many messages (400)
    - No auth (401)
    - Invalid / unsupported model falls back to default
"""
import json
import pytest
from unittest.mock import patch, MagicMock

AUTH = {"X-Test-User-ID": "student-user-id", "X-Test-User-Role": "student"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _post_chat(client, payload, headers=None):
    if headers is None:
        headers = AUTH
    return client.post("/api/ai/chat", headers=headers, json=payload)


def _mock_gemini_ok():
    """Return a successful mock response from the Gemini API."""
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "Here is your answer."}],
                    "role": "model",
                }
            }
        ]
    }
    mock_response.status_code = 200
    return mock_response


# ---------------------------------------------------------------------------
# POST /api/ai/chat
# ---------------------------------------------------------------------------

class TestAiChat:
    def test_success_returns_gemini_response(self, client, mock_db):
        """Valid request is proxied to Gemini and response is forwarded."""
        with patch("os.getenv", side_effect=lambda k, d=None: "fake-api-key" if k == "GEMINI_API_KEY" else d), \
             patch("requests.post", return_value=_mock_gemini_ok()):

            resp = _post_chat(client, {
                "contents": [{"role": "user", "parts": [{"text": "Hello"}]}],
            })

        assert resp.status_code == 200
        data = resp.get_json()
        assert "candidates" in data

    def test_no_auth_returns_401(self, client, mock_db):
        """Request without auth header returns 401."""
        resp = client.post("/api/ai/chat", json={
            "contents": [{"role": "user", "parts": [{"text": "Hello"}]}],
        })

        assert resp.status_code == 401

    def test_too_many_messages_returns_400(self, client, mock_db):
        """More than MAX_AI_CONVERSATION_MESSAGES messages returns 400."""
        # config.MAX_AI_CONVERSATION_MESSAGES = 100
        messages = [{"role": "user", "parts": [{"text": "msg"}]}] * 101

        resp = _post_chat(client, {"contents": messages})

        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data
        assert "long" in data["error"].lower() or "maximum" in data["error"].lower()

    def test_missing_api_key_returns_500(self, client, mock_db):
        """When GEMINI_API_KEY is not set, returns 500 configuration error."""
        with patch("os.getenv", side_effect=lambda k, d=None: None if k == "GEMINI_API_KEY" else d):
            resp = _post_chat(client, {
                "contents": [{"role": "user", "parts": [{"text": "Hello"}]}],
            })

        assert resp.status_code == 500
        data = resp.get_json()
        assert "error" in data

    def test_unsupported_model_falls_back_to_default(self, client, mock_db):
        """Unknown model name is silently overridden with default model."""
        with patch("os.getenv", side_effect=lambda k, d=None: "fake-api-key" if k == "GEMINI_API_KEY" else d), \
             patch("requests.post", return_value=_mock_gemini_ok()) as mock_post:

            _post_chat(client, {
                "model": "gpt-99-ultra",
                "contents": [{"role": "user", "parts": [{"text": "Hi"}]}],
            })

        # The URL must contain the fallback model name
        if mock_post.called:
            called_url = mock_post.call_args[0][0]
            # The default model should be in the URL
            assert "gemini" in called_url

    def test_gemini_error_forwarded_to_client(self, client, mock_db):
        """When Gemini returns an error, it is forwarded with the same status."""
        mock_err_response = MagicMock()
        mock_err_response.ok = False
        mock_err_response.status_code = 429
        mock_err_response.json.return_value = {"error": {"message": "Rate limit exceeded"}}

        with patch("os.getenv", side_effect=lambda k, d=None: "fake-api-key" if k == "GEMINI_API_KEY" else d), \
             patch("requests.post", return_value=mock_err_response):

            resp = _post_chat(client, {
                "contents": [{"role": "user", "parts": [{"text": "Hello"}]}],
            })

        assert resp.status_code == 429

    def test_payload_with_empty_contents_allowed(self, client, mock_db):
        """Empty contents list does not exceed the limit — request goes through."""
        with patch("os.getenv", side_effect=lambda k, d=None: "fake-api-key" if k == "GEMINI_API_KEY" else d), \
             patch("requests.post", return_value=_mock_gemini_ok()):

            resp = _post_chat(client, {"contents": []})

        # Either succeeds or fails with a meaningful error (not a 413 for empty payload)
        assert resp.status_code != 413

    def test_large_single_message_returns_413(self, client, mock_db):
        """A request with content_length exceeding 50KB returns 413."""
        # Simulate a large request by setting content_length header
        large_content = "x" * 60000
        large_payload = json.dumps({
            "contents": [{"role": "user", "parts": [{"text": large_content}]}]
        }).encode()

        with patch("os.getenv", side_effect=lambda k, d=None: "fake-api-key" if k == "GEMINI_API_KEY" else d):
            resp = client.post(
                "/api/ai/chat",
                headers={**AUTH, "Content-Type": "application/json"},
                data=large_payload,
            )

        assert resp.status_code == 413
        data = resp.get_json()
        assert "error" in data
        assert "large" in data["error"].lower() or "kb" in data["error"].lower()
