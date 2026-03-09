"""
FERPA-compliant audit logging for AnalytIQ.

Every data mutation that affects student records is logged to ``audit_log``.
The table is created by migration 006_core_tables.sql.

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

logger = logging.getLogger(__name__)


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
    try:
        # Resolve request context values gracefully (may not exist in tests).
        try:
            from flask import g as flask_g

            user_id = getattr(flask_g, "user_id", None)
        except RuntimeError:
            user_id = None

        try:
            from flask import g as flask_g, request as flask_request

            ip_address = flask_request.remote_addr

            # Include impersonator ID so we can trace the real actor
            impersonator_id = getattr(flask_g, "impersonator_id", None)
            if impersonator_id:
                details = details or {}
                details["impersonator_id"] = impersonator_id
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
