"""
tests/unit/test_token_refresh.py — refresh-token flow (D2).

POST /api/users/refresh exchanges a valid refresh token for a fresh access +
refresh pair. Access tokens carry type="access"; refresh tokens type="refresh".
require_auth must reject a refresh token used as an access token.
"""
from core.auth import create_jwt_token, create_refresh_token, decode_jwt_token


def _user_row(name="Alice", email="a@b.com", role="student", tenant=None, status="active", tv=0):
    # SELECT name, email, role, tenant_id, account_status, token_version
    return (name, email, role, tenant, status, tv)


class TestRefreshEndpoint:
    def test_missing_token_returns_400(self, client, mock_db):
        assert client.post("/api/users/refresh", json={}).status_code == 400

    def test_garbage_token_returns_401(self, client, mock_db):
        assert client.post(
            "/api/users/refresh", json={"refresh_token": "not.a.jwt"}
        ).status_code == 401

    def test_access_token_rejected_as_refresh(self, client, mock_db):
        access = create_jwt_token("u1", role="student", token_version=0)
        r = client.post("/api/users/refresh", json={"refresh_token": access})
        assert r.status_code == 401  # type != "refresh"

    def test_valid_refresh_returns_new_pair(self, client, mock_db):
        mock_db.cursor().fetchone.return_value = _user_row(tv=0)
        rt = create_refresh_token("u1", token_version=0)
        r = client.post("/api/users/refresh", json={"refresh_token": rt})
        assert r.status_code == 200
        data = r.get_json()
        assert "token" in data and "refresh_token" in data
        assert decode_jwt_token(data["token"])["type"] == "access"
        assert decode_jwt_token(data["refresh_token"])["type"] == "refresh"

    def test_tv_mismatch_revokes(self, client, mock_db):
        mock_db.cursor().fetchone.return_value = _user_row(tv=5)  # DB counter advanced
        rt = create_refresh_token("u1", token_version=0)          # stale token
        assert client.post(
            "/api/users/refresh", json={"refresh_token": rt}
        ).status_code == 401

    def test_disabled_account_403(self, client, mock_db):
        mock_db.cursor().fetchone.return_value = _user_row(status="disabled", tv=0)
        rt = create_refresh_token("u1", token_version=0)
        assert client.post(
            "/api/users/refresh", json={"refresh_token": rt}
        ).status_code == 403

    def test_unknown_user_401(self, client, mock_db):
        mock_db.cursor().fetchone.return_value = None
        rt = create_refresh_token("u1", token_version=0)
        assert client.post(
            "/api/users/refresh", json={"refresh_token": rt}
        ).status_code == 401


class TestRefreshTokenNotAccepance:
    def test_require_auth_rejects_refresh_token(self, client, mock_db):
        # A refresh token presented as a Bearer access token must be rejected.
        rt = create_refresh_token("u1", token_version=0)
        r = client.get("/api/users/profile", headers={"Authorization": f"Bearer {rt}"})
        assert r.status_code == 401
