import logging
import os
import sys
import uuid

from dotenv import load_dotenv
from flask import Flask, g, jsonify, render_template, request, send_from_directory
from jinja2 import TemplateNotFound
from pythonjsonlogger import jsonlogger
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.routing import BaseConverter

import config
from db import close_db_connection  # teardown handler registered below
from extensions import limiter, mail


# Early logger — handlers are added below after JSON formatter is configured.
# These early startup warnings use Python's default stderr handler.
logger = logging.getLogger("analytiq")

# Add python directory to path for PDF processor and exercise generator
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "python"))
try:
    from pdf_processor import extract_text_from_pdf_bytes
except ImportError:
    logger.warning("PDF processor not available. PDF uploads will not work.")
    extract_text_from_pdf_bytes = None

try:
    from exercise_generator import generate_exercises_from_pdf_content
except ImportError:
    logger.warning("Exercise generator not available. Exercise generation will not work.")
    generate_exercises_from_pdf_content = None

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Initialize Sentry with proper configuration (PII filtering, etc.)
try:
    from sentry_config import init_sentry

    init_sentry(app)
except ImportError:
    logger.warning("sentry_config not available. Sentry will not be active.")
except Exception as e:
    logger.warning("Failed to initialize Sentry: %s", e)
app.config["SECRET_KEY"] = config.SECRET_KEY

# Disable automatic OPTIONS handling so we can handle CORS manually
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = config.SEND_FILE_MAX_AGE_DEFAULT
app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH
app.config["UPLOAD_FOLDER"] = config.UPLOAD_FOLDER

# Structured Logging Configuration — add JSON handler + request-ID filter
# logger was created early (top of file); now configure its handler
logger.setLevel(logging.INFO)

# Create console handler with JSON formatter
log_handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    "%(asctime)s %(name)s %(levelname)s %(request_id)s %(message)s",
    rename_fields={"asctime": "timestamp", "levelname": "level", "name": "service"},
)
log_handler.setFormatter(formatter)
logger.addHandler(log_handler)


class _RequestIdFilter(logging.Filter):
    """Inject g.request_id into every log record for structured tracing."""

    def filter(self, record):
        try:
            from flask import g as _g

            record.request_id = getattr(_g, "request_id", "-")
        except RuntimeError:
            record.request_id = "-"
        return True


_rid_filter = _RequestIdFilter()
log_handler.addFilter(_rid_filter)
# Apply to root logger so blueprint loggers (which propagate to root) also get it
logging.root.addFilter(_rid_filter)

# Log startup
logger.info(
    "Application starting",
    extra={
        "environment": os.getenv("ENVIRONMENT", "development"),
        "port": os.getenv("PORT", "5001"),
    },
)

# Email configuration (Flask-Mail)
# Email configuration has moved to Resend in tasks.py
if mail is not None:
    logger.warning("Mail initialization removed. Using Resend now.")

# Rate limiting — configured via extensions.py
try:
    _rate_limit_storage = config.REDIS_URL if not config.DEBUG else "memory://"
    app.config["RATELIMIT_DEFAULT"] = (
        f"{config.RATE_LIMIT_DEFAULT_PER_DAY} per day;"
        f"{config.RATE_LIMIT_DEFAULT_PER_HOUR} per hour"
    )
    app.config["RATELIMIT_STORAGE_URL"] = _rate_limit_storage
    app.config["RATELIMIT_STRATEGY"] = "fixed-window"
    limiter.init_app(app)
    logger.info(
        "Rate limiting enabled (storage: %s)",
        "redis" if "redis" in _rate_limit_storage else "memory",
    )
except Exception:
    logger.warning("Rate limiting could not be configured")

# CSRF Protection
csrf = None
try:
    from flask_wtf.csrf import CSRFProtect, generate_csrf

    csrf_instance = CSRFProtect()
    app.config["WTF_CSRF_ENABLED"] = config.WTF_CSRF_ENABLED
    app.config["WTF_CSRF_TIME_LIMIT"] = config.WTF_CSRF_TIME_LIMIT
    app.config["WTF_CSRF_SSL_STRICT"] = config.WTF_CSRF_SSL_STRICT
    app.config["WTF_CSRF_CHECK_DEFAULT"] = config.WTF_CSRF_CHECK_DEFAULT
    if config.FEATURE_CSRF_PROTECTION:
        csrf_instance.init_app(app)
        csrf = csrf_instance
        import extensions

        extensions.csrf = csrf_instance
        logger.info("CSRF protection enabled")
    else:
        logger.info("CSRF protection disabled (feature flag off)")
except ImportError:
    logger.warning("Flask-WTF not installed. CSRF protection will not work.")
    generate_csrf = None

# ============================================================================
# API DOCUMENTATION (Swagger UI)
# ============================================================================

try:
    from flask_swagger_ui import get_swaggerui_blueprint
    import api_docs

    # Swagger UI configuration
    SWAGGER_URL = "/api/docs"
    API_SPEC_URL = "/api/docs/spec.json"

    swaggerui_blueprint = get_swaggerui_blueprint(
        SWAGGER_URL,
        API_SPEC_URL,
        config={
            "app_name": "AnalytIQ API Documentation",
            "docExpansion": "list",
            "defaultModelsExpandDepth": 3,
            "displayRequestDuration": True,
        },
    )

    app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

    # Endpoint to serve the OpenAPI spec
    @app.route(API_SPEC_URL, methods=["GET"])
    def get_api_spec():
        """Serve the OpenAPI specification JSON"""
        return jsonify(api_docs.get_openapi_spec_dict())

    logger.info("API documentation available at /api/docs")
except ImportError:
    logger.warning("Swagger UI not installed. API documentation will not be available.")

# ============================================================================
# CELERY INTEGRATION (Async Task Processing)
# ============================================================================

try:
    from celery_app import celery_app

    # Feature flag for async processing
    FEATURE_ASYNC_TASKS = os.getenv("FEATURE_ASYNC_TASKS", "False").lower() == "true"

    if FEATURE_ASYNC_TASKS:
        logger.info("Celery async tasks enabled")
    else:
        logger.info("Celery async tasks disabled (feature flag off)")
except ImportError:
    logger.warning("Celery not installed. Async task processing will not be available.")
    celery_app = None
    FEATURE_ASYNC_TASKS = False


# Ensure upload folder exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


# CORS handling - uses configured origins (set CORS_ORIGINS env var in production)
def _get_cors_origin():
    """Return the allowed origin for the current request, or None."""
    origin = request.headers.get("Origin", "")
    allowed = config.CORS_ORIGINS  # list from env, e.g. ["https://www.myanalytiq.org"]

    # If wildcard is configured (development), allow everything
    if "*" in allowed:
        return "*"

    # Check if the request origin is in the allowed list
    if origin in allowed:
        return origin

    # Also allow file:// protocol for local development
    if not origin or origin == "null":
        return "*" if config.DEBUG else None

    return None


@app.before_request
def assign_request_id():
    """Assign a UUID per request for log tracing and the X-Request-ID response header."""
    g.request_id = str(uuid.uuid4())
    try:
        import sentry_sdk

        sentry_sdk.set_tag("request_id", g.request_id)
    except Exception:
        pass


@app.before_request
def handle_options():
    if request.method == "OPTIONS":
        response = app.response_class()
        cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers.add("Access-Control-Allow-Origin", cors_origin)
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        response.headers.add("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        response.headers.add("Access-Control-Max-Age", str(config.CORS_MAX_AGE))
        response.status_code = 200
        return response


@app.after_request
def after_request(response):
    # Add CORS headers to all API responses
    if request.path.startswith("/api"):
        cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers["Access-Control-Allow-Origin"] = cors_origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Credentials"] = "false"

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if not config.DEBUG:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # CDN-5: Prevent any proxy or CDN from caching API responses.
        # Auth-gated data must never be served stale from an edge cache.
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"

    else:
        # CDN-4: Cache static assets long-term; serve HTML fresh on every request.
        # HTML pages must never be cached by CDN — deploys must propagate instantly.
        # CSS, JS, and images are content-hashed implicitly via ETags and can be cached.
        if not config.DEBUG:
            is_static_asset = request.path.endswith(
                (".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".woff", ".woff2")
            )
            if is_static_asset:
                response.headers["Cache-Control"] = "public, max-age=86400"
            else:
                # HTML and everything else: revalidate on every request
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                response.headers["Pragma"] = "no-cache"

    # Content-Security-Policy in report-only mode on all responses.
    # Violations are logged in the browser console without blocking anything.
    # Switch to Content-Security-Policy (enforcement) once violations are reviewed.
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


@app.errorhandler(Exception)
def handle_unexpected_error(e):
    """Catch-all for unhandled exceptions — log details, return generic message."""
    if isinstance(e, HTTPException):
        # Return JSON for API routes so JS clients always get parseable errors
        if request.path.startswith("/api"):
            return jsonify({"error": e.description}), e.code
        return e  # HTML for non-API paths (404 pages, etc.)
    logger.error("Unhandled exception: %s", e, exc_info=True)
    return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


DATABASE_URL = os.getenv("DATABASE_URL")

# Register DB teardown handler (pool is managed in db.py)
app.teardown_appcontext(close_db_connection)

# ---------------------------------------------------------------------------
# Blueprint registrations
# ---------------------------------------------------------------------------
from blueprints.health import bp as health_bp  # noqa: E402
from blueprints.ai import bp as ai_bp  # noqa: E402
from blueprints.auth import bp as auth_bp  # noqa: E402
from blueprints.users import bp as users_bp  # noqa: E402
from blueprints.chapters import bp as chapters_bp  # noqa: E402
from blueprints.exercises import bp as exercises_bp  # noqa: E402
from blueprints.classes import bp as classes_bp  # noqa: E402
from blueprints.lti import bp as lti_bp  # noqa: E402
from blueprints.superadmin import bp as superadmin_bp  # noqa: E402
from blueprints.content_import import bp as content_import_bp  # noqa: E402
from blueprints.platform import bp as platform_bp  # noqa: E402
from middleware import check_ip_blocklist, check_maintenance_mode  # noqa: E402

app.register_blueprint(health_bp)
app.register_blueprint(ai_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(users_bp)
app.register_blueprint(chapters_bp)
app.register_blueprint(exercises_bp)
app.register_blueprint(classes_bp)
app.register_blueprint(lti_bp)
app.register_blueprint(superadmin_bp)
app.register_blueprint(content_import_bp)
app.register_blueprint(platform_bp)

# Platform-level request guards (IP blocklist + maintenance mode)
app.before_request(check_ip_blocklist)
app.before_request(check_maintenance_mode)

# ---------------------------------------------------------------------------
# Auto-apply pending SQL migrations at startup (idempotent).
# Ensures production DB schema is always in sync with the codebase.
# ---------------------------------------------------------------------------
try:
    from db import get_db_connection
    from db_migrate import run_migrations

    with app.app_context():
        run_migrations(get_db_connection())
except Exception as _mig_exc:
    import logging as _logging

    _logging.getLogger(__name__).warning("Startup migration runner failed: %s", _mig_exc)


# Serve frontend (local development: open http://localhost:5001)
_ROOT = os.path.dirname(os.path.abspath(__file__))


# Converter so catch-all does not match /api or /api/* (avoids 405 on API paths)
class NoApiPathConverter(BaseConverter):
    regex = r"(?!api(?:\/|$)).+"


app.url_map.converters["no_api_path"] = NoApiPathConverter


@app.route("/", methods=["GET"])
def serve_index():
    return render_template("index.html")


@app.route("/<no_api_path:path>", methods=["GET"])
def serve_frontend(path):
    """Serve frontend files: render HTML via Jinja2; serve static assets directly."""
    safe = os.path.normpath(path)
    if safe.startswith("..") or os.path.isabs(safe):
        return jsonify({"error": "Forbidden"}), 403
    if safe.endswith(".html"):
        try:
            return render_template(safe)
        except TemplateNotFound:
            return render_template("index.html")
    full = os.path.join(_ROOT, safe)
    if not os.path.isfile(full):
        return render_template("index.html")
    return send_from_directory(_ROOT, safe)


# ============================================================================
# API VERSIONING SETUP
# ============================================================================


def register_api_v1_aliases(app):
    """
    Automatically creates /api/v1/ aliases for all /api/ routes.
    This ensures backward compatibility while establishing versioning.
    """
    # Collect routes to alias (to avoid modifying dictionary while iterating)
    routes_to_alias = []

    for rule in app.url_map.iter_rules():
        if rule.rule.startswith("/api/") and not rule.rule.startswith("/api/v1/"):
            # Create new v1 rule
            new_rule = rule.rule.replace("/api/", "/api/v1/", 1)
            endpoint = rule.endpoint
            view_func = app.view_functions.get(endpoint)

            if view_func:
                routes_to_alias.append((new_rule, endpoint + "_v1", view_func, rule.methods))

    # Register aliases
    for rule, endpoint, view_func, methods in routes_to_alias:
        # Filter out methods that might be automatically handled
        valid_methods = [m for m in methods if m not in ("HEAD", "OPTIONS")]
        if valid_methods:
            try:
                app.add_url_rule(rule, endpoint, view_func, methods=valid_methods)
                logger.debug("Created v1 alias: %s -> %s", rule, endpoint)
            except AssertionError:
                pass  # Rule already exists (rare)
            except Exception:
                pass  # Non-critical; skip broken alias silently

    logger.info("Registered %d API v1 aliases", len(routes_to_alias))


# Register v1 aliases
with app.app_context():
    register_api_v1_aliases(app)


if __name__ == "__main__":
    import os  # noqa: F811 — re-imported so exec'd test namespaces have it
    import sys  # noqa: F811

    port = int(os.getenv("PORT", 5001))  # Changed from 5000 to avoid macOS AirPlay conflict
    if len(sys.argv) > 1:
        port = int(sys.argv[1])

    # Only run in debug mode if explicitly set or running locally
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true" or (
        os.getenv("FLASK_ENV") == "development" and "localhost" in os.getenv("HOST", "")
    )

    print(f"Starting Flask server on port {port}...")
    print(f"Debug mode: {debug_mode}")
    print(f"API base URL: http://localhost:{port}/api")
    print(f"Health check: http://localhost:{port}/api/health")

    # For local development, use 127.0.0.1 (safer)
    # For production, use 0.0.0.0 (accessible from outside)
    host = "0.0.0.0" if os.getenv("FLASK_ENV") == "production" else "127.0.0.1"

    try:
        app.run(debug=debug_mode, port=port, host=host)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"\n❌ Error: Port {port} is already in use!")
            print("   Either stop the other process or use a different port:")
            print("   python3 app.py 5002")
        else:
            raise
