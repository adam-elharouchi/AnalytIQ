"""
Integration tests — auth flows against a real Postgres database.

Tests exercise the repository layer (SQL) directly without HTTP overhead.
All tests roll back via the ``tx`` savepoint fixture.
"""

import bcrypt
import psycopg2
import pytest

from tests.integration.conftest import make_user_id
from repositories import auth_repository as auth_repo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _insert_user(conn, user_id, email, role="student"):
    pw_hash = bcrypt.hashpw(b"TestPass123!", bcrypt.gensalt()).decode()
    return auth_repo.insert_user(conn, user_id, "Test User", email, pw_hash, role)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSignupRepository:
    def test_insert_user_returns_tuple(self, tx):
        uid = make_user_id()
        row = _insert_user(tx, uid, f"{uid}@student.hult.edu")
        assert row is not None
        assert row[0] == uid  # user_id
        assert row[1] == "Test User"
        assert row[2] == f"{uid}@student.hult.edu"

    def test_insert_user_persisted(self, tx):
        uid = make_user_id()
        _insert_user(tx, uid, f"{uid}@student.hult.edu")

        with tx.cursor() as cur:
            cur.execute("SELECT user_id, role FROM users WHERE user_id = %s", (uid,))
            row = cur.fetchone()
        assert row is not None
        assert row[0] == uid

    def test_duplicate_email_raises_integrity_error(self, tx):
        uid1 = make_user_id()
        uid2 = make_user_id()
        email = f"{uid1}@student.hult.edu"
        _insert_user(tx, uid1, email)
        with pytest.raises(psycopg2.IntegrityError):
            _insert_user(tx, uid2, email)

    def test_default_profile_created(self, tx):
        uid = make_user_id()
        _insert_user(tx, uid, f"{uid}@student.hult.edu")
        auth_repo.create_default_profile(tx, uid)

        with tx.cursor() as cur:
            cur.execute("SELECT user_id FROM user_profiles WHERE user_id = %s", (uid,))
            row = cur.fetchone()
        assert row is not None

    def test_default_settings_created(self, tx):
        uid = make_user_id()
        _insert_user(tx, uid, f"{uid}@student.hult.edu")
        auth_repo.create_default_settings(tx, uid)

        with tx.cursor() as cur:
            cur.execute(
                "SELECT email_notifications FROM user_settings WHERE user_id = %s", (uid,)
            )
            row = cur.fetchone()
        assert row is not None
        assert row[0] is False  # default is False

    def test_default_preferences_created(self, tx):
        uid = make_user_id()
        _insert_user(tx, uid, f"{uid}@student.hult.edu")
        auth_repo.create_default_preferences(tx, uid)

        with tx.cursor() as cur:
            cur.execute(
                "SELECT current_language FROM user_preferences WHERE user_id = %s", (uid,)
            )
            row = cur.fetchone()
        assert row is not None
        assert row[0] == "python"

    def test_create_default_ai_digest(self, tx):
        uid = make_user_id()
        _insert_user(tx, uid, f"{uid}@student.hult.edu")
        auth_repo.create_default_ai_digest(tx, uid)

        with tx.cursor() as cur:
            cur.execute("SELECT user_id FROM ai_agent_digest WHERE user_id = %s", (uid,))
            row = cur.fetchone()
        assert row is not None

    def test_default_profile_idempotent(self, tx):
        """create_default_profile uses ON CONFLICT DO NOTHING — safe to call twice."""
        uid = make_user_id()
        _insert_user(tx, uid, f"{uid}@student.hult.edu")
        auth_repo.create_default_profile(tx, uid)
        auth_repo.create_default_profile(tx, uid)  # must not raise

        with tx.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM user_profiles WHERE user_id = %s", (uid,)
            )
            (n,) = cur.fetchone()
        assert n == 1


class TestEmailLookup:
    def test_email_exists_true(self, tx):
        uid = make_user_id()
        email = f"{uid}@student.hult.edu"
        _insert_user(tx, uid, email)
        assert auth_repo.email_exists(tx, email) is True

    def test_email_exists_false(self, tx):
        assert auth_repo.email_exists(tx, "nobody@nowhere.invalid") is False

    def test_get_user_by_email(self, tx):
        uid = make_user_id()
        email = f"{uid}@hult.edu"
        _insert_user(tx, uid, email, role="professor")

        row = auth_repo.get_user_by_email(tx, email)
        assert row is not None
        assert row[0] == uid  # user_id is first column


class TestPasswordReset:
    def test_insert_and_validate_reset_token(self, tx):
        from datetime import datetime, timedelta

        uid = make_user_id()
        email = f"{uid}@student.hult.edu"
        _insert_user(tx, uid, email)

        token = "tok_" + uid
        expires = datetime.utcnow() + timedelta(hours=1)
        auth_repo.insert_password_reset_token(tx, email, token, expires)

        row = auth_repo.validate_reset_token(tx, email, token, datetime.utcnow())
        assert row is not None

    def test_expired_token_is_invalid(self, tx):
        from datetime import datetime, timedelta

        uid = make_user_id()
        email = f"{uid}@student.hult.edu"
        _insert_user(tx, uid, email)

        token = "tok_expired_" + uid
        past = datetime.utcnow() - timedelta(hours=2)
        auth_repo.insert_password_reset_token(tx, email, token, past)

        row = auth_repo.validate_reset_token(tx, email, token, datetime.utcnow())
        assert row is None
