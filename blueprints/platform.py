"""
Platform Blueprint — public-facing status and announcement endpoints.

Routes (no auth required):
  GET  /api/platform/status        — active announcements
"""

import logging
from flask import Blueprint, jsonify, request

from core.database import get_db_connection

logger = logging.getLogger(__name__)
bp = Blueprint("platform", __name__)


@bp.route("/api/platform/status", methods=["GET"])
def platform_status():
    """
    Public endpoint: returns active announcements.
    Used by base.html on every page load to show announcement banners.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Active announcements (not expired)
        # Supports optional ?role= and ?tenant_id= params to filter results.
        # Returns: global announcements (tenant_id IS NULL) + tenant-specific ones.
        role = request.args.get("role", "")
        tenant_id = request.args.get("tenant_id", "").strip() or None

        try:
            if tenant_id:
                cur.execute(
                    """
                    SELECT announcement_id, title, message, type, target_roles
                    FROM   announcements
                    WHERE  is_active = TRUE
                      AND  (expires_at IS NULL OR expires_at > NOW())
                      AND  (tenant_id IS NULL OR tenant_id = %s::uuid)
                    ORDER  BY created_at DESC
                    LIMIT  10
                    """,
                    (tenant_id,),
                )
            else:
                cur.execute(
                    """
                    SELECT announcement_id, title, message, type, target_roles
                    FROM   announcements
                    WHERE  is_active = TRUE
                      AND  (expires_at IS NULL OR expires_at > NOW())
                      AND  tenant_id IS NULL
                    ORDER  BY created_at DESC
                    LIMIT  10
                    """
                )
        except Exception:
            # Fallback if tenant_id column doesn't exist yet (pre-migration).
            # Must rollback first — psycopg2 aborts the transaction on any error.
            conn.rollback()
            cur.execute(
                """
                SELECT announcement_id, title, message, type, target_roles
                FROM   announcements
                WHERE  is_active = TRUE
                  AND  (expires_at IS NULL OR expires_at > NOW())
                ORDER  BY created_at DESC
                LIMIT  10
                """
            )

        rows = cur.fetchall()
        cur.close()

        announcements = []
        for r in rows:
            target_roles = r[4] or []
            # If target_roles is empty it applies to everyone; otherwise filter
            if target_roles and role and role not in target_roles:
                continue
            announcements.append(
                {
                    "id": r[0],
                    "title": r[1],
                    "message": r[2],
                    "type": r[3],
                }
            )

        return jsonify({"announcements": announcements}), 200
    except Exception as e:
        logger.error("Failed to fetch platform status: %s", e)
        return jsonify({"announcements": []}), 200
