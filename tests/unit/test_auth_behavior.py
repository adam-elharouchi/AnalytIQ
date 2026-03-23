"""
Behavioral tests: authentication service behaviors.

Tests the real auth paths — signup validation, signin, password checking —
not just import coverage.
"""
import pytest
from unittest.mock import MagicMock, patch
from core.auth import verify_password, hash_password


# ---------------------------------------------------------------------------
# verify_password
# ---------------------------------------------------------------------------


class TestVerifyPassword:
    def test_correct_bcrypt_password(self):
        hashed = hash_password("SecurePass1!")
        valid, needs_rehash = verify_password("SecurePass1!", hashed)
        assert valid is True
        assert needs_rehash is False

    def test_wrong_bcrypt_password(self):
        hashed = hash_password("SecurePass1!")
        valid, needs_rehash = verify_password("WrongPassword", hashed)
        assert valid is False
        assert needs_rehash is False

    def test_legacy_hash_valid(self):
        from core.auth import hash_password_legacy
        legacy = hash_password_legacy("OldPassword")
        valid, needs_rehash = verify_password("OldPassword", legacy)
        assert valid is True
        assert needs_rehash is True  # legacy match → must be re-hashed

    def test_legacy_hash_invalid(self):
        from core.auth import hash_password_legacy
        legacy = hash_password_legacy("OldPassword")
        valid, needs_rehash = verify_password("WrongPassword", legacy)
        assert valid is False
        assert needs_rehash is False


# ---------------------------------------------------------------------------
# Signup HTTP endpoint: password length enforcement
# ---------------------------------------------------------------------------


@pytest.fixture
def client(app):
    return app.test_client()


class TestSignupPasswordValidation:
    def test_password_too_short_returns_400(self, client, mock_db):
        resp = client.post(
            "/api/users/signup",
            json={"name": "Alice", "email": "alice@example.com", "password": "short"},
        )
        assert resp.status_code == 400
        assert "Password" in resp.get_json().get("error", "")

    def test_password_too_long_returns_400(self, client, mock_db):
        resp = client.post(
            "/api/users/signup",
            json={"name": "Alice", "email": "alice@example.com", "password": "x" * 73},
        )
        assert resp.status_code == 400
        assert "Password" in resp.get_json().get("error", "")

    def test_missing_fields_returns_400(self, client, mock_db):
        resp = client.post("/api/users/signup", json={"name": "Alice"})
        assert resp.status_code == 400

    def test_valid_signup_reaches_db(self, client, mock_db):
        """A well-formed signup must reach the DB insert step (mock returns data)."""
        uid = "new-user-id"
        # fetchone is called 3 times:
        #   1. email_exists check → None (no duplicate)
        #   2. find_tenant_by_email_domain → None (no tenant match)
        #   3. insert_user RETURNING → the new user row
        mock_db.cursor.return_value.fetchone.side_effect = [
            None,
            None,
            (uid, "Alice", "alice@example.com", "student"),
        ]
        resp = client.post(
            "/api/users/signup",
            json={"name": "Alice", "email": "alice@example.com", "password": "ValidPass1!"},
        )
        # DB mock returned a row → 200/201
        assert resp.status_code in (200, 201)


# ---------------------------------------------------------------------------
# Signin: returns 401 for wrong password
# ---------------------------------------------------------------------------


class TestSignin:
    def test_signin_with_wrong_password_returns_401(self, client, mock_db):
        import bcrypt

        pw_hash = bcrypt.hashpw(b"CorrectPass1!", bcrypt.gensalt()).decode()
        # get_user_by_email returns (user_id, name, email, password_hash, role, tenant_id)
        mock_db.cursor.return_value.fetchone.return_value = (
            "user-1", "Alice", "alice@example.com", pw_hash, "student", None,
        )
        resp = client.post(
            "/api/users/signin",
            json={"email": "alice@example.com", "password": "WrongPass"},
        )
        assert resp.status_code == 401

    def test_signin_with_unknown_email_returns_401(self, client, mock_db):
        mock_db.cursor.return_value.fetchone.return_value = None
        resp = client.post(
            "/api/users/signin",
            json={"email": "nobody@example.com", "password": "AnyPass1!"},
        )
        assert resp.status_code == 401

    def test_signin_missing_fields_returns_400(self, client, mock_db):
        resp = client.post("/api/users/signin", json={"email": "alice@example.com"})
        assert resp.status_code == 400


