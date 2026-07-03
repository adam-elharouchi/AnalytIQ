"""
tests/unit/test_hardening_batch.py — H-6 (client IP) + H-4 (login timing).
"""
from core.auth import DUMMY_PASSWORD_HASH
from core.extensions import get_client_ip


class TestGetClientIp:
    def test_prefers_cf_connecting_ip(self, app):
        with app.test_request_context(
            headers={"CF-Connecting-IP": "1.2.3.4", "X-Forwarded-For": "9.9.9.9, 8.8.8.8"}
        ):
            # Not the (spoofable) leftmost XFF — the Cloudflare-set client IP.
            assert get_client_ip() == "1.2.3.4"

    def test_falls_back_to_remote_addr(self, app):
        with app.test_request_context(environ_base={"REMOTE_ADDR": "5.6.7.8"}):
            assert get_client_ip() == "5.6.7.8"


class TestSigninTiming:
    def test_unknown_email_runs_dummy_bcrypt(self, client, mock_db, monkeypatch):
        """An unknown email must still trigger a bcrypt comparison so the response
        time matches the 'user exists' path (no enumeration via timing)."""
        captured = {}

        def spy(pw, h):
            captured["hash"] = h
            return (False, False)

        monkeypatch.setattr("blueprints.auth.verify_password", spy)
        mock_db.cursor().fetchone.return_value = None  # get_user_by_email -> None

        resp = client.post(
            "/api/users/signin",
            json={"email": "nobody@example.com", "password": "whatever1"},
        )
        assert resp.status_code == 401
        assert captured.get("hash") == DUMMY_PASSWORD_HASH
