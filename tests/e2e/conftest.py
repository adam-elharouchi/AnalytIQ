"""
E2E test fixtures for AnalytIQ.

Requires a running app:  FLASK_ENV=testing python app.py
Run with:               pytest tests/e2e/ -m e2e -v
"""
import uuid
import pytest
import requests


BASE_URL = "http://localhost:5000"
API_URL = f"{BASE_URL}/api"


def _unique_id():
    return uuid.uuid4().hex[:8]


def _signup_and_login(email: str, password: str, name: str) -> str:
    """Sign up then sign in, return JWT token."""
    r = requests.post(f"{API_URL}/users/signup", json={"name": name, "email": email, "password": password}, timeout=10)
    assert r.status_code in (201, 400), f"Unexpected signup status {r.status_code}: {r.text}"
    # 400 means already exists — proceed to signin
    r = requests.post(f"{API_URL}/users/signin", json={"email": email, "password": password}, timeout=10)
    assert r.status_code == 200, f"Signin failed {r.status_code}: {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def api_url():
    return API_URL


@pytest.fixture(scope="session")
def professor_token():
    uid = _unique_id()
    email = f"prof_{uid}@hult.edu"
    return _signup_and_login(email, "testpass123", f"Prof {uid}")


@pytest.fixture(scope="session")
def student_token():
    uid = _unique_id()
    email = f"student_{uid}@student.hult.edu"
    return _signup_and_login(email, "testpass123", f"Student {uid}")


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
