"""
Auth Repository — SQL operations for signup, signin, and password reset.

Every function receives a DB *connection* and returns plain Python data.
The caller (blueprint) is responsible for commit / rollback / connection lifecycle.
"""

import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Signup
# ---------------------------------------------------------------------------


def email_exists(conn, email):
    """Return True if an account with this email already exists."""
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users WHERE email = %s", (email,))
    exists = cur.fetchone() is not None
    cur.close()
    return exists


def find_tenant_by_email_domain(conn, domain):
    """Return tenant_id for an active tenant whose email_domain matches, or None."""
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT tenant_id FROM tenants WHERE email_domain = %s AND is_active = true",
            (domain.lower(),),
        )
        row = cur.fetchone()
        cur.close()
        return row[0] if row else None
    except Exception:
        conn.rollback()
        cur.close()
        return None


def insert_user(conn, user_id, name, email, password_hash, role, tenant_id=None):
    """Insert a new user and return (user_id, name, email, role)."""
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO users (user_id, name, email, password_hash, role, tenant_id)
           VALUES (%s, %s, %s, %s, %s, %s)
           RETURNING user_id, name, email, COALESCE(role, 'student')""",
        (user_id, name, email, password_hash, role, tenant_id),
    )
    row = cur.fetchone()
    cur.close()
    return row


def create_default_profile(conn, user_id):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO user_profiles (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
        (user_id,),
    )
    cur.close()


def create_default_settings(conn, user_id):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO user_settings (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
        (user_id,),
    )
    cur.close()


def create_default_preferences(conn, user_id):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO user_preferences (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
        (user_id,),
    )
    cur.close()


def create_default_ai_digest(conn, user_id):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO ai_agent_digest (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
        (user_id,),
    )
    cur.close()


# ---------------------------------------------------------------------------
# Signin
# ---------------------------------------------------------------------------


def get_user_by_email(conn, email):
    """Return (user_id, name, email, password_hash, role, tenant_id) or None."""
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT user_id, name, email, password_hash, COALESCE(role, 'student'), tenant_id FROM users WHERE email = %s",
            (email,),
        )
        row = cur.fetchone()
        cur.close()
        return row
    except Exception:
        conn.rollback()
        # Fallback for environments where the tenant_id migration hasn't run yet
        cur2 = conn.cursor()
        try:
            cur2.execute(
                "SELECT user_id, name, email, password_hash, COALESCE(role, 'student') FROM users WHERE email = %s",
                (email,),
            )
            row = cur2.fetchone()
            cur2.close()
            if row:
                return row + (None,)  # Append None for tenant_id
            return None
        except Exception:
            conn.rollback()
            cur2.close()
            return None


def update_password_hash(conn, user_id, new_hash):
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET password_hash = %s WHERE user_id = %s",
        (new_hash, user_id),
    )
    cur.close()


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------


def get_user_name_by_email(conn, email):
    """Return (user_id, name) or None."""
    cur = conn.cursor()
    cur.execute("SELECT user_id, name FROM users WHERE email = %s", (email,))
    row = cur.fetchone()
    cur.close()
    return row


def insert_password_reset_token(conn, email, token, expires_at):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO password_resets (email, token, expires_at) VALUES (%s, %s, %s)",
        (email, token, expires_at),
    )
    cur.close()


def validate_reset_token(conn, email, token, now):
    """Return reset row id or None."""
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM password_resets WHERE email = %s AND token = %s AND expires_at > %s",
        (email, token, now),
    )
    row = cur.fetchone()
    cur.close()
    return row


def reset_password(conn, email, new_hash):
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET password_hash = %s, updated_at = CURRENT_TIMESTAMP WHERE email = %s",
        (new_hash, email),
    )
    cur.close()


def delete_reset_token(conn, email, token):
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM password_resets WHERE email = %s AND token = %s",
        (email, token),
    )
    cur.close()
