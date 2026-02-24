"""
FERPA-compliant audit logging for AnalytIQ.

Every data mutation that affects student records is logged to ``audit_log``.
The table is created on first use (CREATE TABLE IF NOT EXISTS) so no migration
script is required.

Usage::

    from audit import audit
    from db import get_db_connection

    conn = get_db_connection()
    # ... business operation ...
    audit(conn, "DELETE_CLASS", resource_type="class", resource_id=class_id)
    conn.commit()   # commits both the business op AND the audit row atomically

``audit()`` never raises — a failure is logged as a warning so the caller's
request is never interrupted by an audit-layer problem.
"""

import json
import logging
import threading

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
# Lazy table-creation guard (once per process)                        #
# ------------------------------------------------------------------ #

_table_ready = False
_table_lock = threading.Lock()

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS audit_log (
    id            BIGSERIAL    PRIMARY KEY,
    user_id       TEXT,
    action        TEXT         NOT NULL,
    resource_type TEXT,
    resource_id   TEXT,
    ip_address    TEXT,
    details       JSONB,
    created_at    TIMESTAMPTZ  DEFAULT NOW()
);
"""

_CREATE_IDX_USER_SQL = """
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id
    ON audit_log (user_id);
"""

_CREATE_IDX_TIME_SQL = """
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at
    ON audit_log (created_at DESC);
"""


def ensure_audit_log_table(conn):
    """Create the ``audit_log`` table and indexes if they do not already exist.

    Commits immediately so the table is visible to subsequent requests
    that share the same pool.
    """
    with conn.cursor() as cur:
        cur.execute(_CREATE_TABLE_SQL)
        cur.execute(_CREATE_IDX_USER_SQL)
        cur.execute(_CREATE_IDX_TIME_SQL)
    conn.commit()


# ------------------------------------------------------------------ #
# Public API                                                          #
# ------------------------------------------------------------------ #

#: Upper-snake-case action codes used throughout the codebase.
#: Keep this list in sync with every ``audit()`` call site.
ACTIONS = {
    # Auth
    "CREATE_USER",
    "RESET_PASSWORD",
    # Users
    "UPDATE_PROFILE",
    "UPDATE_PASSWORD",
    "DELETE_USER",
    # Classes
    "CREATE_CLASS",
    "DELETE_CLASS",
    "ENROLL_CLASS",
    # Chapters
    "CREATE_CHAPTER",
    "DELETE_CHAPTER",
    # Exercises
    "CREATE_EXERCISE",
    "DELETE_EXERCISE",
    "EXERCISE_SUBMISSION",
    # Super Admin
    "IMPERSONATE_USER",
    "CREATE_TENANT",
    "UPDATE_TENANT",
    "DELETE_TENANT",
    "DISABLE_USER",
    "ENABLE_USER",
    "DELETE_USER",
    "UPDATE_USER_ROLE",
    "FORCE_PASSWORD_RESET",
    "TRANSFER_CLASS",
    # Content Import
    "IMPORT_CHAPTER",
}


def audit(conn, action, *, resource_type=None, resource_id=None, details=None):
    """Insert one audit record into ``audit_log``.

    The INSERT shares the caller's open transaction; call ``conn.commit()``
    after this function to persist both the business operation and the audit
    row atomically.  If the caller rolls back, the audit row is also rolled
    back — preventing phantom audit entries for failed operations.

    Args:
        conn:          psycopg2 connection from ``get_db_connection()``.
        action:        Upper-snake-case action code, e.g. ``"DELETE_CLASS"``.
        resource_type: Resource kind, e.g. ``"class"``, ``"chapter"``.
        resource_id:   String ID of the affected resource.
        details:       Optional ``dict`` of extra context (stored as JSONB).
    """
    global _table_ready

    # Ensure the table exists (idempotent, one-time cost per process).
    if not _table_ready:
        with _table_lock:
            if not _table_ready:
                try:
                    ensure_audit_log_table(conn)
                    _table_ready = True
                except Exception as exc:
                    logger.warning(
                        "audit_log table setup failed — audit disabled: %s", exc
                    )
                    return

    try:
        # Resolve request context values gracefully (may not exist in tests).
        try:
            from flask import g as flask_g

            user_id = getattr(flask_g, "user_id", None)
        except RuntimeError:
            user_id = None

        try:
            from flask import request as flask_request

            ip_address = flask_request.remote_addr
            
            # Extract impersonator ID if present so we can trace real actor
            try:
                from flask import g as flask_g
                impersonator_id = getattr(flask_g, "impersonator_id", None)
                if impersonator_id:
                    details = details or {}
                    details["impersonator_id"] = impersonator_id
            except RuntimeError:
                pass
                
        except RuntimeError:
            ip_address = None

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO audit_log
                    (user_id, action, resource_type, resource_id, ip_address, details)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    action,
                    resource_type,
                    str(resource_id) if resource_id is not None else None,
                    ip_address,
                    json.dumps(details) if details else None,
                ),
            )

    except Exception as exc:
        logger.warning("audit() failed for action=%s: %s", action, exc)
