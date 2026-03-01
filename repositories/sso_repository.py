"""
SSO Repository — SQL operations for tenant SSO provider configuration and identity linking.

Every function receives a DB *connection* and returns plain Python data.
The caller (blueprint) is responsible for commit / rollback / connection lifecycle.

Client secrets are stored Fernet-encrypted; encryption/decryption is handled in
blueprints/sso.py so this repository only deals with raw (already-encrypted) bytes.
"""

import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Provider queries (public — login page)
# ---------------------------------------------------------------------------


def get_enabled_providers(conn):
    """
    Return all enabled SSO providers with safe (non-secret) fields.
    Used to render SSO buttons on the login page.

    Returns list of dicts: {provider_id, provider_name, provider_type, tenant_id}
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT p.provider_id, p.provider_name, p.provider_type, p.tenant_id,
               t.name AS tenant_name
        FROM tenant_sso_providers p
        JOIN tenants t ON t.tenant_id = p.tenant_id
        WHERE p.is_enabled = true AND t.is_active = true
        ORDER BY t.name, p.provider_name
        """,
    )
    rows = cur.fetchall()
    cur.close()
    return [
        {
            "provider_id": r[0],
            "provider_name": r[1],
            "provider_type": r[2],
            "tenant_id": r[3],
            "tenant_name": r[4],
        }
        for r in rows
    ]


def get_provider_by_id(conn, provider_id):
    """
    Return full provider row including the encrypted client_secret.
    Returns a dict or None.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT provider_id, tenant_id, provider_name, provider_type,
               client_id, client_secret, discovery_url,
               allowed_domains, role_mapping_attribute, role_mapping, default_role,
               is_enabled
        FROM tenant_sso_providers
        WHERE provider_id = %s
        """,
        (provider_id,),
    )
    row = cur.fetchone()
    cur.close()
    if not row:
        return None
    return {
        "provider_id": row[0],
        "tenant_id": row[1],
        "provider_name": row[2],
        "provider_type": row[3],
        "client_id": row[4],
        "client_secret": row[5],  # still encrypted — caller must decrypt
        "discovery_url": row[6],
        "allowed_domains": row[7] or [],
        "role_mapping_attribute": row[8],
        "role_mapping": row[9] or {},
        "default_role": row[10] or "student",
        "is_enabled": row[11],
    }


def get_providers_for_tenant(conn, tenant_id):
    """
    Return all providers for a given tenant (admin view, excludes secret).
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT provider_id, provider_name, provider_type, client_id, discovery_url,
               allowed_domains, role_mapping_attribute, role_mapping, default_role,
               is_enabled, created_at, updated_at
        FROM tenant_sso_providers
        WHERE tenant_id = %s
        ORDER BY created_at
        """,
        (tenant_id,),
    )
    rows = cur.fetchall()
    cur.close()
    return [
        {
            "provider_id": r[0],
            "provider_name": r[1],
            "provider_type": r[2],
            "client_id": r[3],
            "discovery_url": r[4],
            "allowed_domains": r[5] or [],
            "role_mapping_attribute": r[6],
            "role_mapping": r[7] or {},
            "default_role": r[8] or "student",
            "is_enabled": r[9],
            "created_at": r[10].isoformat() if r[10] else None,
            "updated_at": r[11].isoformat() if r[11] else None,
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Provider management (admin)
# ---------------------------------------------------------------------------


def insert_provider(
    conn,
    provider_id,
    tenant_id,
    provider_name,
    provider_type,
    client_id,
    client_secret_encrypted,
    discovery_url,
    allowed_domains,
    role_mapping_attribute,
    role_mapping,
    default_role,
    created_by,
):
    """Insert a new SSO provider. client_secret_encrypted must be pre-encrypted by caller."""
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO tenant_sso_providers (
            provider_id, tenant_id, provider_name, provider_type,
            client_id, client_secret, discovery_url,
            allowed_domains, role_mapping_attribute, role_mapping, default_role,
            is_enabled, created_by
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true, %s)
        RETURNING provider_id
        """,
        (
            provider_id,
            tenant_id,
            provider_name,
            provider_type,
            client_id,
            client_secret_encrypted,
            discovery_url,
            allowed_domains or [],
            role_mapping_attribute,
            role_mapping or {},
            default_role or "student",
            created_by,
        ),
    )
    row = cur.fetchone()
    cur.close()
    return row[0] if row else None


def update_provider(conn, provider_id, updates: dict):
    """
    Partial update of a provider. Only keys present in `updates` are changed.
    Allowed keys: provider_name, provider_type, client_id, client_secret (encrypted),
                  discovery_url, allowed_domains, role_mapping_attribute,
                  role_mapping, default_role, is_enabled.
    """
    allowed = {
        "provider_name",
        "provider_type",
        "client_id",
        "client_secret",
        "discovery_url",
        "allowed_domains",
        "role_mapping_attribute",
        "role_mapping",
        "default_role",
        "is_enabled",
    }
    fields = {k: v for k, v in updates.items() if k in allowed}
    if not fields:
        return False

    fields["updated_at"] = "CURRENT_TIMESTAMP"
    set_clauses = []
    values = []
    for k, v in fields.items():
        if v == "CURRENT_TIMESTAMP":
            set_clauses.append(f"{k} = CURRENT_TIMESTAMP")
        else:
            set_clauses.append(f"{k} = %s")
            values.append(v)

    values.append(provider_id)
    cur = conn.cursor()
    cur.execute(
        f"UPDATE tenant_sso_providers SET {', '.join(set_clauses)} WHERE provider_id = %s",
        values,
    )
    updated = cur.rowcount > 0
    cur.close()
    return updated


def delete_provider(conn, provider_id):
    """Hard delete a provider (cascades to linked users' sso_provider_id via SET NULL)."""
    cur = conn.cursor()
    cur.execute("DELETE FROM tenant_sso_providers WHERE provider_id = %s", (provider_id,))
    deleted = cur.rowcount > 0
    cur.close()
    return deleted


# ---------------------------------------------------------------------------
# User identity queries
# ---------------------------------------------------------------------------


def get_user_by_sso_identity(conn, provider_id, subject):
    """
    Return (user_id, name, email, role, tenant_id) for a user identified
    by their SSO provider + subject claim, or None if not found.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT user_id, name, email, COALESCE(role, 'student'), tenant_id
        FROM users
        WHERE sso_provider_id = %s AND sso_subject = %s
        """,
        (provider_id, subject),
    )
    row = cur.fetchone()
    cur.close()
    return row


def link_sso_identity(conn, user_id, provider_id, subject):
    """Attach an SSO identity to an existing user (email-matched account linking)."""
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE users
        SET sso_provider_id = %s, sso_subject = %s, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = %s
        """,
        (provider_id, subject, user_id),
    )
    cur.close()
