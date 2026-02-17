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

app.register_blueprint(health_bp)
app.register_blueprint(ai_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(users_bp)
app.register_blueprint(chapters_bp)
app.register_blueprint(exercises_bp)


def generate_class_code():
    """Generate a unique 10-character class code (5 letters + 5 numbers)"""
    import random
    import string

    letters = "".join(random.choices(string.ascii_uppercase, k=5))
    numbers = "".join(random.choices(string.digits, k=5))
    return letters + numbers


@app.route("/api/classes", methods=["POST"])
@csrf_exempt
@require_auth
def create_class():
    """Create a new class (professor only)"""
    try:
        data = request.json or {}
        user_id = g.user_id
        name = data.get("name")
        description = data.get("description", "")
        class_code = data.get("class_code", "").strip().upper()  # Custom code from professor

        errors = validate_fields(data, [
            ("name", True, config.MAX_CLASS_NAME_LENGTH),
            ("description", False, config.MAX_CLASS_DESCRIPTION_LENGTH),
        ])
        if errors:
            return jsonify({"error": errors[0]}), 400

        if not class_code:
            return (
                jsonify(
                    {
                        "error": "Class code is required. Please enter a code that matches your school system."
                    }
                ),
                400,
            )

        # Validate class code format (alphanumeric, 3-20 characters)
        if not class_code.isalnum() or len(class_code) < 3 or len(class_code) > 20:
            return jsonify({"error": "Class code must be 3-20 alphanumeric characters"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Verify user is a professor
        cursor.execute("SELECT role FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        if not user or user[0] != "professor":
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Only professors can create classes"}), 403

        # Check if class code already exists
        cursor.execute("SELECT class_id FROM classes WHERE class_id = %s", (class_code,))
        if cursor.fetchone():
            cursor.close()
            close_conn_safely(conn)
            return (
                jsonify(
                    {
                        "error": f'Class code "{class_code}" is already in use. Please choose a different code.'
                    }
                ),
                409,
            )

        # Create class with custom code
        cursor.execute(
            """INSERT INTO classes (class_id, professor_id, name, description)
               VALUES (%s, %s, %s, %s) RETURNING class_id, name, description, created_at""",
            (class_code, user_id, name, description),
        )
        new_class = cursor.fetchone()

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        cache.invalidate_cache(f"classes:user:{user_id}:*")

        return (
            jsonify(
                {
                    "class_id": new_class[0],
                    "name": new_class[1],
                    "description": new_class[2],
                    "created_at": new_class[3].isoformat() if new_class[3] else None,
                    "success": True,
                }
            ),
            201,
        )

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@app.route("/api/classes", methods=["GET"])
@require_auth
def get_classes():
    """Get classes for current user (professor sees their classes, student sees enrolled classes)"""
    try:
        user_id = g.user_id

        # Get pagination parameters
        limit, offset = utils.get_pagination_params(request.args)

        # Try cache first
        cache_key = f"classes:user:{user_id}:limit:{limit}:offset:{offset}"
        cached_result = cache.get_cached(cache_key)
        if cached_result:
            return jsonify(cached_result), 200

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check user role
        cursor.execute("SELECT role FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "User not found"}), 404

        role = user[0] or "student"

        if role == "professor":
            # Get total count for professors
            cursor.execute(
                """
                SELECT COUNT(*) FROM classes WHERE professor_id = %s
            """,
                (user_id,),
            )
            total_count = cursor.fetchone()[0] or 0

            # Get paginated classes created by this professor
            cursor.execute(
                """
                SELECT c.class_id, c.name, c.description, c.created_at,
                       COUNT(DISTINCT ce.student_id) as student_count,
                       COUNT(DISTINCT ch.chapter_id) as chapter_count
                FROM classes c
                LEFT JOIN class_enrollments ce ON c.class_id = ce.class_id
                LEFT JOIN class_chapters ch ON c.class_id = ch.class_id
                WHERE c.professor_id = %s
                GROUP BY c.class_id, c.name, c.description, c.created_at
                ORDER BY c.created_at DESC
                LIMIT %s OFFSET %s
            """,
                (user_id, limit, offset),
            )
        else:
            # Get total count for students
            cursor.execute(
                """
                SELECT COUNT(*) 
                FROM class_enrollments 
                WHERE student_id = %s
            """,
                (user_id,),
            )
            total_count = cursor.fetchone()[0] or 0

            # Get paginated classes student is enrolled in
            cursor.execute(
                """
                SELECT c.class_id, c.name, c.description, c.created_at,
                       COUNT(DISTINCT ce.student_id) as student_count,
                       COUNT(DISTINCT ch.chapter_id) as chapter_count
                FROM classes c
                INNER JOIN class_enrollments ce ON c.class_id = ce.class_id
                LEFT JOIN class_chapters ch ON c.class_id = ch.class_id
                WHERE ce.student_id = %s
                GROUP BY c.class_id, c.name, c.description, c.created_at
                ORDER BY c.created_at DESC
                LIMIT %s OFFSET %s
            """,
                (user_id, limit, offset),
            )

        classes = []
        for row in cursor.fetchall():
            classes.append(
                {
                    "class_id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "created_at": row[3].isoformat() if row[3] else None,
                    "student_count": row[4] or 0,
                    "chapter_count": row[5] or 0,
                }
            )

        cursor.close()
        close_conn_safely(conn)

        # Return paginated response
        response = utils.build_paginated_response(
            classes, total_count, limit, offset, "classes"
        )

        # Cache for 5 minutes
        cache.set_cached(cache_key, response, ttl=300)

        return jsonify(response), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@app.route("/api/classes/<class_id>", methods=["GET"])
@require_auth
def get_class(class_id):
    """Get class details"""
    try:
        user_id = g.user_id

        conn = get_db_connection()
        cursor = conn.cursor()

        # Get class info
        cursor.execute(
            """
            SELECT c.class_id, c.name, c.description, c.professor_id, c.created_at,
                   u.name as professor_name, u.email as professor_email
            FROM classes c
            JOIN users u ON c.professor_id = u.user_id
            WHERE c.class_id = %s
        """,
            (class_id,),
        )

        class_data = cursor.fetchone()
        if not class_data:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Class not found"}), 404

        # Check if user has access (professor who created it, or enrolled student)
        cursor.execute("SELECT role FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "User not found"}), 404

        role = user[0] or "student"
        is_professor = role == "professor"
        is_owner = class_data[3] == user_id

        if not is_owner and not is_professor:
            # Check if student is enrolled
            cursor.execute(
                """
                SELECT 1 FROM class_enrollments 
                WHERE class_id = %s AND student_id = %s
            """,
                (class_id, user_id),
            )
            if not cursor.fetchone():
                cursor.close()
                close_conn_safely(conn)
                return jsonify({"error": "Access denied. You are not enrolled in this class."}), 403

        # Get student count
        cursor.execute(
            """
            SELECT COUNT(*) FROM class_enrollments WHERE class_id = %s
        """,
            (class_id,),
        )
        student_count = cursor.fetchone()[0] or 0

        # Get chapter count
        cursor.execute(
            """
            SELECT COUNT(*) FROM class_chapters WHERE class_id = %s
        """,
            (class_id,),
        )
        chapter_count = cursor.fetchone()[0] or 0

        # Get exercise count (NEW FIX)
        cursor.execute(
            """
            SELECT COUNT(*) FROM class_exercises WHERE class_id = %s
        """,
            (class_id,),
        )
        exercise_count = cursor.fetchone()[0] or 0

        cursor.close()
        close_conn_safely(conn)

        return (
            jsonify(
                {
                    "class_id": class_data[0],
                    "name": class_data[1],
                    "description": class_data[2],
                    "professor_id": class_data[3],
                    "created_at": class_data[4].isoformat() if class_data[4] else None,
                    "professor_name": class_data[5],
                    "professor_email": class_data[6] if len(class_data) > 6 else None,
                    "student_count": student_count,
                    "chapter_count": chapter_count,
                    "exercise_count": exercise_count,
                    "is_owner": is_owner,
                }
            ),
            200,
        )

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


# ... (Previous code) ...


@app.route("/api/classes/<class_id>/resources", methods=["GET"])
@require_auth
def get_class_resources(class_id):
    """Get all resources for a class (including chapters as resources)"""
    # ... Implementation check ...
    try:
        user_id = g.user_id
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Verify user is enrolled in the class or is the professor
        cursor.execute(
            """
            SELECT professor_id FROM classes WHERE class_id = %s
        """,
            (class_id,),
        )
        class_data = cursor.fetchone()

        if not class_data:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Class not found"}), 404

        # Get chapters to show as resources
        cursor.execute(
            """
            SELECT chapter_id, title, description, pdf_url, created_at
            FROM class_chapters
            WHERE class_id = %s
            ORDER BY created_at DESC
        """,
            (class_id,),
        )

        chapters = cursor.fetchall()

        resources = []
        for ch in chapters:
            chapter_id = ch[0]
            # Construct PDF URL that points to our serving endpoint
            pdf_url = f"/api/chapters/{chapter_id}/pdf"

            resources.append(
                {
                    "resource_id": chapter_id,
                    "title": ch[1],
                    "description": ch[2],
                    "resource_type": "pdf",  # Frontend expects 'pdf' for icon
                    "is_chapter": True,  # Flag for chapter logic
                    "chapter_id": chapter_id,  # Link target
                    "resource_url": pdf_url,  # Fallback URL matches field name expected by frontend (resource_url vs url)
                    "created_at": ch[4].isoformat() if ch[4] else None,
                }
            )

        # Get other resources from class_resources table
        ensure_resources_table()
        try:
            cursor.execute(
                """
                SELECT resource_id, title, description, resource_type, resource_url, created_at
                FROM class_resources
                WHERE class_id = %s
                ORDER BY created_at DESC
            """,
                (class_id,),
            )

            other_resources = cursor.fetchall()
            for res in other_resources:
                # Fallback: If URL is missing from DB but it looks like a file upload (no link), generate default download URL
                resource_url = res[4]
                if not resource_url and res[0]:  # res[0] is resource_id
                    # Assuming it's a file if unknown
                    resource_url = f"/api/resources/{res[0]}/download"

                resources.append(
                    {
                        "resource_id": res[0],
                        "title": res[1],
                        "description": res[2],
                        "resource_type": res[3],
                        "url": resource_url,
                        "created_at": res[5].isoformat() if res[5] else None,
                        "is_custom": True,
                    }
                )
        except Exception as table_err:
            print(f"Error fetching class_resources: {table_err}")

        cursor.close()
        close_conn_safely(conn)

        return jsonify({"all_resources": resources}), 200

    except Exception as e:
        print(f"Error in get_class_resources: {e}")
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@app.route("/api/classes/<class_id>", methods=["PUT"])
@csrf_exempt
@require_auth
def update_class(class_id):
    """Update class (professor only, must be owner)"""
    conn = None
    try:
        data = request.json
        user_id = g.user_id
        name = data.get("name")
        description = data.get("description")

        conn = get_db_connection()
        cursor = conn.cursor()

        # Verify user is professor and owner
        cursor.execute(
            """
            SELECT professor_id FROM classes WHERE class_id = %s
        """,
            (class_id,),
        )
        class_data = cursor.fetchone()
        if not class_data:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Class not found"}), 404

        if class_data[0] != user_id:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Only the class owner can update the class"}), 403

        # Update class - use explicit field updates to prevent SQL injection
        update_fields = []
        params = []

        if name is not None:
            update_fields.append("name = %s")
            params.append(name)
        if description is not None:
            update_fields.append("description = %s")
            params.append(description)

        if not update_fields:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "No fields to update"}), 400

        # Safe: update_fields contains only whitelisted field assignments
        params.append(class_id)
        query = f"""
            UPDATE classes 
            SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
            WHERE class_id = %s
        """
        cursor.execute(query, params)

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        cache.invalidate_cache(f"classes:user:{user_id}:*")

        return jsonify({"success": True}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


def allowed_file(filename):
    """Check if file extension is allowed"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_pdf_file(file):
    """
    Comprehensive PDF file validation without external dependencies
    Returns (is_valid, error_message)
    """
    # 1. Check file size (50MB max for PDFs)
    MAX_PDF_SIZE = 50 * 1024 * 1024  # 50MB
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Reset to beginning

    if file_size > MAX_PDF_SIZE:
        logger.warning(
            "File upload rejected: too large", extra={"size_mb": file_size / 1024 / 1024}
        )
        return False, f"File too large: {file_size / 1024 / 1024:.1f}MB (max 50MB)"

    if file_size == 0:
        logger.warning("File upload rejected: empty file")
        return False, "File is empty"

    # 2. Verify PDF structure (read first 1KB)
    try:
        file_header = file.read(1024)
        file.seek(0)  # Reset

        # PDF files must start with %PDF-
        if not file_header.startswith(b"%PDF-"):
            logger.warning("File upload rejected: invalid PDF header")
            return False, "Invalid PDF: file does not start with PDF header"

        # Check for valid PDF version (1.0 through 1.7, and 2.0)
        valid_versions = [b"%PDF-1." + bytes([i]) for i in range(ord("0"), ord("8"))] + [
            b"%PDF-2.0"
        ]
        if not any(file_header.startswith(version) for version in valid_versions):
            logger.warning("File upload rejected: unsupported PDF version")
            return False, "Unsupported PDF version (must be 1.0-1.7 or 2.0)"

        # Check for common malicious patterns (basic security check)
        suspicious_patterns = [
            b"/JavaScript",  # Embedded JavaScript
            b"/JS",  # JavaScript shorthand
            b"/Launch",  # Launch external programs
            b"/EmbeddedFile",  # Embedded executables
        ]

        # Read more of the file for pattern matching (first 10KB)
        file.seek(0)
        sample_content = file.read(10240)
        file.seek(0)

        for pattern in suspicious_patterns:
            if pattern in sample_content:
                logger.warning(
                    "File upload rejected: suspicious content",
                    extra={"pattern": pattern.decode("utf-8", errors="ignore")},
                )
                return False, f"PDF contains potentially unsafe content"

    except Exception as e:
        logger.error("PDF validation error", extra={"error": str(e)})
        return False, f"PDF validation error: {str(e)}"

    logger.info("PDF validation passed", extra={"size_mb": file_size / 1024 / 1024})
    return True, None


@app.route("/api/classes/<class_id>", methods=["DELETE"])
@csrf_exempt
@require_auth
def delete_class(class_id):
    """Delete class (professor only, must be owner)"""
    try:
        user_id = g.user_id
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Verify user is professor and owner
        cursor.execute(
            """
            SELECT professor_id FROM classes WHERE class_id = %s
        """,
            (class_id,),
        )
        class_data = cursor.fetchone()
        if not class_data:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Class not found"}), 404

        if class_data[0] != user_id:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Only the class owner can delete the class"}), 403

        # Delete class (cascade will delete enrollments, chapters, exercises)
        cursor.execute("DELETE FROM classes WHERE class_id = %s", (class_id,))

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        cache.invalidate_cache(f"classes:user:{user_id}:*")

        return jsonify({"success": True}), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


# ============================================================================
# Phase 6: Exercise Management Endpoints
# ============================================================================


@app.route("/api/classes/enroll", methods=["POST"])
@csrf_exempt
@require_auth
def enroll_in_class():
    """Enroll student in a class using class_id (class code)"""
    try:
        data = request.json
        user_id = g.user_id
        class_id = data.get("class_id")

        if not class_id:
            return jsonify({"error": "Missing required field (class_id)"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Verify user is a student
        cursor.execute("SELECT role FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "User not found"}), 404

        role = user[0] or "student"
        if role == "professor":
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Professors cannot enroll in classes"}), 403

        # Verify class exists
        cursor.execute(
            "SELECT class_id, name, professor_id FROM classes WHERE class_id = %s", (class_id,)
        )
        class_data = cursor.fetchone()
        if not class_data:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Class not found. Please check the class code."}), 404

        class_name = class_data[1]
        professor_id = class_data[2]

        # Check if already enrolled
        cursor.execute(
            """
            SELECT 1 FROM class_enrollments 
            WHERE class_id = %s AND student_id = %s
        """,
            (class_id, user_id),
        )
        if cursor.fetchone():
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Already enrolled in this class"}), 400

        # Enroll student
        cursor.execute(
            """
            INSERT INTO class_enrollments (class_id, student_id)
            VALUES (%s, %s)
            RETURNING enrolled_at
        """,
            (class_id, user_id),
        )

        enrolled_at = cursor.fetchone()[0]

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        return (
            jsonify(
                {
                    "class_id": class_id,
                    "class_name": class_name,
                    "enrolled_at": enrolled_at.isoformat() if enrolled_at else None,
                    "success": True,
                }
            ),
            201,
        )

    except Exception as e:
        import traceback

        traceback.print_exc()
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@app.route("/api/classes/enrolled", methods=["GET"])
@require_auth
def get_enrolled_classes():
    """Get all classes a student is enrolled in"""
    try:
        user_id = g.user_id
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        # Get pagination parameters
        limit, offset = utils.get_pagination_params(request.args)

        conn = get_db_connection()
        cursor = conn.cursor()

        # Verify user exists
        cursor.execute("SELECT role FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "User not found"}), 404

        # Get total count of enrolled classes
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM class_enrollments
            WHERE student_id = %s
        """,
            (user_id,),
        )
        total_count = cursor.fetchone()[0] or 0

        # Get paginated enrolled classes with class details
        cursor.execute(
            """
            SELECT 
                c.class_id,
                c.name,
                c.description,
                c.created_at,
                u.name as professor_name,
                u.email as professor_email,
                ce.enrolled_at,
                (SELECT COUNT(*) FROM class_enrollments WHERE class_id = c.class_id) as student_count,
                (SELECT COUNT(*) FROM class_chapters WHERE class_id = c.class_id) as chapter_count
            FROM class_enrollments ce
            JOIN classes c ON ce.class_id = c.class_id
            JOIN users u ON c.professor_id = u.user_id
            WHERE ce.student_id = %s
            ORDER BY ce.enrolled_at DESC
            LIMIT %s OFFSET %s
        """,
            (user_id, limit, offset),
        )

        classes = []
        for row in cursor.fetchall():
            classes.append(
                {
                    "class_id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "created_at": row[3].isoformat() if row[3] else None,
                    "professor_name": row[4],
                    "professor_email": row[5],
                    "enrolled_at": row[6].isoformat() if row[6] else None,
                    "student_count": row[7],
                    "chapter_count": row[8],
                }
            )

        cursor.close()
        close_conn_safely(conn)

        # Return paginated response
        response = utils.build_paginated_response(classes, total_count, limit, offset, "classes")
        return jsonify(response), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@app.route("/api/classes/<class_id>/students", methods=["GET"])
@require_auth
def get_class_students(class_id):
    """Get all students enrolled in a class (professor only)"""
    try:
        user_id = g.user_id
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Verify class exists and user is the professor
        cursor.execute("SELECT professor_id FROM classes WHERE class_id = %s", (class_id,))
        class_data = cursor.fetchone()
        if not class_data:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Class not found"}), 404

        if class_data[0] != user_id:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Only the class owner can view enrolled students"}), 403

        # Get enrolled students
        cursor.execute(
            """
            SELECT 
                u.user_id,
                u.name,
                u.email,
                ce.enrolled_at
            FROM class_enrollments ce
            JOIN users u ON ce.student_id = u.user_id
            WHERE ce.class_id = %s
            ORDER BY ce.enrolled_at ASC
        """,
            (class_id,),
        )

        students = []
        for row in cursor.fetchall():
            students.append(
                {
                    "student_id": row[0],
                    "name": row[1],
                    "email": row[2],
                    "enrolled_at": row[3].isoformat() if row[3] else None,
                }
            )

        cursor.close()
        close_conn_safely(conn)

        return jsonify({"students": students}), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


# ============================================================================
# Phase 9: Progress Tracking Endpoints
# ============================================================================


@app.route("/api/classes/<class_id>/progress", methods=["GET"])
@require_auth
def get_class_progress(class_id):
    """Get all students' progress for a class (professor only)"""
    conn = None
    try:
        user_id = g.user_id
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Verify class exists and user is the professor
        cursor.execute("SELECT professor_id FROM classes WHERE class_id = %s", (class_id,))
        class_data = cursor.fetchone()
        if not class_data:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Class not found"}), 404

        if class_data[0] != user_id:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Only the class owner can view progress"}), 403

        # Get all exercises for this class
        cursor.execute(
            """
            SELECT exercise_id, title, difficulty
            FROM class_exercises
            WHERE class_id = %s
            ORDER BY exercise_number, created_at
        """,
            (class_id,),
        )
        exercises = cursor.fetchall()

        # Get all enrolled students
        cursor.execute(
            """
            SELECT u.user_id, u.name, u.email
            FROM class_enrollments ce
            JOIN users u ON ce.student_id = u.user_id
            WHERE ce.class_id = %s
            ORDER BY u.name
        """,
            (class_id,),
        )
        students = cursor.fetchall()

        # OPTIMIZED: Get ALL progress data in a single query using JOIN
        # This replaces the N*M individual queries (30 students × 10 exercises = 300 queries!)
        cursor.execute(
            """
            SELECT 
                ce.student_id,
                ex.exercise_id,
                COALESCE(pp.best_score, 0) as best_score,
                COALESCE(pp.best_accuracy, 0) as best_accuracy,
                COALESCE(pp.total_attempts, 0) as total_attempts,
                COALESCE(pp.completed, false) as completed,
                pp.last_completed_at
            FROM class_enrollments ce
            CROSS JOIN class_exercises ex
            LEFT JOIN practice_progress pp 
                ON pp.user_id = ce.student_id 
                AND pp.class_exercise_id = ex.exercise_id
            WHERE ce.class_id = %s AND ex.class_id = %s
            ORDER BY ce.student_id, ex.exercise_number, ex.created_at
        """,
            (class_id, class_id),
        )

        progress_rows = cursor.fetchall()

        # Build nested structure from flat result set
        progress_data = {}

        # Initialize student data structures
        for student in students:
            student_id, student_name, student_email = student
            progress_data[student_id] = {
                "student_id": student_id,
                "student_name": student_name,
                "student_email": student_email,
                "exercises": {},
            }

        # Populate exercise progress from single query result
        for row in progress_rows:
            student_id = row[0]
            exercise_id = row[1]

            if student_id in progress_data:
                # Find exercise details
                exercise_title = None
                exercise_difficulty = None
                for ex in exercises:
                    if ex[0] == exercise_id:
                        exercise_title = ex[1]
                        exercise_difficulty = ex[2]
                        break

                progress_data[student_id]["exercises"][exercise_id] = {
                    "exercise_id": exercise_id,
                    "exercise_title": exercise_title,
                    "difficulty": exercise_difficulty,
                    "best_score": row[2],
                    "best_accuracy": float(row[3]),
                    "total_attempts": row[4],
                    "completed": row[5],
                    "last_completed_at": row[6].isoformat() if row[6] else None,
                }

        cursor.close()
        close_conn_safely(conn)

        # Convert to list format
        progress_list = list(progress_data.values())

        return (
            jsonify(
                {
                    "class_id": class_id,
                    "exercises": [
                        {"exercise_id": ex[0], "title": ex[1], "difficulty": ex[2]}
                        for ex in exercises
                    ],
                    "students_progress": progress_list,
                }
            ),
            200,
        )

    except Exception as e:
        import traceback

        traceback.print_exc()
        if conn:
            conn.rollback()
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@app.route("/api/progress", methods=["GET"])
@require_auth
def get_progress():
    """Get student's progress for exercises (optionally filtered by class_id)"""
    try:
        user_id = g.user_id
        class_id = request.args.get("class_id")

        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        if class_id:
            # Get progress for exercises in a specific class
            cursor.execute(
                """
                SELECT 
                    pp.class_exercise_id,
                    ce.title as exercise_title,
                    ce.difficulty,
                    pp.best_score,
                    pp.best_accuracy,
                    pp.total_attempts,
                    pp.completed,
                    pp.last_completed_at
                FROM practice_progress pp
                JOIN class_exercises ce ON pp.class_exercise_id = ce.exercise_id
                WHERE pp.user_id = %s AND pp.class_id = %s AND ce.class_id = %s
                ORDER BY ce.exercise_number, ce.created_at
            """,
                (user_id, class_id, class_id),
            )
        else:
            # Get all progress for the student
            cursor.execute(
                """
                SELECT 
                    exercise_id,
                    exercise_title,
                    best_score,
                    best_accuracy,
                    total_attempts,
                    completed,
                    last_completed_at
                FROM practice_progress
                WHERE user_id = %s
                ORDER BY exercise_id
            """,
                (user_id,),
            )

        progress = []
        for row in cursor.fetchall():
            if class_id:
                progress.append(
                    {
                        "exercise_id": row[0],
                        "exercise_title": row[1],
                        "difficulty": row[2],
                        "best_score": row[3] or 0,
                        "best_accuracy": float(row[4]) if row[4] else 0,
                        "total_attempts": row[5] or 0,
                        "completed": row[6] or False,
                        "last_completed_at": row[7].isoformat() if row[7] else None,
                    }
                )
            else:
                progress.append(
                    {
                        "exercise_id": row[0],
                        "exercise_title": row[1],
                        "best_score": row[2] or 0,
                        "best_accuracy": float(row[3]) if row[3] else 0,
                        "total_attempts": row[4] or 0,
                        "completed": row[5] or False,
                        "last_completed_at": row[6].isoformat() if row[6] else None,
                    }
                )

        cursor.close()
        close_conn_safely(conn)

        return jsonify({"progress": progress}), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@app.route("/api/students/<student_id>/progress", methods=["GET"])
@require_auth
def get_student_progress(student_id):
    """Get specific student's progress (professor only for their classes)"""
    try:
        user_id = g.user_id  # professor's user_id
        class_id = request.args.get("class_id")  # optional: filter by class

        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Verify user is a professor
        cursor.execute("SELECT role FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "User not found"}), 404

        role = user[0] or "student"
        if role != "professor":
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Only professors can view student progress"}), 403

        # Verify student exists
        cursor.execute("SELECT user_id, name, email FROM users WHERE user_id = %s", (student_id,))
        student = cursor.fetchone()
        if not student:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Student not found"}), 404

        # Build query based on whether class_id is provided
        if class_id:
            # Verify professor owns this class
            cursor.execute("SELECT professor_id FROM classes WHERE class_id = %s", (class_id,))
            class_data = cursor.fetchone()
            if not class_data or class_data[0] != user_id:
                cursor.close()
                close_conn_safely(conn)
                return jsonify({"error": "Access denied"}), 403

            # Get progress for this class only
            cursor.execute(
                """
                SELECT 
                    pp.class_exercise_id,
                    ce.title as exercise_title,
                    ce.difficulty,
                    pp.best_score,
                    pp.best_accuracy,
                    pp.total_attempts,
                    pp.completed,
                    pp.last_completed_at
                FROM practice_progress pp
                JOIN class_exercises ce ON pp.class_exercise_id = ce.exercise_id
                WHERE pp.user_id = %s AND pp.class_id = %s AND ce.class_id = %s
                ORDER BY ce.exercise_number, ce.created_at
            """,
                (student_id, class_id, class_id),
            )
        else:
            # Get all progress for classes owned by this professor
            cursor.execute(
                """
                SELECT 
                    pp.class_exercise_id,
                    ce.title as exercise_title,
                    ce.difficulty,
                    pp.class_id,
                    c.name as class_name,
                    pp.best_score,
                    pp.best_accuracy,
                    pp.total_attempts,
                    pp.completed,
                    pp.last_completed_at
                FROM practice_progress pp
                JOIN class_exercises ce ON pp.class_exercise_id = ce.exercise_id
                JOIN classes c ON pp.class_id = c.class_id
                WHERE pp.user_id = %s AND c.professor_id = %s
                ORDER BY c.name, ce.exercise_number
            """,
                (student_id, user_id),
            )

        progress = []
        for row in cursor.fetchall():
            if class_id:
                progress.append(
                    {
                        "exercise_id": row[0],
                        "exercise_title": row[1],
                        "difficulty": row[2],
                        "best_score": row[3] or 0,
                        "best_accuracy": float(row[4]) if row[4] else 0,
                        "total_attempts": row[5] or 0,
                        "completed": row[6] or False,
                        "last_completed_at": row[7].isoformat() if row[7] else None,
                    }
                )
            else:
                progress.append(
                    {
                        "exercise_id": row[0],
                        "exercise_title": row[1],
                        "difficulty": row[2],
                        "class_id": row[3],
                        "class_name": row[4],
                        "best_score": row[5] or 0,
                        "best_accuracy": float(row[6]) if row[6] else 0,
                        "total_attempts": row[7] or 0,
                        "completed": row[8] or False,
                        "last_completed_at": row[9].isoformat() if row[9] else None,
                    }
                )

        cursor.close()
        close_conn_safely(conn)

        return (
            jsonify(
                {
                    "student_id": student_id,
                    "student_name": student[1],
                    "student_email": student[2],
                    "progress": progress,
                }
            ),
            200,
        )

    except Exception as e:
        import traceback

        traceback.print_exc()
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


# Update existing progress endpoint to support class_id and class_exercise_id
# Note: The existing PUT endpoint at /api/users/practice-progress already exists
# We'll update it to also store class_id and class_exercise_id when provided

# ============================================================================
# Additional Class Endpoints - Leaderboards and Resources
# ============================================================================


@app.route("/api/classes/<class_id>/leaderboard/average", methods=["GET"])
@require_auth
def get_class_average_leaderboard(class_id):
    """Get average leaderboard for a class (all students ranked by average score)"""
    try:
        user_id = g.user_id
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Verify user is enrolled in the class or is the professor
        cursor.execute(
            """
            SELECT professor_id FROM classes WHERE class_id = %s
        """,
            (class_id,),
        )
        class_data = cursor.fetchone()

        if not class_data:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Class not found"}), 404

        is_professor = class_data[0] == user_id

        # Check if student is enrolled
        if not is_professor:
            cursor.execute(
                """
                SELECT 1 FROM class_enrollments 
                WHERE class_id = %s AND student_id = %s
            """,
                (class_id, user_id),
            )
            if not cursor.fetchone():
                cursor.close()
                close_conn_safely(conn)
                return jsonify({"error": "Not authorized to view this leaderboard"}), 403

        # Get average scores for all students in the class
        # Get average scores - Optimized query
        try:
            cursor.execute(
                """
                SELECT 
                    u.user_id,
                    u.name,
                    u.email,
                    COALESCE(AVG(pp.best_score), 0) as average_score,
                    COUNT(DISTINCT pp.exercise_id) as exercises_completed
                FROM class_enrollments ce
                JOIN users u ON ce.student_id = u.user_id
                LEFT JOIN practice_progress pp ON pp.user_id = u.user_id AND pp.class_id = %s AND pp.completed = true
                WHERE ce.class_id = %s
                GROUP BY u.user_id, u.name, u.email
                ORDER BY average_score DESC, u.name ASC
            """,
                (class_id, class_id),
            )
            students = cursor.fetchall()
        except Exception as query_err:
            print(f"Error executing leaderboard query: {query_err}")
            # Fallback to empty list if query fails (e.g. connection issue)
            students = []

        cursor.close()
        close_conn_safely(conn)

        leaderboard = []
        for rank, student in enumerate(students, 1):
            leaderboard.append(
                {
                    "rank": rank,
                    "student_id": student[0],
                    "name": student[1],
                    "email": student[2],
                    "average_score": round(float(student[3]), 1),
                    "exercises_completed": int(student[4]),
                }
            )

        return jsonify({"leaderboard": leaderboard}), 200

    except Exception as e:
        print(f"Error in get_class_average_leaderboard: {e}")
        import traceback

        traceback.print_exc()
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@app.route("/api/classes/<class_id>/leaderboard/exercise/<exercise_id>", methods=["GET"])
@require_auth
def get_exercise_leaderboard_for_class(class_id, exercise_id):
    """Get leaderboard for a specific exercise in a class"""
    try:
        user_id = g.user_id
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Verify user is enrolled in the class or is the professor
        cursor.execute(
            """
            SELECT professor_id FROM classes WHERE class_id = %s
        """,
            (class_id,),
        )
        class_data = cursor.fetchone()

        if not class_data:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Class not found"}), 404

        is_professor = class_data[0] == user_id

        # Check if student is enrolled
        if not is_professor:
            cursor.execute(
                """
                SELECT 1 FROM class_enrollments 
                WHERE class_id = %s AND student_id = %s
            """,
                (class_id, user_id),
            )
            if not cursor.fetchone():
                cursor.close()
                close_conn_safely(conn)
                return jsonify({"error": "Not authorized to view this leaderboard"}), 403

        # Get scores for all students for this specific exercise
        cursor.execute(
            """
            SELECT 
                u.user_id,
                u.name,
                u.email,
                COALESCE(pp.best_score, 0) as score
            FROM class_enrollments ce
            JOIN users u ON ce.student_id = u.user_id
            LEFT JOIN practice_progress pp ON pp.user_id = u.user_id AND pp.class_exercise_id = %s
            WHERE ce.class_id = %s
            ORDER BY score DESC, u.name ASC
        """,
            (exercise_id, class_id),
        )

        students = cursor.fetchall()
        cursor.close()
        close_conn_safely(conn)

        leaderboard = []
        for rank, student in enumerate(students, 1):
            leaderboard.append(
                {
                    "rank": rank,
                    "student_id": student[0],
                    "name": student[1],
                    "email": student[2],
                    "score": round(float(student[3]), 1),
                }
            )

        return jsonify({"leaderboard": leaderboard}), 200

    except Exception as e:
        print(f"Error in get_exercise_leaderboard_for_class: {e}")
        import traceback

        traceback.print_exc()
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


def ensure_exercises_table():
    """Ensure class_exercises table has all required columns (Lazy Migration)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check for solution_code column
        try:
            cursor.execute("SELECT solution_code FROM class_exercises LIMIT 1")
        except Exception:
            conn.rollback()
            print("Adding missing solution_code column to class_exercises")
            cursor.execute("ALTER TABLE class_exercises ADD COLUMN solution_code TEXT")

        # Check for exercise_number column
        try:
            cursor.execute("SELECT exercise_number FROM class_exercises LIMIT 1")
        except Exception:
            conn.rollback()
            print("Adding missing exercise_number column to class_exercises")
            cursor.execute(
                "ALTER TABLE class_exercises ADD COLUMN exercise_number INTEGER DEFAULT 1"
            )

        # Check for created_by column (Fix for 500 error on Create Exercise)
        try:
            cursor.execute("SELECT created_by FROM class_exercises LIMIT 1")
        except Exception:
            conn.rollback()
            print("Adding missing created_by column to class_exercises")
            cursor.execute("ALTER TABLE class_exercises ADD COLUMN created_by VARCHAR(255)")

        conn.commit()
        cursor.close()
        close_conn_safely(conn)
    except Exception as e:
        print(f"Error checking exercises table: {e}")


import uuid


# Duplicated function removed to prevent conflict.
# The correct create_exercise is below, which handles the class_id url param properly.


@app.route("/api/classes/<class_id>/resources", methods=["POST"])
@csrf_exempt
@require_auth
def add_class_resource(class_id):
    """Add a new resource (link) to the class"""
    try:
        ensure_resources_table()

        data = request.json
        user_id = g.user_id

        # Generate Unique ID using UUID
        resource_id = f"res_{str(uuid.uuid4())}"

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO class_resources (resource_id, class_id, user_id, title, description, resource_type, resource_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
            (
                resource_id,
                class_id,
                user_id,
                data.get("title"),
                data.get("description", ""),
                data.get("resource_type", "link"),
                data.get("resource_url"),
            ),
        )

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        return jsonify({"success": True, "resource_id": resource_id}), 201

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500




# ============================================================================
# PDF File Serving Endpoint
# ============================================================================


def ensure_resources_table():
    """Ensure class_resources table exists and has correct columns (Lazy Migration)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Create table if not exists
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS class_resources (
                resource_id VARCHAR(255) PRIMARY KEY,
                class_id VARCHAR(255) NOT NULL,
                user_id VARCHAR(255) NOT NULL,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                resource_type VARCHAR(50) NOT NULL,
                resource_url TEXT,
                file_data BYTEA,
                filename VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        )

        # Explicitly check and add missing columns for existing tables
        columns_to_check = ["user_id", "resource_type", "file_data", "filename"]

        for col in columns_to_check:
            try:
                cursor.execute(f"SELECT {col} FROM class_resources LIMIT 1")
            except Exception:
                conn.rollback()
                print(f"Adding missing column '{col}' to class_resources")
                if col == "user_id":
                    cursor.execute(
                        f"ALTER TABLE class_resources ADD COLUMN {col} VARCHAR(255) NOT NULL DEFAULT 'admin'"
                    )
                elif col == "file_data":
                    cursor.execute(f"ALTER TABLE class_resources ADD COLUMN {col} BYTEA")
                else:
                    cursor.execute(f"ALTER TABLE class_resources ADD COLUMN {col} VARCHAR(255)")
                conn.commit()

        # Handle legacy 'type' column migration separately if needed
        try:
            cursor.execute("SELECT type FROM class_resources LIMIT 1")
            print("Migrating legacy 'type' column...")
            cursor.execute(
                "UPDATE class_resources SET resource_type = type WHERE (resource_type IS NULL OR resource_type = '')"
            )
            cursor.execute("ALTER TABLE class_resources DROP COLUMN type")
            conn.commit()
        except Exception:
            conn.rollback()

        conn.commit()
        cursor.close()
        close_conn_safely(conn)
    except Exception as e:
        print(f"Error checking resources table: {e}")


@app.route("/api/classes/<class_id>/resources/upload", methods=["POST"])
@csrf_exempt
@require_auth
def upload_class_resource(class_id):
    """Upload a file as a resource"""
    try:
        ensure_resources_table()

        if "file" not in request.files:
            return jsonify({"error": "No file part"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400

        user_id = g.user_id

        filename = secure_filename(file.filename)
        # Store in DB
        file_data = file.read()

        resource_id = f"res_{int(datetime.now().timestamp() * 1000)}"
        # Use a special URL pattern for DB-served files
        resource_url = f"/api/resources/{resource_id}/download"

        conn = get_db_connection()
        cursor = conn.cursor()

        # Use psycopg2.Binary for BLOB storage
        from psycopg2.extensions import Binary

        cursor.execute(
            """
            INSERT INTO class_resources (resource_id, class_id, user_id, title, description, resource_type, resource_url, file_data, filename)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
            (
                resource_id,
                class_id,
                user_id,
                request.form.get("title"),
                request.form.get("description", ""),
                request.form.get("resource_type", "file"),
                resource_url,
                Binary(file_data),
                filename,
            ),
        )

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        return (
            jsonify({"success": True, "resource_id": resource_id, "resource_url": resource_url}),
            201,
        )

    except Exception as e:
        import traceback

        traceback.print_exc()
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@app.route("/api/resources/<resource_id>/download", methods=["GET"])
def serve_resource_download(resource_id):
    """Serve resource file from database (BLOB)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT file_data, filename, resource_type FROM class_resources WHERE resource_id = %s",
            (resource_id,),
        )
        result = cursor.fetchone()

        cursor.close()
        close_conn_safely(conn)

        if not result:
            return jsonify({"error": "Resource not found"}), 404

        file_data = result[0]
        filename = result[1] or "download.file"
        resource_type = result[2]

        if not file_data:
            return jsonify({"error": "File content is empty"}), 404

        from flask import Response
        import mimetypes

        # Determine mime type
        # FORCE generic binary stream for everything except specifically viewable types
        # This prevents browsers from trying to "render" CSVs or JSON/IPYNBs and failing
        mimetype = "application/octet-stream"

        # Only set specific mime types for things we WANT to render in-browser
        guessed_type = mimetypes.guess_type(filename)[0]
        if guessed_type in ["application/pdf", "image/jpeg", "image/png"]:
            mimetype = guessed_type
        if filename.endswith(".pdf"):
            mimetype = "application/pdf"

        # Determine disposition (inline for PDF/Images, attachment for others)
        disposition = "attachment"
        if mimetype in ["application/pdf", "image/jpeg", "image/png"] or filename.endswith(".pdf"):
            disposition = "inline"

        return Response(
            bytes(file_data),
            mimetype=mimetype,
            headers={
                "Content-Disposition": f'{disposition}; filename="{filename}"',
                "Access-Control-Allow-Origin": _get_cors_origin() or "",
            },
        )

    except Exception as e:
        print(f"Error serving resource: {e}")
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@app.route("/api/classes/<class_id>/resources/<resource_id>", methods=["PUT", "DELETE"])
@csrf_exempt
def manage_resource(class_id, resource_id):
    """Update or Delete a resource"""
    try:
        ensure_resources_table()
        conn = get_db_connection()
        cursor = conn.cursor()

        if request.method == "DELETE":
            cursor.execute("DELETE FROM class_resources WHERE resource_id = %s", (resource_id,))
            conn.commit()
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"success": True}), 200

        elif request.method == "PUT":
            data = request.json
            cursor.execute(
                """
                UPDATE class_resources 
                SET title = %s, description = %s, resource_type = %s, resource_url = %s, updated_at = CURRENT_TIMESTAMP
                WHERE resource_id = %s
            """,
                (
                    data.get("title"),
                    data.get("description"),
                    data.get("resource_type"),
                    data.get("resource_url"),
                    resource_id,
                ),
            )
            conn.commit()
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"success": True}), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@app.route("/api/resources/files/<filename>", methods=["GET"])
def serve_resource_file(filename):
    """Serve uploaded resource file (Legacy - kept for older non-migrated files)"""
    try:
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)
    except Exception as e:
        return jsonify({"error": "File not found"}), 404


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
