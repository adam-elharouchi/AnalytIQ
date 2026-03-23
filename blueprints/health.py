"""
Health, CSRF, Task Status, and Contact blueprints.

Routes:
  GET  /api/health
  GET  /api/csrf-token
  GET  /api/tasks/<task_id>
  POST /api/contact
"""

import logging
import time
from datetime import datetime

from flask import Blueprint, jsonify, request

import config
from core.auth import decode_jwt_token, require_auth, validate_fields
from core.cache import cache_health_check
from workers.celery_app import celery_app
from core.database import close_conn_safely, get_db_connection
from core.extensions import csrf_exempt
from core.storage import storage_health_check

logger = logging.getLogger(__name__)
bp = Blueprint("health", __name__)

# 30-second in-process cache for /api/health results
_health_cache = None  # type: ignore[var-annotated]  (tuple of health_status dict + status_code int)
_health_cache_time = 0.0
_HEALTH_CACHE_TTL = 30  # seconds


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


def _run_health_checks():
    """Run all service health checks; return (status_dict, http_code). Cached 30 s."""
    global _health_cache, _health_cache_time

    now = time.monotonic()
    if _health_cache is not None and (now - _health_cache_time) < _HEALTH_CACHE_TTL:
        return _health_cache

    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {},
    }
    all_healthy = True

    # 1. Database (CRITICAL)
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        close_conn_safely(conn)
        health_status["services"]["database"] = {
            "status": "healthy",
            "connection_pool": {"max_connections": 25, "min_connections": 2},
        }
        logger.info("Health check: database healthy")
    except Exception:
        all_healthy = False
        health_status["services"]["database"] = {"status": "unhealthy"}
        logger.error("Health check: database unhealthy", exc_info=True)

    # 2. Gemini API (NON-CRITICAL)
    gemini_api_key = config.GEMINI_API_KEY
    if gemini_api_key and gemini_api_key != "your_gemini_api_key_here":
        health_status["services"]["gemini_api"] = {
            "status": "configured",
            "note": "API key present and configured",
        }
    else:
        health_status["services"]["gemini_api"] = {
            "status": "not_configured",
            "note": "API key not set - exercise generation disabled",
            "impact": "Exercise generation unavailable",
        }

    # 3. Email service (NON-CRITICAL)
    try:
        import resend

        if getattr(resend, "api_key", None) or config.RESEND_API_KEY:
            health_status["services"]["email"] = {
                "status": "configured",
                "note": "Resend configured",
            }
        else:
            health_status["services"]["email"] = {
                "status": "not_configured",
                "note": "Resend API key missing",
                "impact": "Password reset emails unavailable",
            }
    except Exception:
        health_status["services"]["email"] = {
            "status": "degraded",
            "impact": "Email features may be unavailable",
        }
        logger.warning("Health check: Email service degraded", exc_info=True)

    # 4. Redis Cache (NON-CRITICAL)
    if config.FEATURE_CACHING:
        try:
            cache_status = cache_health_check()
            health_status["services"]["cache"] = cache_status
            if not cache_status.get("healthy", False):
                logger.warning("Health check: Cache unhealthy: %s", cache_status.get("message"))
        except Exception:
            health_status["services"]["cache"] = {"status": "error"}
            logger.error("Health check: Cache error", exc_info=True)
    else:
        health_status["services"]["cache"] = {
            "status": "disabled",
            "note": "Caching feature flag off",
        }

    # 5. Supabase Storage (NON-CRITICAL — PDF uploads degrade gracefully)
    try:
        storage_status = storage_health_check()
        health_status["services"]["storage"] = storage_status
        if not storage_status.get("healthy", False):
            logger.warning("Health check: Storage unhealthy: %s", storage_status.get("message"))
    except Exception:
        health_status["services"]["storage"] = {"status": "error"}
        logger.warning("Health check: Storage error", exc_info=True)

    status_code = 200
    if not all_healthy:
        health_status["status"] = "degraded"
        logger.warning("Health check: system degraded")
        status_code = 503
    else:
        logger.info("Health check: all systems healthy")

    _health_cache = (health_status, status_code)
    _health_cache_time = time.monotonic()
    return _health_cache


@bp.route("/api/health", methods=["GET"])
def health():
    """Minimal public health probe — 200 healthy, 503 degraded.

    Returns only {"status": "healthy|degraded"} so internal service details
    are not exposed publicly.  Used by Render's healthCheckPath.
    """
    _, status_code = _run_health_checks()
    status = "healthy" if status_code == 200 else "degraded"
    return jsonify({"status": status}), status_code


@bp.route("/api/health/detail", methods=["GET"])
@require_auth
def health_detail():
    """Authenticated detailed health check — full service diagnostics.

    Requires a valid Bearer token.  Returns the complete health_status dict
    with per-service breakdowns (database, gemini_api, email, cache, storage).
    """
    health_status, status_code = _run_health_checks()
    return jsonify(health_status), status_code


# ---------------------------------------------------------------------------
# CSRF token
# ---------------------------------------------------------------------------


@bp.route("/api/csrf-token", methods=["GET"])
def get_csrf_token():
    """Generate and return a CSRF token for the client."""
    if not config.FEATURE_CSRF_PROTECTION:
        return (
            jsonify({"csrf_enabled": False, "message": "CSRF protection is currently disabled"}),
            200,
        )

    try:
        try:
            from flask_wtf.csrf import generate_csrf
        except ImportError:
            generate_csrf = None

        if generate_csrf:
            token = generate_csrf()
            return jsonify({"csrf_enabled": True, "csrf_token": token}), 200
        else:
            return jsonify({"csrf_enabled": False, "error": "CSRF module not available"}), 500
    except Exception:
        logger.error("Failed to generate CSRF token", exc_info=True)
        return jsonify({"error": "Failed to generate CSRF token"}), 500


# ---------------------------------------------------------------------------
# Async task status
# ---------------------------------------------------------------------------


@bp.route("/api/tasks/<task_id>", methods=["GET"])
def get_task_status(task_id):
    """Get the status of an async Celery task."""
    if not celery_app or not config.FEATURE_ASYNC_TASKS:
        return jsonify({"error": "Async tasks not enabled", "task_id": task_id}), 503

    try:
        from celery.result import AsyncResult

        task = AsyncResult(task_id, app=celery_app)

        response = {
            "task_id": task_id,
            "status": task.state,
        }

        if task.state == "PENDING":
            response["message"] = "Task is waiting to be processed"
        elif task.state == "STARTED":
            response["message"] = "Task is currently being processed"
        elif task.state == "SUCCESS":
            response["result"] = task.result
            response["message"] = "Task completed successfully"
        elif task.state == "FAILURE":
            logger.error("Async task failed: task_id=%s info=%s", task_id, task.info)
            response["message"] = "Task failed"
        elif task.state == "RETRY":
            response["message"] = "Task is being retried"
        else:
            response["message"] = f"Task state: {task.state}"

        return jsonify(response), 200

    except Exception:
        logger.error("Failed to get task status: task_id=%s", task_id, exc_info=True)
        return (
            jsonify(
                {"error": "Failed to retrieve task status. Please try again.", "task_id": task_id}
            ),
            500,
        )


# ---------------------------------------------------------------------------
# Contact form
# ---------------------------------------------------------------------------


@bp.route("/api/contact", methods=["POST"])
@csrf_exempt
def submit_contact():
    """Submit a contact form message."""
    try:
        data = request.json or {}
        name = data.get("name")
        email = data.get("email")
        subject = data.get("subject")
        message = data.get("message")

        errors = validate_fields(
            data,
            [
                ("name", True, config.MAX_NAME_LENGTH),
                ("email", True, config.MAX_EMAIL_LENGTH),
                ("subject", True, 200),
                ("message", True, config.MAX_GENERIC_TEXT_LENGTH),
            ],
        )
        if errors:
            return jsonify({"error": errors[0]}), 400

        # Optional: extract user_id from JWT if present
        user_id = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                payload = decode_jwt_token(auth_header.split(" ", 1)[1])
                user_id = str(payload["user_id"])
            except Exception:
                pass  # Contact form works without auth

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO contact_submissions (name, email, subject, message, user_id, status, created_at)
            VALUES (%s, %s, %s, %s, %s, 'unread', NOW())
        """,
            (name, email, subject, message, user_id),
        )

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        return jsonify({"success": True, "message": "Contact message submitted successfully"}), 201

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500
