"""
E2E: AI chat proxy flows.
Requires a running app: FLASK_ENV=testing python app.py
Note: these tests hit the real Gemini API unless the app stubs it.
"""
import pytest
import requests

from conftest import API_URL, auth_headers


pytestmark = pytest.mark.e2e

_VALID_MSG = [{"role": "user", "parts": [{"text": "What is a pandas DataFrame in one sentence?"}]}]


class TestAiChatFlow:
    def test_valid_message_returns_200(self, professor_token):
        r = requests.post(
            f"{API_URL}/ai/chat",
            json={"contents": _VALID_MSG, "model": "gemini-2.0-flash"},
            headers=auth_headers(professor_token),
            timeout=30,
        )
        # 200 = success, 503 = Gemini unavailable in test env — both acceptable
        assert r.status_code in (200, 503), f"Unexpected: {r.status_code} {r.text}"

    def test_empty_contents_returns_400(self, professor_token):
        r = requests.post(
            f"{API_URL}/ai/chat",
            json={"contents": [], "model": "gemini-2.0-flash"},
            headers=auth_headers(professor_token),
            timeout=10,
        )
        assert r.status_code == 400

    def test_missing_contents_key_returns_400(self, professor_token):
        r = requests.post(
            f"{API_URL}/ai/chat",
            json={"model": "gemini-2.0-flash"},
            headers=auth_headers(professor_token),
            timeout=10,
        )
        assert r.status_code == 400

    def test_oversized_payload_returns_413_or_400(self, professor_token):
        # Build a payload > 50KB
        big_text = "x" * 60_000
        r = requests.post(
            f"{API_URL}/ai/chat",
            json={"contents": [{"role": "user", "parts": [{"text": big_text}]}], "model": "gemini-2.0-flash"},
            headers=auth_headers(professor_token),
            timeout=10,
        )
        assert r.status_code in (400, 413), f"Expected 400/413, got {r.status_code}"

    def test_too_many_messages_returns_400(self, professor_token):
        messages = [{"role": "user", "parts": [{"text": f"msg {i}"}]} for i in range(101)]
        r = requests.post(
            f"{API_URL}/ai/chat",
            json={"contents": messages, "model": "gemini-2.0-flash"},
            headers=auth_headers(professor_token),
            timeout=10,
        )
        assert r.status_code == 400

    def test_unauthenticated_request_returns_401(self):
        r = requests.post(
            f"{API_URL}/ai/chat",
            json={"contents": _VALID_MSG, "model": "gemini-2.0-flash"},
            timeout=10,
        )
        assert r.status_code == 401
