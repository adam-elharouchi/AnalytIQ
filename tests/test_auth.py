"""
tests/test_auth.py — Behavioral tests for auth routes.

Covers:
  POST /api/users/signup
  POST /api/users/signin
  POST /api/users/forgot-password
  POST /api/users/reset-password
"""
import pytest
import bcrypt
from datetime import datetime, timedelta
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_bcrypt_hash(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


# ---------------------------------------------------------------------------
# POST /api/users/signup
# ---------------------------------------------------------------------------

class TestSignup:
    def test_signup_success_returns_201_and_token(self, client, mock_db):
        """Successful signup returns 201 with a token key in the body."""
        # email_exists -> None (no existing user); insert_user -> row
        cursor = mock_db.cursor()
        cursor.fetchone.side_effect = [
            None,  # email_exists check
            ("new-user-id", "Alice", "alice@student.hult.edu", "student", False),  # insert_user
        ]

        resp = client.post(
            "/api/users/signup",
            json={
                "name": "Alice",
                "email": "alice@student.hult.edu",
                "password": "securePass1",
            },
        )

        assert resp.status_code == 201
        data = resp.get_json()
        assert "token" in data
        assert data["success"] is True

    def test_signup_professor_role_detected_from_email(self, client, mock_db):
        """@hult.edu email gets professor role in the response."""
        cursor = mock_db.cursor()
        cursor.fetchone.side_effect = [
            None,
            ("prof-id", "Prof Bob", "bob@hult.edu", "professor", False),
        ]

        resp = client.post(
            "/api/users/signup",
            json={
                "name": "Prof Bob",
                "email": "bob@hult.edu",
                "password": "securePass1",
            },
        )

        assert resp.status_code == 201
        data = resp.get_json()
        assert data["role"] == "professor"

    def test_signup_analytiq_org_role_detected_from_email(self, client, mock_db):
        """@myanalytiq.org email gets professor role in the response."""
        cursor = mock_db.cursor()
        cursor.fetchone.side_effect = [
            None,
            ("admin-id", "Admin Sam", "sam@myanalytiq.org", "professor", True),
        ]

        resp = client.post(
            "/api/users/signup",
            json={
                "name": "Admin Sam",
                "email": "sam@myanalytiq.org",
                "password": "securePass1",
            },
        )

        assert resp.status_code == 201
        data = resp.get_json()
        assert data["role"] == "professor"

    def test_signup_missing_name_returns_400(self, client, mock_db):
        """Missing name field returns 400 with an error key."""
        resp = client.post(
            "/api/users/signup",
            json={"email": "x@example.com", "password": "securePass1"},
        )
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_signup_missing_email_returns_400(self, client, mock_db):
        """Missing email field returns 400."""
        resp = client.post(
            "/api/users/signup",
            json={"name": "Alice", "password": "securePass1"},
        )
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_signup_missing_password_returns_400(self, client, mock_db):
        """Missing password field returns 400."""
        resp = client.post(
            "/api/users/signup",
            json={"name": "Alice", "email": "alice@example.com"},
        )
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_signup_password_too_short_returns_400(self, client, mock_db):
        """Password shorter than MIN_PASSWORD_LENGTH (8) is rejected with 400."""
        resp = client.post(
            "/api/users/signup",
            json={"name": "Alice", "email": "alice@example.com", "password": "abc"},
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data
        assert "8" in data["error"]  # mentions minimum length

    def test_signup_password_too_long_returns_400(self, client, mock_db):
        """Password longer than MAX_PASSWORD_LENGTH (72) is rejected with 400."""
        long_pw = "a" * 73
        resp = client.post(
            "/api/users/signup",
            json={"name": "Alice", "email": "alice@example.com", "password": long_pw},
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data
        assert "72" in data["error"]

    def test_signup_email_already_registered_returns_400(self, client, mock_db):
        """Duplicate email returns 400 with 'already registered' message."""
        cursor = mock_db.cursor()
        # email_exists -> existing row
        cursor.fetchone.return_value = ("existing-user-id",)

        resp = client.post(
            "/api/users/signup",
            json={"name": "Alice", "email": "existing@example.com", "password": "securePass1"},
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "already registered" in data["error"].lower()


# ---------------------------------------------------------------------------
# POST /api/users/signin
# ---------------------------------------------------------------------------

class TestSignin:
    def test_signin_success_returns_200_and_token(self, client, mock_db):
        """Valid credentials return 200 with a token."""
        password_hash = _make_bcrypt_hash("correctPass1")
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (
            "user123", "Alice", "alice@example.com", password_hash, "student"
        )

        resp = client.post(
            "/api/users/signin",
            json={"email": "alice@example.com", "password": "correctPass1"},
        )

        assert resp.status_code == 200
        data = resp.get_json()
        assert "token" in data
        assert data["user_id"] == "user123"

    def test_signin_wrong_password_returns_401(self, client, mock_db):
        """Wrong password returns 401 with an error message."""
        password_hash = _make_bcrypt_hash("correctPass1")
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (
            "user123", "Alice", "alice@example.com", password_hash, "student"
        )

        resp = client.post(
            "/api/users/signin",
            json={"email": "alice@example.com", "password": "wrongPass1"},
        )

        assert resp.status_code == 401
        data = resp.get_json()
        assert "error" in data

    def test_signin_unknown_email_returns_401(self, client, mock_db):
        """Non-existent email returns 401."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None

        resp = client.post(
            "/api/users/signin",
            json={"email": "nobody@example.com", "password": "anyPass1"},
        )

        assert resp.status_code == 401
        assert "error" in resp.get_json()

    def test_signin_missing_email_returns_400(self, client, mock_db):
        """Missing email returns 400."""
        resp = client.post(
            "/api/users/signin",
            json={"password": "somePass1"},
        )
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_signin_missing_password_returns_400(self, client, mock_db):
        """Missing password returns 400."""
        resp = client.post(
            "/api/users/signin",
            json={"email": "alice@example.com"},
        )
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_signin_response_includes_user_fields(self, client, mock_db):
        """Successful signin response contains id, name, email, role."""
        password_hash = _make_bcrypt_hash("pass12345")
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (
            "usr-abc", "Bob", "bob@example.com", password_hash, "professor"
        )

        resp = client.post(
            "/api/users/signin",
            json={"email": "bob@example.com", "password": "pass12345"},
        )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["name"] == "Bob"
        assert data["email"] == "bob@example.com"
        assert data["role"] == "professor"


# ---------------------------------------------------------------------------
# POST /api/users/forgot-password
# ---------------------------------------------------------------------------

class TestForgotPassword:
    def test_forgot_password_existing_user_returns_200(self, client, mock_db):
        """Existing user triggers reset flow but always returns 200 (security)."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = ("user123", "Alice")

        resp = client.post(
            "/api/users/forgot-password",
            json={"email": "alice@example.com"},
        )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True

    def test_forgot_password_unknown_email_still_returns_200(self, client, mock_db):
        """Non-existent email still returns 200 to prevent email enumeration."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None

        resp = client.post(
            "/api/users/forgot-password",
            json={"email": "nobody@example.com"},
        )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True

    def test_forgot_password_missing_email_returns_400(self, client, mock_db):
        """Missing email field returns 400."""
        resp = client.post(
            "/api/users/forgot-password",
            json={},
        )
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_forgot_password_response_has_message(self, client, mock_db):
        """Response body has a 'message' key explaining what happened."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None

        resp = client.post(
            "/api/users/forgot-password",
            json={"email": "test@example.com"},
        )

        assert resp.status_code == 200
        data = resp.get_json()
        assert "message" in data


# ---------------------------------------------------------------------------
# POST /api/users/reset-password
# ---------------------------------------------------------------------------

class TestResetPassword:
    def test_reset_password_success_returns_200(self, client, mock_db):
        """Valid token resets password and returns 200."""
        cursor = mock_db.cursor()
        # validate_reset_token -> valid row
        cursor.fetchone.return_value = ("test@example.com",)

        resp = client.post(
            "/api/users/reset-password",
            json={
                "token": "valid-token-abc",
                "email": "test@example.com",
                "newPassword": "newPass123",
            },
        )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True

    def test_reset_password_invalid_token_returns_400(self, client, mock_db):
        """Invalid or expired token returns 400."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None  # token not found

        resp = client.post(
            "/api/users/reset-password",
            json={
                "token": "bogus-token",
                "email": "test@example.com",
                "newPassword": "newPass123",
            },
        )

        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data

    def test_reset_password_short_password_returns_400(self, client, mock_db):
        """New password shorter than 8 chars is rejected with 400."""
        resp = client.post(
            "/api/users/reset-password",
            json={
                "token": "some-token",
                "email": "test@example.com",
                "newPassword": "abc",
            },
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data
        assert "8" in data["error"]

    def test_reset_password_missing_fields_returns_400(self, client, mock_db):
        """Missing token, email, or newPassword returns 400."""
        resp = client.post(
            "/api/users/reset-password",
            json={"email": "test@example.com"},
        )
        assert resp.status_code == 400
        assert "error" in resp.get_json()
