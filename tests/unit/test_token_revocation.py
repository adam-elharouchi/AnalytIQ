"""
tests/unit/test_token_revocation.py — JWT revocation via users.token_version (B1).

Every issued JWT embeds the user's token_version as a "tv" claim; require_auth
rejects a token whose tv no longer matches the stored counter. Bumping the
counter (password change/reset, admin force-reset, account disable) revokes all
outstanding tokens for that user.
"""
from unittest.mock import MagicMock

from core.auth import (
    create_jwt_token,
    decode_jwt_token,
    get_user_token_version,
    bump_user_token_version,
)


class TestTvClaim:
    def test_token_embeds_tv_claim(self):
        tok = create_jwt_token("u1", role="student", token_version=3)
        assert decode_jwt_token(tok)["tv"] == 3

    def test_token_defaults_tv_zero(self):
        tok = create_jwt_token("u1", role="student")
        assert decode_jwt_token(tok)["tv"] == 0

    def test_none_token_version_coerced_to_zero(self):
        tok = create_jwt_token("u1", role="student", token_version=None)
        assert decode_jwt_token(tok)["tv"] == 0


class TestGetTokenVersion:
    def test_returns_stored_value(self):
        conn = MagicMock()
        conn.cursor().fetchone.return_value = (5,)
        assert get_user_token_version(conn, "u1") == 5

    def test_missing_row_returns_zero(self):
        conn = MagicMock()
        conn.cursor().fetchone.return_value = None
        assert get_user_token_version(conn, "u1") == 0

    def test_db_error_returns_zero_and_rolls_back(self):
        conn = MagicMock()
        conn.cursor.side_effect = Exception("no such column: token_version")
        assert get_user_token_version(conn, "u1") == 0
        conn.rollback.assert_called_once()


class TestBumpTokenVersion:
    def test_issues_increment_update(self):
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value = cur
        assert bump_user_token_version(conn, "u1") is True
        sql = cur.execute.call_args[0][0]
        assert "token_version" in sql and "+ 1" in sql

    def test_error_returns_false_and_rolls_back(self):
        conn = MagicMock()
        conn.cursor.side_effect = Exception("boom")
        assert bump_user_token_version(conn, "u1") is False
        conn.rollback.assert_called_once()
