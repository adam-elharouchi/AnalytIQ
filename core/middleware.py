"""
AnalytIQ request middleware.

Registered in app.py via @app.before_request.

Guards:
  1. IP blocklist   — 403 for banned IPs on all routes.
  2. Maintenance mode — 503 for non-superadmin API requests when maintenance is on.

Both guards use a 30-second in-memory cache to avoid a DB round-trip on every
request while still picking up changes within half a minute.
"""

import time as _time
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level caches (process-local, expires every _CACHE_TTL seconds)
# ---------------------------------------------------------------------------

_CACHE_TTL: float = 30.0

_ip_cache: dict = {"ips": frozenset(), "ts": 0.0}
_maint_cache: dict = {"active": False, "message": "", "ts": 0.0}

# Paths that are always allowed even during maintenance
_MAINTENANCE_EXEMPT: frozenset = frozenset(
    {
        "/api/users/signin",
        "/api/users/forgot-password",
        "/api/users/reset-password",
        "/api/platform/status",
        "/api/health",
    }
)


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _refresh_ip_blocklist():
    """Reload IP blocklist from DB if cache is stale."""
    now = _time.monotonic()
    if now - _ip_cache["ts"] <= _CACHE_TTL:
        return
    try:
        from core.database import get_db_connection
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT ip_address FROM ip_blocklist")
        _ip_cache["ips"] = frozenset(r[0] for r in cur.fetchall())
        cur.close()
        _ip_cache["ts"] = now
    except Exception as exc:
        logger.warning("IP blocklist refresh failed (fail-open): %s", exc)
        _ip_cache["ts"] = now  # avoid tight-loop retries on DB outage


def _refresh_maintenance():
    """Reload maintenance mode config from DB if cache is stale."""
    now = _time.monotonic()
    if now - _maint_cache["ts"] <= _CACHE_TTL:
        return
    try:
        from core.database import get_db_connection
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT key, value FROM platform_config WHERE key IN ('maintenance_mode','maintenance_message')"
        )
        rows = {r[0]: r[1] for r in cur.fetchall()}
        cur.close()
        _maint_cache["active"]  = rows.get("maintenance_mode", "false") == "true"
        _maint_cache["message"] = rows.get("maintenance_message", "")
        _maint_cache["ts"]      = now
    except Exception as exc:
        logger.warning("Maintenance-mode refresh failed (fail-open): %s", exc)
        _maint_cache["ts"] = now


# ---------------------------------------------------------------------------
# Request hook functions — registered in app.py
# ---------------------------------------------------------------------------

def check_ip_blocklist():
    """Block requests from IPs on the blocklist (403)."""
    from flask import request, jsonify

    if request.method == "OPTIONS":
        return  # handled by handle_options()

    _refresh_ip_blocklist()

    remote_ip = request.remote_addr or ""
    if remote_ip in _ip_cache["ips"]:
        return (jsonify({"error": "Access denied."}), 403)


def check_maintenance_mode():
    """Return 503 for non-superadmin API requests while maintenance mode is on."""
    from flask import request, jsonify

    if request.method == "OPTIONS":
        return
    if not request.path.startswith("/api"):
        return  # static files / HTML pages are served regardless

    _refresh_maintenance()
    if not _maint_cache["active"]:
        return

    # Exempt paths (signin, platform status, health check, etc.)
    if request.path.rstrip("/") in _MAINTENANCE_EXEMPT:
        return

    # Allow superadmins to pass through during maintenance
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            import jwt
            from config import Config as _config
            payload = jwt.decode(
                auth_header[7:],
                _config.JWT_SECRET_KEY,
                algorithms=["HS256"],
            )
            if payload.get("role") == "superadmin":
                return
        except Exception:
            pass  # fall through to 503

    msg = _maint_cache["message"] or "Platform is temporarily under maintenance. Please try again shortly."
    return (
        jsonify({"error": msg, "maintenance": True}),
        503,
    )
