"""
LTI 1.3 repository — all SQL operations for LMS integration.

Tables: lti_configurations, lti_sessions
Extensions: users.lti_sub/lti_issuer, classes.lti_context_id/nrps_context_url/ags_*
"""

import json
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# lti_configurations — LMS platform registrations
# ---------------------------------------------------------------------------


def get_all_lti_configs(conn):
    """Return all registered LMS platforms as a list of dicts."""
    cur = conn.cursor()
    cur.execute(
        """SELECT config_id, platform_name, issuer, client_id,
                  auth_login_url, auth_token_url, key_set_url,
                  deployment_ids, created_by, created_at
           FROM lti_configurations
           ORDER BY created_at"""
    )
    rows = cur.fetchall()
    cur.close()
    cols = [
        "config_id",
        "platform_name",
        "issuer",
        "client_id",
        "auth_login_url",
        "auth_token_url",
        "key_set_url",
        "deployment_ids",
        "created_by",
        "created_at",
    ]
    return [dict(zip(cols, row)) for row in rows]


def insert_lti_config(
    conn,
    platform_name,
    issuer,
    client_id,
    auth_login_url,
    auth_token_url,
    key_set_url,
    deployment_ids,
    created_by,
):
    """Insert a new LMS platform registration. Returns the new config dict."""
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO lti_configurations
               (platform_name, issuer, client_id, auth_login_url,
                auth_token_url, key_set_url, deployment_ids, created_by)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
           RETURNING config_id, platform_name, issuer, client_id,
                     auth_login_url, auth_token_url, key_set_url,
                     deployment_ids, created_by, created_at""",
        (
            platform_name,
            issuer,
            client_id,
            auth_login_url,
            auth_token_url,
            key_set_url,
            deployment_ids or [],
            created_by,
        ),
    )
    row = cur.fetchone()
    cur.close()
    cols = [
        "config_id",
        "platform_name",
        "issuer",
        "client_id",
        "auth_login_url",
        "auth_token_url",
        "key_set_url",
        "deployment_ids",
        "created_by",
        "created_at",
    ]
    return dict(zip(cols, row))


def get_lti_config_by_id(conn, config_id):
    """Return a single LTI config by ID, or None."""
    cur = conn.cursor()
    cur.execute(
        "SELECT config_id, issuer, client_id, created_by FROM lti_configurations WHERE config_id = %s",
        (config_id,),
    )
    row = cur.fetchone()
    cur.close()
    if not row:
        return None
    return dict(zip(["config_id", "issuer", "client_id", "created_by"], row))


def delete_lti_config(conn, config_id, professor_id):
    """Delete an LTI config created by this professor. Returns True if deleted."""
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM lti_configurations WHERE config_id = %s AND created_by = %s",
        (config_id, professor_id),
    )
    deleted = cur.rowcount > 0
    cur.close()
    return deleted


# ---------------------------------------------------------------------------
# User LTI identity linking
# ---------------------------------------------------------------------------


def get_user_by_lti_sub(conn, lti_sub, issuer):
    """Return user row (user_id, name, email, role) by LTI sub + issuer, or None."""
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, name, email, role FROM users WHERE lti_sub = %s AND lti_issuer = %s",
        (lti_sub, issuer),
    )
    row = cur.fetchone()
    cur.close()
    return row


def link_lti_identity(conn, user_id, lti_sub, issuer):
    """Associate an existing user account with an LTI sub identifier."""
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET lti_sub = %s, lti_issuer = %s WHERE user_id = %s",
        (lti_sub, issuer, user_id),
    )
    cur.close()


# ---------------------------------------------------------------------------
# lti_sessions — launch context records
# ---------------------------------------------------------------------------


def create_lti_session(
    conn,
    session_id,
    user_id,
    class_id,
    nrps_context_url,
    lti_context_id,
    issuer,
    client_id,
    launch_data,
    expires_at,
):
    """Insert or replace an LTI session record after a successful launch."""
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO lti_sessions
               (session_id, user_id, class_id, nrps_context_url, lti_context_id,
                issuer, client_id, launch_data, expires_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (session_id) DO UPDATE
               SET user_id          = EXCLUDED.user_id,
                   class_id         = EXCLUDED.class_id,
                   nrps_context_url = EXCLUDED.nrps_context_url,
                   lti_context_id   = EXCLUDED.lti_context_id,
                   issuer           = EXCLUDED.issuer,
                   client_id        = EXCLUDED.client_id,
                   launch_data      = EXCLUDED.launch_data,
                   expires_at       = EXCLUDED.expires_at""",
        (
            session_id,
            user_id,
            class_id,
            nrps_context_url,
            lti_context_id,
            issuer,
            client_id,
            json.dumps(launch_data) if launch_data else None,
            expires_at,
        ),
    )
    cur.close()


def get_lti_session(conn, session_id):
    """Return an LTI session row as a dict, or None."""
    cur = conn.cursor()
    cur.execute(
        """SELECT session_id, user_id, class_id, nrps_context_url,
                  lti_context_id, issuer, client_id, launch_data, expires_at
           FROM lti_sessions
           WHERE session_id = %s AND expires_at > NOW()""",
        (session_id,),
    )
    row = cur.fetchone()
    cur.close()
    if not row:
        return None
    cols = [
        "session_id",
        "user_id",
        "class_id",
        "nrps_context_url",
        "lti_context_id",
        "issuer",
        "client_id",
        "launch_data",
        "expires_at",
    ]
    return dict(zip(cols, row))


def cleanup_expired_lti_sessions(conn):
    """Delete expired LTI session records. Returns number of rows deleted."""
    cur = conn.cursor()
    cur.execute("DELETE FROM lti_sessions WHERE expires_at <= NOW()")
    count = cur.rowcount
    cur.close()
    logger.info("Cleaned up %d expired LTI sessions", count)
    return count


# ---------------------------------------------------------------------------
# Class ↔ LTI context linking
# ---------------------------------------------------------------------------


def link_class_to_lti_context(
    conn, class_id, lti_context_id, issuer, nrps_context_url, ags_lineitems_url=None
):
    """Store LTI context/NRPS/AGS URLs on a class row."""
    cur = conn.cursor()
    cur.execute(
        """UPDATE classes
           SET lti_context_id   = %s,
               lti_issuer       = %s,
               nrps_context_url = %s,
               ags_lineitems_url = %s,
               updated_at       = NOW()
           WHERE class_id = %s""",
        (lti_context_id, issuer, nrps_context_url, ags_lineitems_url, class_id),
    )
    cur.close()


def get_class_by_lti_context(conn, lti_context_id, issuer):
    """Find a class linked to a specific LTI context, or None."""
    cur = conn.cursor()
    cur.execute(
        """SELECT class_id, professor_id, name, description,
                  lti_context_id, lti_issuer, nrps_context_url,
                  ags_enabled, ags_lineitems_url
           FROM classes
           WHERE lti_context_id = %s AND lti_issuer = %s""",
        (lti_context_id, issuer),
    )
    row = cur.fetchone()
    cur.close()
    if not row:
        return None
    cols = [
        "class_id",
        "professor_id",
        "name",
        "description",
        "lti_context_id",
        "lti_issuer",
        "nrps_context_url",
        "ags_enabled",
        "ags_lineitems_url",
    ]
    return dict(zip(cols, row))


def set_class_ags_enabled(conn, class_id, enabled):
    """Toggle AGS grade passback on or off for a class."""
    cur = conn.cursor()
    cur.execute(
        "UPDATE classes SET ags_enabled = %s, updated_at = NOW() WHERE class_id = %s",
        (enabled, class_id),
    )
    cur.close()


def update_class_ags_lineitems_url(conn, class_id, lineitems_url):
    """Persist the AGS lineitems URL captured from an LTI launch."""
    cur = conn.cursor()
    cur.execute(
        "UPDATE classes SET ags_lineitems_url = %s, updated_at = NOW() WHERE class_id = %s",
        (lineitems_url, class_id),
    )
    cur.close()
