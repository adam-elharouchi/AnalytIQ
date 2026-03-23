"""
Application factory helpers.

create_app() in app.py calls these functions in order. Each function handles
one concern, making the startup sequence explicit and independently testable.

Import graph (no circular imports):
    app.py  →  core.factory  →  config, core.*, blueprints.*
"""

from __future__ import annotations

import logging
import os
import uuid

import config

logger = logging.getLogger("analytiq")


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def setup_logging(app) -> None:
    """Configure structured JSON logging with per-request tracing."""
    try:
        from pythonjsonlogger import jsonlogger
    except ImportError:
        logging.basicConfig(level=logging.INFO)
        logger.warning("python-json-logger not installed; using plain text logging")
        return

    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(request_id)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level", "name": "service"},
    )
    handler.setFormatter(formatter)

    class _RequestIdFilter(logging.Filter):
        """Inject g.request_id into every log record for distributed tracing."""

        def filter(self, record):
            try:
                from flask import g as _g
                record.request_id = getattr(_g, "request_id", "-")
            except RuntimeError:
                record.request_id = "-"
            return True

    _filter = _RequestIdFilter()
    handler.addFilter(_filter)
    logging.root.addFilter(_filter)

    logger.addHandler(handler)
    logger.info(
        "Application starting",
        extra={
            "environment": os.getenv("ENVIRONMENT", "development"),
            "port": os.getenv("PORT", "5001"),
        },
    )


# ---------------------------------------------------------------------------
# App config
# ---------------------------------------------------------------------------


def configure_app(app) -> None:
    """Apply Flask config values from the centralized config module."""
    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = config.SEND_FILE_MAX_AGE_DEFAULT
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH
    app.config["UPLOAD_FOLDER"] = config.UPLOAD_FOLDER
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


# ---------------------------------------------------------------------------
# Sentry
# ---------------------------------------------------------------------------


def setup_sentry(app) -> None:
    """Initialize Sentry error tracking if configured."""
    try:
        from core.sentry import init_sentry
        init_sentry(app)
    except ImportError:
        logger.warning("core.sentry not available — Sentry inactive")
    except Exception as e:
        logger.warning("Failed to initialize Sentry: %s", e)


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


def setup_rate_limiting(app) -> None:
    """Initialize Flask-Limiter with Redis (prod) or memory (dev) storage."""
    from core.extensions import limiter

    try:
        storage = config.REDIS_URL if not config.DEBUG else "memory://"
        app.config["RATELIMIT_DEFAULT"] = (
            f"{config.RATE_LIMIT_DEFAULT_PER_DAY} per day;"
            f"{config.RATE_LIMIT_DEFAULT_PER_HOUR} per hour"
        )
        app.config["RATELIMIT_STORAGE_URL"] = storage
        app.config["RATELIMIT_STRATEGY"] = "fixed-window"
        limiter.init_app(app)
        logger.info(
            "Rate limiting enabled (storage: %s)",
            "redis" if "redis" in storage else "memory",
        )
    except Exception:
        logger.warning("Rate limiting could not be configured")


# ---------------------------------------------------------------------------
# CSRF
# ---------------------------------------------------------------------------


def setup_csrf(app) -> None:
    """
    Initialize Flask-WTF CSRF protection.

    When FEATURE_CSRF_PROTECTION=True the CSRFProtect instance is attached to
    the app AND injected into core.extensions so blueprints can use
    @csrf_exempt consistently.
    """
    try:
        from flask_wtf.csrf import CSRFProtect, generate_csrf  # noqa: F401
        from core import extensions as _ext

        app.config["WTF_CSRF_ENABLED"] = config.WTF_CSRF_ENABLED
        app.config["WTF_CSRF_TIME_LIMIT"] = config.WTF_CSRF_TIME_LIMIT
        app.config["WTF_CSRF_SSL_STRICT"] = config.WTF_CSRF_SSL_STRICT
        app.config["WTF_CSRF_CHECK_DEFAULT"] = config.WTF_CSRF_CHECK_DEFAULT

        csrf_instance = CSRFProtect()
        if config.FEATURE_CSRF_PROTECTION:
            csrf_instance.init_app(app)
            _ext.csrf = csrf_instance
            logger.info("CSRF protection enabled")
        else:
            logger.info("CSRF protection disabled (FEATURE_CSRF_PROTECTION=False)")
    except ImportError:
        logger.warning("Flask-WTF not installed — CSRF protection unavailable")


# ---------------------------------------------------------------------------
# Swagger / API docs
# ---------------------------------------------------------------------------


def setup_swagger(app) -> None:
    """Register Swagger UI blueprint and the /api/docs/spec.json endpoint."""
    try:
        from flask import jsonify
        from flask_swagger_ui import get_swaggerui_blueprint
        import blueprints.api_docs as api_docs

        SWAGGER_URL = "/api/docs"
        API_SPEC_URL = "/api/docs/spec.json"

        swaggerui_bp = get_swaggerui_blueprint(
            SWAGGER_URL,
            API_SPEC_URL,
            config={
                "app_name": "AnalytIQ API Documentation",
                "docExpansion": "list",
                "defaultModelsExpandDepth": 3,
                "displayRequestDuration": True,
            },
        )
        app.register_blueprint(swaggerui_bp, url_prefix=SWAGGER_URL)

        @app.route(API_SPEC_URL, methods=["GET"])
        def get_api_spec():
            return jsonify(api_docs.get_openapi_spec_dict())

        logger.info("API documentation available at /api/docs")
    except ImportError:
        logger.warning("flask-swagger-ui not installed — API docs unavailable")


# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------


def setup_celery(app) -> None:
    """Import Celery app so tasks are registered; log feature-flag state."""
    global FEATURE_ASYNC_TASKS
    try:
        from workers.celery_app import celery_app as _celery  # noqa: F401

        FEATURE_ASYNC_TASKS = config.FEATURE_ASYNC_TASKS
        if FEATURE_ASYNC_TASKS:
            logger.info("Celery async tasks enabled")
        else:
            logger.info("Celery async tasks disabled (FEATURE_ASYNC_TASKS=False)")
    except ImportError:
        logger.warning("Celery not installed — async task processing unavailable")
        FEATURE_ASYNC_TASKS = False


FEATURE_ASYNC_TASKS: bool = False


# ---------------------------------------------------------------------------
# Request hooks
# ---------------------------------------------------------------------------


def register_request_hooks(app) -> None:
    """Register before/after request hooks: request-ID, CORS, OPTIONS, security headers."""
    from flask import g, request

    from core.middleware import check_ip_blocklist, check_maintenance_mode

    app.before_request(check_ip_blocklist)
    app.before_request(check_maintenance_mode)

    @app.before_request
    def assign_request_id():
        g.request_id = str(uuid.uuid4())
        try:
            import sentry_sdk
            sentry_sdk.set_tag("request_id", g.request_id)
        except Exception:
            pass

    def _get_cors_origin():
        origin = request.headers.get("Origin", "")
        allowed = config.CORS_ORIGINS
        if "*" in allowed:
            return "*"
        if origin in allowed:
            return origin
        if not origin or origin == "null":
            return "*" if config.DEBUG else None
        return None

    @app.before_request
    def handle_options():
        if request.method == "OPTIONS":
            response = app.response_class()
            cors_origin = _get_cors_origin()
            if cors_origin:
                response.headers["Access-Control-Allow-Origin"] = cors_origin
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Max-Age"] = str(config.CORS_MAX_AGE)
            response.status_code = 200
            return response

    @app.after_request
    def after_request(response):
        if request.path.startswith("/api"):
            cors_origin = _get_cors_origin()
            if cors_origin:
                response.headers["Access-Control-Allow-Origin"] = cors_origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Credentials"] = "false"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            if not config.DEBUG:
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            # Prevent CDN/proxy from caching auth-gated API responses
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
        else:
            if not config.DEBUG:
                is_asset = request.path.endswith(
                    (".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg",
                     ".ico", ".woff", ".woff2")
                )
                if is_asset:
                    response.headers["Cache-Control"] = "public, max-age=86400"
                else:
                    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                    response.headers["Pragma"] = "no-cache"

        response.headers["Content-Security-Policy-Report-Only"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' "
            "https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://unpkg.com; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "font-src 'self'; "
            "frame-ancestors 'none'"
        )
        response.headers["X-Request-ID"] = getattr(g, "request_id", "")
        return response


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------


def register_error_handlers(app) -> None:
    """Register the global catch-all error handler."""
    from flask import jsonify, request
    from werkzeug.exceptions import HTTPException

    @app.errorhandler(Exception)
    def handle_unexpected_error(e):
        if isinstance(e, HTTPException):
            if request.path.startswith("/api"):
                return jsonify({"error": e.description}), e.code
            return e
        logger.error("Unhandled exception: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


# ---------------------------------------------------------------------------
# Blueprints
# ---------------------------------------------------------------------------


def register_blueprints(app) -> None:
    """Register all domain blueprints."""
    from blueprints.health import bp as health_bp
    from blueprints.ai import bp as ai_bp
    from blueprints.auth import bp as auth_bp
    from blueprints.users import bp as users_bp
    from blueprints.chapters import bp as chapters_bp
    from blueprints.exercises import bp as exercises_bp
    from blueprints.classes import bp as classes_bp
    from blueprints.lti import bp as lti_bp
    from blueprints.superadmin import bp as superadmin_bp
    from blueprints.content_import import bp as content_import_bp
    from blueprints.platform import bp as platform_bp
    from blueprints.sso import bp as sso_bp
    from blueprints.tenant_admin import bp as tenant_admin_bp
    from blueprints.flywheel import bp as flywheel_bp

    for bp in (
        health_bp, ai_bp, auth_bp, users_bp, chapters_bp,
        exercises_bp, classes_bp, lti_bp, superadmin_bp,
        content_import_bp, platform_bp, sso_bp, tenant_admin_bp, flywheel_bp,
    ):
        app.register_blueprint(bp)


# ---------------------------------------------------------------------------
# Frontend routes
# ---------------------------------------------------------------------------


def register_frontend_routes(app) -> None:
    """Register the SPA catch-all and named page routes.

    Routing strategy (strangler-fig migration):
    - /login, /classes, /dashboard, /class/* → React app (static/react/index.html)
    - All other non-API paths → legacy Jinja templates
    - /static/react/* → built React assets served directly
    """
    import os as _os
    from flask import jsonify, redirect, render_template, request, send_from_directory
    from jinja2 import TemplateNotFound
    from werkzeug.routing import BaseConverter

    _ROOT = _os.path.dirname(_os.path.abspath(app.root_path))
    _REACT_DIR = _os.path.join(_ROOT, "static", "react")

    # React-managed client routes — empty: all routes served by Jinja2 templates.
    _REACT_ROUTES: set[str] = set()

    def _serve_react():
        """Send the React app shell so React Router can take over."""
        react_index = _os.path.join(_REACT_DIR, "index.html")
        if _os.path.isfile(react_index):
            return send_from_directory(_REACT_DIR, "index.html")
        # Fallback: React build not present yet (dev without a build step)
        return render_template("landing.html")

    class NoApiPathConverter(BaseConverter):
        """Match any path that does NOT start with 'api' — keeps /api/* out of the catch-all."""
        regex = r"(?!api(?:\/|$)).+"

    app.url_map.converters["no_api_path"] = NoApiPathConverter

    @app.route("/", methods=["GET"])
    def serve_index():
        return render_template("landing.html")

    @app.route("/home", methods=["GET"])
    def serve_home():
        return render_template("index.html")

    @app.route("/<no_api_path:path>", methods=["GET"])
    def serve_frontend(path):
        safe = _os.path.normpath(path)
        if safe.startswith("..") or _os.path.isabs(safe):
            return jsonify({"error": "Forbidden"}), 403

        # Redirect legacy .html URLs to clean paths (permanent)
        if safe.endswith(".html"):
            clean = safe[:-5] or "/"
            return redirect(f"/{clean}", 301)

        # React routes: send the React shell
        top_segment = safe.split("/")[0]
        if top_segment in _REACT_ROUTES:
            return _serve_react()

        # Legacy Jinja templates
        try:
            return render_template(f"{safe}.html")
        except TemplateNotFound:
            pass

        # Static files (e.g. /static/react/assets/*)
        full = _os.path.join(_ROOT, safe)
        if _os.path.isfile(full):
            return send_from_directory(_ROOT, safe)

        return render_template("index.html")


# ---------------------------------------------------------------------------
# API versioning
# ---------------------------------------------------------------------------


def register_api_versioning(app) -> None:
    """
    Auto-create /api/v1/* aliases for every /api/* route.

    This lets clients migrate to versioned URLs gradually without a hard
    cutover, while establishing a versioning convention for future breaking
    changes.
    """
    routes_to_alias = []

    for rule in app.url_map.iter_rules():
        if rule.rule.startswith("/api/") and not rule.rule.startswith("/api/v1/"):
            new_rule = rule.rule.replace("/api/", "/api/v1/", 1)
            view_func = app.view_functions.get(rule.endpoint)
            if view_func:
                routes_to_alias.append((new_rule, rule.endpoint + "_v1", view_func, rule.methods))

    for rule, endpoint, view_func, methods in routes_to_alias:
        valid = [m for m in methods if m not in ("HEAD", "OPTIONS")]
        if valid:
            try:
                app.add_url_rule(rule, endpoint, view_func, methods=valid)
            except AssertionError:
                pass  # Already registered
            except Exception:
                pass  # Non-critical — skip silently

    logger.info("Registered %d API v1 aliases", len(routes_to_alias))


# ---------------------------------------------------------------------------
# Database migrations
# ---------------------------------------------------------------------------


def run_migrations(app) -> None:
    """Apply pending SQL migrations at startup (idempotent — safe to call repeatedly)."""
    try:
        from core.database import get_db_connection
        from db_migrate import run_migrations as _run

        with app.app_context():
            _run(get_db_connection())
    except Exception as e:
        logger.warning("Startup migration runner failed: %s", e)
