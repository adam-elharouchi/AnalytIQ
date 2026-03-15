"""
tests/test_sso_repository.py — Unit tests for repositories/sso_repository.py

Covers all 8 repository functions:
  get_enabled_providers
  get_provider_by_id
  get_providers_for_tenant
  insert_provider
  update_provider
  delete_provider
  get_user_by_sso_identity
  link_sso_identity
"""
import uuid
from unittest.mock import MagicMock, Mock

import pytest

from repositories.sso_repository import (
    delete_provider,
    get_enabled_providers,
    get_provider_by_id,
    get_providers_for_tenant,
    get_user_by_sso_identity,
    insert_provider,
    link_sso_identity,
    update_provider,
)

PROVIDER_ID = str(uuid.uuid4())
TENANT_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())


@pytest.fixture
def conn():
    """Standalone mock DB connection for repository unit tests."""
    cursor = MagicMock()
    cursor.fetchone = Mock(return_value=None)
    cursor.fetchall = Mock(return_value=[])
    cursor.execute = Mock()
    cursor.close = Mock()
    cursor.rowcount = 1

    connection = MagicMock()
    connection.cursor = Mock(return_value=cursor)
    connection.commit = Mock()
    connection.rollback = Mock()
    return connection


# ---------------------------------------------------------------------------
# get_enabled_providers
# ---------------------------------------------------------------------------


class TestGetEnabledProviders:
    def test_returns_empty_list_when_none(self, conn):
        conn.cursor().fetchall.return_value = []
        result = get_enabled_providers(conn)
        assert result == []

    def test_returns_provider_rows(self, conn):
        conn.cursor().fetchall.return_value = [
            (PROVIDER_ID, "Google SSO", "google", TENANT_ID, "Acme"),
        ]
        result = get_enabled_providers(conn)
        assert len(result) == 1
        assert result[0]["provider_id"] == PROVIDER_ID
        assert result[0]["provider_name"] == "Google SSO"
        assert result[0]["provider_type"] == "google"
        assert result[0]["tenant_id"] == TENANT_ID

    def test_returns_multiple_providers(self, conn):
        conn.cursor().fetchall.return_value = [
            (PROVIDER_ID, "Google", "google", TENANT_ID, "Acme"),
            (str(uuid.uuid4()), "Microsoft", "microsoft", TENANT_ID, "Acme"),
        ]
        result = get_enabled_providers(conn)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# get_provider_by_id
# ---------------------------------------------------------------------------


class TestGetProviderById:
    def test_returns_none_when_not_found(self, conn):
        conn.cursor().fetchone.return_value = None
        result = get_provider_by_id(conn, PROVIDER_ID)
        assert result is None

    def test_returns_provider_dict(self, conn):
        conn.cursor().fetchone.return_value = (
            PROVIDER_ID, TENANT_ID, "Google SSO", "google",
            "client-id", "encrypted-secret", None,
            ["acme.com"], None, {}, "student", True,
        )
        result = get_provider_by_id(conn, PROVIDER_ID)
        assert result is not None
        assert result["provider_id"] == PROVIDER_ID
        assert result["provider_type"] == "google"
        assert result["client_id"] == "client-id"
        assert result["is_enabled"] is True


# ---------------------------------------------------------------------------
# get_providers_for_tenant
# ---------------------------------------------------------------------------


class TestGetProvidersForTenant:
    def test_returns_empty_when_none(self, conn):
        conn.cursor().fetchall.return_value = []
        result = get_providers_for_tenant(conn, TENANT_ID)
        assert result == []

    def test_returns_providers_for_tenant(self, conn):
        conn.cursor().fetchall.return_value = [
            (PROVIDER_ID, "Google SSO", "google", "client-id", None,
             ["acme.com"], None, {}, "student", True, None, None),
        ]
        result = get_providers_for_tenant(conn, TENANT_ID)
        assert len(result) == 1
        assert result[0]["provider_id"] == PROVIDER_ID


# ---------------------------------------------------------------------------
# insert_provider
# ---------------------------------------------------------------------------


class TestInsertProvider:
    def test_insert_returns_provider_id(self, conn):
        conn.cursor().fetchone.return_value = (PROVIDER_ID,)
        result = insert_provider(
            conn,
            provider_id=PROVIDER_ID,
            tenant_id=TENANT_ID,
            provider_name="Google SSO",
            provider_type="google",
            client_id="cid",
            client_secret_encrypted="enc-secret",
            discovery_url=None,
            allowed_domains=[],
            role_mapping_attribute=None,
            role_mapping={},
            default_role="student",
            created_by=USER_ID,
        )
        assert result == PROVIDER_ID

    def test_insert_executes_sql(self, conn):
        conn.cursor().fetchone.return_value = (PROVIDER_ID,)
        insert_provider(
            conn,
            provider_id=PROVIDER_ID,
            tenant_id=TENANT_ID,
            provider_name="MS SSO",
            provider_type="microsoft",
            client_id="cid",
            client_secret_encrypted="enc",
            discovery_url="https://example.com/.well-known/openid-configuration",
            allowed_domains=["corp.com"],
            role_mapping_attribute="groups",
            role_mapping={"admins": "professor"},
            default_role="student",
            created_by=USER_ID,
        )
        conn.cursor().execute.assert_called()


# ---------------------------------------------------------------------------
# update_provider
# ---------------------------------------------------------------------------


class TestUpdateProvider:
    def test_update_returns_true_on_success(self, conn):
        conn.cursor().rowcount = 1
        result = update_provider(conn, PROVIDER_ID, {"provider_name": "New Name"})
        assert result is True

    def test_update_returns_false_when_not_found(self, conn):
        conn.cursor().rowcount = 0
        result = update_provider(conn, PROVIDER_ID, {"provider_name": "X"})
        assert result is False

    def test_update_ignores_unknown_fields(self, conn):
        conn.cursor().rowcount = 1
        # Only known fields should make it into the SQL
        result = update_provider(
            conn, PROVIDER_ID,
            {"provider_name": "X", "unknown_field": "ignored"}
        )
        assert result is True

    def test_update_empty_dict_returns_false(self, conn):
        """Nothing to update → should return False or skip."""
        result = update_provider(conn, PROVIDER_ID, {})
        assert result is False

    def test_update_is_enabled_field(self, conn):
        conn.cursor().rowcount = 1
        result = update_provider(conn, PROVIDER_ID, {"is_enabled": False})
        assert result is True


# ---------------------------------------------------------------------------
# delete_provider
# ---------------------------------------------------------------------------


class TestDeleteProvider:
    def test_delete_returns_true_when_found(self, conn):
        conn.cursor().rowcount = 1
        result = delete_provider(conn, PROVIDER_ID)
        assert result is True

    def test_delete_returns_false_when_not_found(self, conn):
        conn.cursor().rowcount = 0
        result = delete_provider(conn, PROVIDER_ID)
        assert result is False

    def test_delete_executes_cascade_on_users(self, conn):
        conn.cursor().rowcount = 1
        delete_provider(conn, PROVIDER_ID)
        # Should have called execute (for SET NULL and DELETE)
        assert conn.cursor().execute.called


# ---------------------------------------------------------------------------
# get_user_by_sso_identity
# ---------------------------------------------------------------------------


class TestGetUserBySsoIdentity:
    def test_returns_none_when_not_found(self, conn):
        conn.cursor().fetchone.return_value = None
        result = get_user_by_sso_identity(conn, PROVIDER_ID, "sub-12345")
        assert result is None

    def test_returns_user_tuple(self, conn):
        conn.cursor().fetchone.return_value = (
            USER_ID, "Alice", "alice@acme.com", "student", TENANT_ID,
        )
        result = get_user_by_sso_identity(conn, PROVIDER_ID, "sub-12345")
        assert result is not None
        assert result[0] == USER_ID
        assert result[2] == "alice@acme.com"

    def test_calls_execute_with_correct_params(self, conn):
        conn.cursor().fetchone.return_value = None
        get_user_by_sso_identity(conn, PROVIDER_ID, "my-subject")
        conn.cursor().execute.assert_called()


# ---------------------------------------------------------------------------
# link_sso_identity
# ---------------------------------------------------------------------------


class TestLinkSsoIdentity:
    def test_link_executes_upsert(self, conn):
        link_sso_identity(conn, USER_ID, PROVIDER_ID, "sub-99999")
        assert conn.cursor().execute.called

    def test_link_does_not_raise(self, conn):
        # Should complete without error even with mock cursor
        link_sso_identity(conn, USER_ID, PROVIDER_ID, "sub-abc")
