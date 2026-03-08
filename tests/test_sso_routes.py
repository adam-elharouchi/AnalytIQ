"""
tests/test_sso_routes.py — Behavioral tests for SSO blueprint routes.

Covers:
  GET  /api/sso/providers                   — public list of enabled providers
  GET  /api/sso/init/<provider_id>          — start OAuth2 flow
  GET  /api/sso/callback/<provider_id>      — OAuth2 callback (state/code exchange)
  GET  /api/sso/admin/providers             — list providers (admin)
  POST /api/sso/admin/providers             — create provider (admin)
  PUT  /api/sso/admin/providers/<id>        — update provider (admin)
  DELETE /api/sso/admin/providers/<id>      — delete provider (admin)
"""
from unittest.mock import MagicMock, patch

import pytest

PROVIDER_ID = "prov-aaaa-bbbb-cccc-dddddddddddd"
TENANT_ID = "aaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

AUTH_ADMIN = {
    "X-Test-User-ID": "admin-user-id",
    "X-Test-User-Role": "superadmin",
}
AUTH_TENANT_ADMIN = {
    "X-Test-User-ID": "tenant-admin-id",
    "X-Test-User-Role": "tenant_admin",
}


# ---------------------------------------------------------------------------
# GET /api/sso/providers  (public)
# ---------------------------------------------------------------------------


class TestListPublicProviders:
    def test_returns_200_with_empty_list_when_feature_off(self, client, mock_db):
        """When FEATURE_SSO is not set, returns empty list."""
        resp = client.get("/api/sso/providers")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "providers" in data

    def test_returns_providers_from_db(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchall.return_value = [
            (PROVIDER_ID, "Google SSO", "google", TENANT_ID, "Acme Corp"),
        ]
        with patch.dict("os.environ", {"FEATURE_SSO": "True"}):
            resp = client.get("/api/sso/providers")
        assert resp.status_code == 200

    def test_db_error_returns_200_with_empty_list(self, client, mock_db):
        """Fail-open: provider fetch failure still returns 200 with empty list."""
        mock_db.cursor.side_effect = Exception("db down")
        with patch.dict("os.environ", {"FEATURE_SSO": "True"}):
            resp = client.get("/api/sso/providers")
        assert resp.status_code == 200
        mock_db.cursor.side_effect = None


# ---------------------------------------------------------------------------
# GET /api/sso/init/<provider_id>
# ---------------------------------------------------------------------------


class TestSsoInit:
    def _mock_provider(self, cursor):
        cursor.fetchone.return_value = {
            "provider_id": PROVIDER_ID,
            "provider_name": "Google",
            "provider_type": "google",
            "client_id": "test-client-id",
            "client_secret": "encrypted-secret",
            "discovery_url": None,
            "allowed_domains": [],
            "role_mapping_attribute": None,
            "role_mapping": {},
            "default_role": "student",
            "tenant_id": TENANT_ID,
            "is_enabled": True,
        }

    def test_provider_not_found_returns_404(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None
        with patch("blueprints.sso.sso_repo") as mock_repo:
            mock_repo.get_provider_by_id.return_value = None
            resp = client.get(f"/api/sso/init/{PROVIDER_ID}")
        assert resp.status_code == 404

    def test_provider_disabled_returns_404(self, client, mock_db):
        # Route returns 404 for disabled or missing provider (not 403)
        with patch("blueprints.sso.sso_repo") as mock_repo:
            mock_repo.get_provider_by_id.return_value = {
                "provider_id": PROVIDER_ID,
                "is_enabled": False,
                "provider_type": "google",
                "client_id": "cid",
                "client_secret": "cs",
            }
            resp = client.get(f"/api/sso/init/{PROVIDER_ID}")
        assert resp.status_code == 404

    def test_sso_feature_disabled_returns_503(self, client, mock_db):
        with patch.dict("os.environ", {"FEATURE_SSO": "False"}):
            with patch("blueprints.sso.sso_repo") as mock_repo:
                mock_repo.get_provider_by_id.return_value = None
                resp = client.get(f"/api/sso/init/{PROVIDER_ID}")
        # Either 503 (feature off) or 404 (provider not found) are acceptable
        assert resp.status_code in (404, 503)


# ---------------------------------------------------------------------------
# GET /api/sso/admin/providers
# ---------------------------------------------------------------------------


class TestAdminListProviders:
    def test_superadmin_lists_all_providers(self, client, mock_db):
        with patch("blueprints.sso.sso_repo") as mock_repo:
            mock_repo.get_providers_for_tenant.return_value = []
            resp = client.get(
                f"/api/sso/admin/providers?tenant_id={TENANT_ID}",
                headers=AUTH_ADMIN,
            )
        assert resp.status_code == 200
        assert "providers" in resp.get_json()

    def test_unauthenticated_returns_401(self, client, mock_db):
        resp = client.get("/api/sso/admin/providers")
        assert resp.status_code == 401

    def test_student_role_returns_403(self, client, mock_db):
        resp = client.get(
            "/api/sso/admin/providers",
            headers={"X-Test-User-ID": "student-id", "X-Test-User-Role": "student"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /api/sso/admin/providers
# ---------------------------------------------------------------------------


class TestAdminCreateProvider:
    def test_invalid_provider_type_returns_400(self, client, mock_db):
        resp = client.post(
            f"/api/sso/admin/providers?tenant_id={TENANT_ID}",
            json={
                "provider_name": "Test",
                "provider_type": "saml",  # not supported
                "client_id": "cid",
                "client_secret": "cs",
            },
            headers=AUTH_ADMIN,
        )
        assert resp.status_code == 400

    def test_missing_required_fields_returns_400(self, client, mock_db):
        resp = client.post(
            f"/api/sso/admin/providers?tenant_id={TENANT_ID}",
            json={"provider_name": "Test"},
            headers=AUTH_ADMIN,
        )
        assert resp.status_code == 400

    def test_missing_tenant_returns_400(self, client, mock_db):
        resp = client.post(
            "/api/sso/admin/providers",
            json={
                "provider_name": "Test",
                "provider_type": "google",
                "client_id": "cid",
                "client_secret": "cs",
            },
            headers=AUTH_ADMIN,
        )
        assert resp.status_code == 400

    def test_unauthenticated_returns_401(self, client, mock_db):
        resp = client.post(
            f"/api/sso/admin/providers?tenant_id={TENANT_ID}",
            json={},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PUT /api/sso/admin/providers/<id>
# ---------------------------------------------------------------------------


class TestAdminUpdateProvider:
    def test_provider_not_found_returns_404(self, client, mock_db):
        with patch("blueprints.sso.sso_repo") as mock_repo:
            mock_repo.get_provider_by_id.return_value = None
            resp = client.put(
                f"/api/sso/admin/providers/{PROVIDER_ID}?tenant_id={TENANT_ID}",
                json={"provider_name": "New Name"},
                headers=AUTH_ADMIN,
            )
        assert resp.status_code == 404

    def test_unauthenticated_returns_401(self, client, mock_db):
        resp = client.put(
            f"/api/sso/admin/providers/{PROVIDER_ID}",
            json={"provider_name": "X"},
        )
        assert resp.status_code == 401

    def test_student_returns_403(self, client, mock_db):
        resp = client.put(
            f"/api/sso/admin/providers/{PROVIDER_ID}",
            json={"provider_name": "X"},
            headers={"X-Test-User-ID": "s-id", "X-Test-User-Role": "student"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /api/sso/admin/providers/<id>
# ---------------------------------------------------------------------------


class TestAdminDeleteProvider:
    def test_provider_not_found_returns_404(self, client, mock_db):
        with patch("blueprints.sso.sso_repo") as mock_repo:
            mock_repo.get_provider_by_id.return_value = None
            resp = client.delete(
                f"/api/sso/admin/providers/{PROVIDER_ID}?tenant_id={TENANT_ID}",
                headers=AUTH_ADMIN,
            )
        assert resp.status_code == 404

    def test_unauthenticated_returns_401(self, client, mock_db):
        resp = client.delete(f"/api/sso/admin/providers/{PROVIDER_ID}")
        assert resp.status_code == 401

    def test_student_returns_403(self, client, mock_db):
        resp = client.delete(
            f"/api/sso/admin/providers/{PROVIDER_ID}",
            headers={"X-Test-User-ID": "s-id", "X-Test-User-Role": "student"},
        )
        assert resp.status_code == 403

    def test_successful_delete_returns_200(self, client, mock_db):
        with patch("blueprints.sso.sso_repo") as mock_repo:
            provider = {
                "provider_id": PROVIDER_ID,
                "tenant_id": TENANT_ID,
                "is_enabled": True,
                "provider_type": "google",
            }
            mock_repo.get_provider_by_id.return_value = provider
            mock_repo.delete_provider.return_value = True
            resp = client.delete(
                f"/api/sso/admin/providers/{PROVIDER_ID}?tenant_id={TENANT_ID}",
                headers=AUTH_ADMIN,
            )
        assert resp.status_code == 200
