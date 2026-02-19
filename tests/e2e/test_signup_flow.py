"""
E2E: Signup and signin flows.
Requires a running app: FLASK_ENV=testing python app.py
"""
import uuid
import pytest
import requests

from conftest import API_URL, auth_headers


pytestmark = pytest.mark.e2e


def _uid():
    return uuid.uuid4().hex[:8]


class TestSignup:
    def test_professor_signup_returns_201(self):
        uid = _uid()
        r = requests.post(
            f"{API_URL}/users/signup",
            json={"name": f"Prof {uid}", "email": f"prof_{uid}@hult.edu", "password": "testpass123"},
            timeout=10,
        )
        assert r.status_code == 201
        body = r.json()
        assert "token" in body
        assert body["user"]["role"] == "professor"

    def test_student_signup_returns_201(self):
        uid = _uid()
        r = requests.post(
            f"{API_URL}/users/signup",
            json={"name": f"Student {uid}", "email": f"student_{uid}@student.hult.edu", "password": "testpass123"},
            timeout=10,
        )
        assert r.status_code == 201
        body = r.json()
        assert "token" in body
        assert body["user"]["role"] == "student"

    def test_duplicate_email_returns_400(self):
        uid = _uid()
        payload = {"name": f"Dup {uid}", "email": f"dup_{uid}@hult.edu", "password": "testpass123"}
        r1 = requests.post(f"{API_URL}/users/signup", json=payload, timeout=10)
        assert r1.status_code == 201
        r2 = requests.post(f"{API_URL}/users/signup", json=payload, timeout=10)
        assert r2.status_code == 400
        assert "already" in r2.json().get("error", "").lower()

    def test_short_password_returns_400(self):
        uid = _uid()
        r = requests.post(
            f"{API_URL}/users/signup",
            json={"name": f"Short {uid}", "email": f"short_{uid}@hult.edu", "password": "abc"},
            timeout=10,
        )
        assert r.status_code == 400

    def test_missing_fields_returns_400(self):
        r = requests.post(f"{API_URL}/users/signup", json={"email": "nope@hult.edu"}, timeout=10)
        assert r.status_code == 400


class TestSignin:
    def test_valid_credentials_returns_token(self):
        uid = _uid()
        email = f"signin_{uid}@hult.edu"
        requests.post(
            f"{API_URL}/users/signup",
            json={"name": f"Signin {uid}", "email": email, "password": "testpass123"},
            timeout=10,
        )
        r = requests.post(f"{API_URL}/users/signin", json={"email": email, "password": "testpass123"}, timeout=10)
        assert r.status_code == 200
        assert "token" in r.json()

    def test_wrong_password_returns_401(self):
        uid = _uid()
        email = f"wrongpw_{uid}@hult.edu"
        requests.post(
            f"{API_URL}/users/signup",
            json={"name": f"Wrong {uid}", "email": email, "password": "testpass123"},
            timeout=10,
        )
        r = requests.post(f"{API_URL}/users/signin", json={"email": email, "password": "wrongpassword"}, timeout=10)
        assert r.status_code == 401

    def test_unknown_email_returns_401(self):
        r = requests.post(
            f"{API_URL}/users/signin",
            json={"email": "nobody_xyz_12345@hult.edu", "password": "testpass123"},
            timeout=10,
        )
        assert r.status_code == 401

    def test_no_auth_header_on_protected_route(self):
        r = requests.get(f"{API_URL}/classes", timeout=10)
        assert r.status_code == 401
