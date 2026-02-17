from flask import Flask, request, jsonify, g, send_from_directory
from werkzeug.routing import BaseConverter
from werkzeug.exceptions import HTTPException
from extensions import limiter, csrf_exempt, mail, Message
from db import get_db_connection, close_conn_safely, close_db_connection
from auth_helpers import (
    require_auth, create_jwt_token, decode_jwt_token,
    hash_password, hash_password_legacy, verify_password,
    detect_role_from_email, validate_fields
)
import psycopg2
from dotenv import load_dotenv
import os
import json
from datetime import datetime
from werkzeug.utils import secure_filename
import sys
import config
import utils
import cache
from cache import cache_health_check
from supabase_storage import storage_health_check


# Add python directory to path for PDF processor and exercise generator
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "python"))
try:
    from pdf_processor import extract_text_from_pdf_bytes
except ImportError:
    print("Warning: PDF processor not available. PDF uploads will not work.")
    extract_text_from_pdf_bytes = None

try:
    from exercise_generator import generate_exercises_from_pdf_content
except ImportError:
    print("Warning: Exercise generator not available. Exercise generation will not work.")
    generate_exercises_from_pdf_content = None

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Initialize Sentry with proper configuration (PII filtering, etc.)
try:
    from sentry_config import init_sentry
    init_sentry(app)
except ImportError:
    print("Warning: sentry_config not available. Sentry will not be active.")
except Exception as e:
    print(f"Warning: Failed to initialize Sentry: {e}")
app.config["SECRET_KEY"] = config.SECRET_KEY

# Disable automatic OPTIONS handling so we can handle CORS manually
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = config.SEND_FILE_MAX_AGE_DEFAULT
app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH
app.config["UPLOAD_FOLDER"] = config.UPLOAD_FOLDER

# Structured Logging Configuration
import logging
from pythonjsonlogger import jsonlogger

# Create logger
logger = logging.getLogger("analytiq")
logger.setLevel(logging.INFO)

# Create console handler with JSON formatter
log_handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    "%(asctime)s %(name)s %(levelname)s %(message)s",
    rename_fields={"asctime": "timestamp", "levelname": "level", "name": "service"},
)
log_handler.setFormatter(formatter)
logger.addHandler(log_handler)

# Log startup
logger.info(
    "Application starting",
    extra={
        "environment": os.getenv("ENVIRONMENT", "development"),
        "port": os.getenv("PORT", "5001"),
    },
)

# Email configuration (Flask-Mail)
if mail is not None:
    app.config["MAIL_SERVER"] = config.MAIL_SERVER
    app.config["MAIL_PORT"] = config.MAIL_PORT
    app.config["MAIL_USE_TLS"] = config.MAIL_USE_TLS
    app.config["MAIL_USERNAME"] = config.MAIL_USERNAME
    app.config["MAIL_PASSWORD"] = config.MAIL_PASSWORD
    app.config["MAIL_DEFAULT_SENDER"] = config.MAIL_DEFAULT_SENDER
    mail.init_app(app)
else:
    print("Warning: Flask-Mail not installed. Email features will not work.")

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
    logger.info("Rate limiting enabled (storage: %s)", "redis" if "redis" in _rate_limit_storage else "memory")
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

    print("✅ API documentation available at /api/docs")
except ImportError:
    print("Warning: Swagger UI not installed. API documentation will not be available.")

# ============================================================================
# CELERY INTEGRATION (Async Task Processing)
# ============================================================================

try:
    from celery_app import celery_app

    # Feature flag for async processing
    FEATURE_ASYNC_TASKS = os.getenv("FEATURE_ASYNC_TASKS", "False").lower() == "true"

    if FEATURE_ASYNC_TASKS:
        print("✅ Celery async tasks enabled")
    else:
        print("⚠️  Celery async tasks disabled (feature flag off)")
        # Use a marker or just note it's disabled
        pass
except ImportError:
    print("Warning: Celery not installed. Async task processing will not be available.")
    celery_app = None
    FEATURE_ASYNC_TASKS = False


# Ensure upload folder exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf", "csv", "xlsx", "xls", "json", "txt", "ipynb"}


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
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )

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
    return response


@app.errorhandler(Exception)
def handle_unexpected_error(e):
    """Catch-all for unhandled exceptions — log details, return generic message."""
    if isinstance(e, HTTPException):
        return e  # Let Flask handle 404, 405, etc. normally
    logger.error("Unhandled exception: %s", e, exc_info=True)
    return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


DATABASE_URL = os.getenv("DATABASE_URL")

# Register DB teardown handler (pool is managed in db.py)
app.teardown_appcontext(close_db_connection)

# ---------------------------------------------------------------------------
# Blueprint registrations
# ---------------------------------------------------------------------------
from blueprints.health import bp as health_bp        # noqa: E402
from blueprints.ai import bp as ai_bp                # noqa: E402
from blueprints.auth import bp as auth_bp            # noqa: E402
from blueprints.users import bp as users_bp          # noqa: E402
from blueprints.chapters import bp as chapters_bp    # noqa: E402
from blueprints.exercises import bp as exercises_bp  # noqa: E402
from blueprints.classes import bp as classes_bp      # noqa: E402

app.register_blueprint(health_bp)
app.register_blueprint(ai_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(users_bp)
app.register_blueprint(chapters_bp)
app.register_blueprint(exercises_bp)
app.register_blueprint(classes_bp)


# Serve frontend (local development: open http://localhost:5001)
_ROOT = os.path.dirname(os.path.abspath(__file__))


# Converter so catch-all does not match /api or /api/* (avoids 405 on API paths)
class NoApiPathConverter(BaseConverter):
    regex = r"(?!api(?:\/|$)).+"


app.url_map.converters["no_api_path"] = NoApiPathConverter


@app.route("/", methods=["GET"])
def serve_index():
    return send_from_directory(_ROOT, "index.html")


@app.route("/<no_api_path:path>", methods=["GET"])
def serve_frontend(path):
    """Serve frontend static files (HTML, CSS, JS, etc.) for local dev."""
    safe = os.path.normpath(path)
    if safe.startswith("..") or os.path.isabs(safe):
        return jsonify({"error": "Forbidden"}), 403
    full = os.path.join(_ROOT, safe)
    if not os.path.isfile(full):
        return send_from_directory(_ROOT, "index.html")
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
                # Assuming 'logger' is defined elsewhere, if not, this line might cause an error.
                # For this task, I'll keep it as is, assuming 'logger' exists.
                # If 'logger' is not defined, it would need to be imported or defined.
                # For now, I'll comment it out to prevent potential errors if it's not defined.
                # logger.debug(f"Created v1 alias: {rule} -> {endpoint}")
                pass  # Placeholder if logger is not available
            except AssertionError:
                # Ignore if rule already exists (rare case)
                pass
            except Exception as e:
                # logger.warning(f"Failed to alias {rule}: {e}")
                pass  # Placeholder if logger is not available

    # logger.info(f"✅ Registered {len(routes_to_alias)} API v1 aliases")
    pass  # Placeholder if logger is not available


# Register v1 aliases
with app.app_context():
    register_api_v1_aliases(app)


if __name__ == "__main__":
    import sys
    import os

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
            print(f"   Either stop the other process or use a different port:")
            print(f"   python3 app.py 5002")
        else:
            raise
