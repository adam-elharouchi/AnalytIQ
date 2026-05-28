"""
AnalytIQ request middleware.

Registered in app.py via @app.before_request.

Guards:
  1. IP blocklist — 403 for banned IPs on all routes.

Uses a 30-second in-memory cache to avoid a DB round-trip on every request.
"""

import time as _time
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level cache (process-local, expires every _CACHE_TTL seconds)
# ---------------------------------------------------------------------------

_CACHE_TTL: float = 30.0

_ip_cache: dict = {"ips": frozenset(), "ts": 0.0}


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
