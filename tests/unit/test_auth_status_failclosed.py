"""
tests/unit/test_auth_status_failclosed.py — fail-closed account-status enforcement (H-3).

require_auth checks account_status + token_version on every request. Previously a
DB error while reading that row failed OPEN (the request proceeded), so a disabled
or token-revoked user could keep using a valid-but-stale JWT during any DB hiccup.

It now fails CLOSED: on a DB error it falls back to a short-lived per-process cache
of the last known status, and returns 503 when nothing is cached. These tests drive
a real access JWT through the decorator (not the X-Test-User-ID bypass) so the DB
status block actually runs.
"""
from unittest.mock import MagicMock, patch

import pytest
from flask import g, jsonify

from core.auth import (
    require_auth,
    create_jwt_token,
    _clear_auth_status_cache,
    _cache_auth_status,
    _get_cached_auth_status,
)


@require_auth
def _protected():
    return jsonify({"ok": True, "user": g.user_id})


def _status(resp):
    """require_auth's early returns are (body, code) tuples; success is a Response."""
    if isinstance(resp, tuple):
        return resp[1]
    return resp.status_code


def _mock_conn(fetchone_value):
    conn = MagicMock()
    conn.cursor().fetchone.return_value = fetchone_value
    return conn


def _call(app, token):
    """Invoke the protected view with a Bearer token under a request context."""
    with app.test_request_context("/x", headers={"Authorization": f"Bearer {token}"}):
        return _protected()


@pytest.fixture(autouse=True)
def _clean_cache():
    _clear_auth_status_cache()
    yield
    _clear_auth_status_cache()


class TestNormalDbPath:
    def test_active_user_with_matching_tv_passes(self, app):
        token = create_jwt_token("u1", role="student", token_version=0)
        with patch("core.database.get_db_connection", return_value=_mock_conn(("active", 0))):
            assert _status(_call(app, token)) == 200

    def test_disabled_user_403(self, app):
        token = create_jwt_token("u1", role="student", token_version=0)
        with patch("core.database.get_db_connection", return_value=_mock_conn(("disabled", 0))):
            assert _status(_call(app, token)) == 403

    def test_pending_approval_user_403(self, app):
        token = create_jwt_token("u1", role="student", token_version=0)
        conn = _mock_conn(("pending_approval", 0))
        with patch("core.database.get_db_connection", return_value=conn):
            assert _status(_call(app, token)) == 403

    def test_revoked_token_version_mismatch_401(self, app):
        token = create_jwt_token("u1", role="student", token_version=0)
        with patch("core.database.get_db_connection", return_value=_mock_conn(("active", 5))):
            assert _status(_call(app, token)) == 401

    def test_deleted_user_row_missing_401(self, app):
        token = create_jwt_token("u1", role="student", token_version=0)
        with patch("core.database.get_db_connection", return_value=_mock_conn(None)):
            assert _status(_call(app, token)) == 401


class TestFailClosedOnDbError:
    def test_db_error_no_cache_fails_closed_503(self, app):
        token = create_jwt_token("u1", role="student", token_version=0)
        with patch("core.database.get_db_connection", side_effect=Exception("db down")):
            assert _status(_call(app, token)) == 503

    def test_db_error_uses_cached_active_status(self, app):
        token = create_jwt_token("u1", role="student", token_version=0)
        # Warm the cache from a successful lookup.
        with patch("core.database.get_db_connection", return_value=_mock_conn(("active", 0))):
            assert _status(_call(app, token)) == 200
        # Now the DB is down — the cached "active" status carries the request.
        with patch("core.database.get_db_connection", side_effect=Exception("db down")):
            assert _status(_call(app, token)) == 200

    def test_db_error_cached_disabled_still_403(self, app):
        token = create_jwt_token("u1", role="student", token_version=0)
        with patch("core.database.get_db_connection", return_value=_mock_conn(("disabled", 0))):
            assert _status(_call(app, token)) == 403
        # A disabled user must stay blocked even when the DB later errors.
        with patch("core.database.get_db_connection", side_effect=Exception("db down")):
            assert _status(_call(app, token)) == 403

    def test_db_error_cached_tv_mismatch_still_401(self, app):
        token = create_jwt_token("u1", role="student", token_version=0)
        with patch("core.database.get_db_connection", return_value=_mock_conn(("active", 9))):
            assert _status(_call(app, token)) == 401
        with patch("core.database.get_db_connection", side_effect=Exception("db down")):
            assert _status(_call(app, token)) == 401


class TestCacheHelpers:
    def test_round_trip(self):
        _clear_auth_status_cache()
        _cache_auth_status("uX", "active", 2)
        assert _get_cached_auth_status("uX") == ("active", 2)

    def test_missing_returns_none(self):
        _clear_auth_status_cache()
        assert _get_cached_auth_status("nope") is None

    def test_expired_entry_returns_none(self, monkeypatch):
        import core.auth as auth_mod

        _clear_auth_status_cache()
        monkeypatch.setattr(auth_mod, "_AUTH_STATUS_STALE_GRACE", 30)
        clock = {"t": 1000.0}
        monkeypatch.setattr(auth_mod.time, "monotonic", lambda: clock["t"])
        _cache_auth_status("uX", "active", 0)  # cached_at = 1000
        clock["t"] = 1000.0 + 5  # within grace
        assert _get_cached_auth_status("uX") == ("active", 0)
        clock["t"] = 1000.0 + 31  # past the grace window
        assert _get_cached_auth_status("uX") is None
