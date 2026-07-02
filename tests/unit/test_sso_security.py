"""
tests/unit/test_sso_security.py — SSO federation-linking safety (C-5 + B2).

_upsert_sso_user must:
  - never federate into a privileged (superadmin/tenant_admin) account by email,
  - only auto-link to a pre-existing account when the IdP asserts email_verified,
  - link normally to a verified, non-privileged existing account.
"""
from unittest.mock import MagicMock, patch

import pytest

from blueprints.sso import _upsert_sso_user


def _provider():
    return {
        "provider_id": "p1",
        "tenant_id": "t1",
        "allowed_domains": [],
        "role_mapping_attribute": None,
        "role_mapping": {},
        "default_role": "student",
    }


def _conn_returning(email_user_row):
    conn = MagicMock()
    cur = MagicMock()
    cur.fetchone.return_value = email_user_row
    conn.cursor.return_value = cur
    return conn


@patch("blueprints.sso.sso_repo")
def test_refuses_privileged_account_link(mock_repo):
    mock_repo.get_user_by_sso_identity.return_value = None
    conn = _conn_returning(("u1", "Admin", "admin@x.edu", "superadmin"))
    with pytest.raises(PermissionError):
        _upsert_sso_user(
            conn, _provider(), {"sub": "s", "email": "admin@x.edu", "email_verified": True}
        )


@patch("blueprints.sso.sso_repo")
def test_refuses_unverified_email_link(mock_repo):
    mock_repo.get_user_by_sso_identity.return_value = None
    conn = _conn_returning(("u1", "Bob", "bob@x.edu", "student"))
    with pytest.raises(PermissionError):
        _upsert_sso_user(
            conn, _provider(), {"sub": "s", "email": "bob@x.edu", "email_verified": False}
        )


@patch("blueprints.sso.sso_repo")
def test_links_verified_existing_account(mock_repo):
    mock_repo.get_user_by_sso_identity.return_value = None
    mock_repo.link_sso_identity.return_value = None
    conn = _conn_returning(("u1", "Bob", "bob@x.edu", "student"))
    result = _upsert_sso_user(
        conn, _provider(), {"sub": "s", "email": "bob@x.edu", "email_verified": True}
    )
    assert result[0] == "u1"
    mock_repo.link_sso_identity.assert_called_once()
