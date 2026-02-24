"""
Platform Blueprint — public-facing status and announcement endpoints.

Routes (no auth required):
  GET  /api/platform/status        — maintenance mode flag + active announcements
"""

import logging
from flask import Blueprint, jsonify, request

from db import get_db_connection

logger = logging.getLogger(__name__)
bp = Blueprint("platform", __name__)


@bp.route("/api/platform/status", methods=["GET"])
def platform_status():
    """
    Public endpoint: returns maintenance mode status and any active announcements.
    Used by base.html on every page load to show announcement banners.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Maintenance mode + message
        cur.execute(
            "SELECT key, value FROM platform_config WHERE key IN ('maintenance_mode', 'maintenance_message')"
        )
        config = {r[0]: r[1] for r in cur.fetchall()}
        maintenance = config.get("maintenance_mode", "false") == "true"
        maintenance_msg = config.get("maintenance_message", "")

        # Active announcements (not expired)
        # Filter by caller's role if provided via optional ?role= param
        role = request.args.get("role", "")
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

        return (
            jsonify(
                {
                    "maintenance": maintenance,
                    "maintenance_message": maintenance_msg,
                    "announcements": announcements,
                }
            ),
            200,
        )
    except Exception as e:
        logger.error("Failed to fetch platform status: %s", e)
        # Fail open — clients should not be blocked by a status check failure
        return jsonify({"maintenance": False, "announcements": []}), 200
