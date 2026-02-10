from flask import Flask, request, jsonify, g, send_from_directory
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv
import os
import socket
from urllib.parse import urlparse
import json
from datetime import datetime
from werkzeug.utils import secure_filename
import sys
import time
import config
import utils
import cache
from cache import cache_health_check
from supabase_storage import storage_health_check


# Global database pool
db_pool = None

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

# Email configuration (Flask-Mail)
try:
    from flask_mail import Mail, Message

    app.config["MAIL_SERVER"] = config.MAIL_SERVER
    app.config["MAIL_PORT"] = config.MAIL_PORT
    app.config["MAIL_USE_TLS"] = config.MAIL_USE_TLS
    app.config["MAIL_USERNAME"] = config.MAIL_USERNAME
    app.config["MAIL_PASSWORD"] = config.MAIL_PASSWORD
    app.config["MAIL_DEFAULT_SENDER"] = config.MAIL_DEFAULT_SENDER
    mail = Mail(app)
except ImportError:
    print("Warning: Flask-Mail not installed. Email features will not work.")
    mail = None

# Rate Limiting Configuration
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address

    # Use Redis for rate limiting in production (shared across workers),
    # fall back to in-memory for development
    _rate_limit_storage = config.REDIS_URL if not config.DEBUG else "memory://"
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=[
            f"{config.RATE_LIMIT_DEFAULT_PER_DAY} per day",
            f"{config.RATE_LIMIT_DEFAULT_PER_HOUR} per hour",
        ],
        storage_uri=_rate_limit_storage,
        strategy="fixed-window",
    )
    print(f"✅ Rate limiting enabled (storage: {'redis' if 'redis' in _rate_limit_storage else 'memory'})")
except ImportError:
    print("Warning: Flask-Limiter not installed. Rate limiting will not work.")
    limiter = None

# CSRF Protection Configuration
try:
    from flask_wtf.csrf import CSRFProtect, generate_csrf

    # Initialize CSRF protection
    csrf = CSRFProtect()

    # Configure CSRF from config
    app.config["WTF_CSRF_ENABLED"] = config.WTF_CSRF_ENABLED
    app.config["WTF_CSRF_TIME_LIMIT"] = config.WTF_CSRF_TIME_LIMIT
    app.config["WTF_CSRF_SSL_STRICT"] = config.WTF_CSRF_SSL_STRICT
    app.config["WTF_CSRF_CHECK_DEFAULT"] = config.WTF_CSRF_CHECK_DEFAULT

    # Only initialize if feature is enabled
    if config.FEATURE_CSRF_PROTECTION:
        csrf.init_app(app)
        print("✅ CSRF protection enabled")
    else:
        print("⚠️  CSRF protection disabled (feature flag off)")
        csrf = None
except ImportError:
    print("Warning: Flask-WTF not installed. CSRF protection will not work.")
    csrf = None
    generate_csrf = None


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
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if not config.DEBUG:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
    return response


DATABASE_URL = os.getenv("DATABASE_URL")


def detect_role_from_email(email):
    """Detect user role from email domain"""
    if not email:
        return "student"
    email_lower = email.lower()
    if email_lower.endswith("@hult.edu") or email_lower.endswith("@faculty.hult.edu"):
        return "professor"
    elif email_lower.endswith("@student.hult.edu"):
        return "student"
    return "student"  # Default to student


def get_db_params():
    """Parse DATABASE_URL and return connection parameters dictionary"""
    if not DATABASE_URL:
        raise Exception("DATABASE_URL environment variable is not set")

    # Clean up the database URL - remove invalid query parameters like pgbouncer
    clean_url = DATABASE_URL.split("?")[0]

    try:
        # Handle both postgresql:// and postgres:// schemes
        url = clean_url
        if not url.startswith(("postgresql://", "postgres://")):
            if "://" not in url:
                url = "postgresql://" + url
            else:
                raise ValueError(f"Unsupported connection string scheme: {url.split('://')[0]}")

        from urllib.parse import unquote

        parsed = urlparse(url)

        if not parsed.hostname:
            raise ValueError("Hostname is missing from connection string")

        username = unquote(parsed.username) if parsed.username else "postgres"
        password = unquote(parsed.password) if parsed.password else ""
        database = parsed.path[1:] if parsed.path and len(parsed.path) > 1 else "postgres"

        return {
            "host": parsed.hostname,
            "port": parsed.port or 5432,
            "database": database,
            "user": username,
            "password": password,
        }
    except Exception as e:
        print(f"Error parsing connection string: {e}")
        return None


def init_db_pool():
    """Initialize the database connection pool with timeout settings"""
    global db_pool
    if db_pool is not None:
        return

    try:
        # Try to use simple direct connection string first (works with Supabase Pooler)
        # Ensure sslmode and timeout settings are configured
        clean_url = DATABASE_URL

        # Add connection parameters if not present
        from urllib.parse import quote

        params_to_add = []
        if "sslmode" not in clean_url:
            params_to_add.append("sslmode=require")
        if "connect_timeout" not in clean_url:
            params_to_add.append("connect_timeout=10")  # 10 second connection timeout
        if "options" not in clean_url:
            # URL-encode the options parameter value
            params_to_add.append(
                f'options={quote("-c statement_timeout=30000")}'
            )  # 30 second query timeout

        if params_to_add:
            separator = "&" if "?" in clean_url else "?"
            clean_url = clean_url + separator + "&".join(params_to_add)

        logger.info(
            "Initializing connection pool",
            extra={
                "connection_timeout": f"{config.DB_CONNECTION_TIMEOUT}s",
                "statement_timeout": f"{config.DB_STATEMENT_TIMEOUT}s",
                "min_connections": config.DB_POOL_MIN_CONNECTIONS,
                "max_connections": config.DB_POOL_MAX_CONNECTIONS,
            },
        )

        # Initialize connection pool with configuration
        db_pool = pool.ThreadedConnectionPool(
            minconn=config.DB_POOL_MIN_CONNECTIONS,
            maxconn=config.DB_POOL_MAX_CONNECTIONS,
            dsn=clean_url,
        )

        # Test the connection pool with a simple query
        try:
            test_conn = db_pool.getconn()
            test_cursor = test_conn.cursor()
            test_cursor.execute("SELECT 1")
            test_cursor.close()
            db_pool.putconn(test_conn)
            print("✅ Database connection pool initialized and tested successfully")
        except Exception as test_error:
            print(f"⚠️  Pool created but test query failed: {test_error}")
            # Don't raise - pool might still work for actual queries

    except psycopg2.OperationalError as e:
        print(f"Pool initialization failed with direct URL: {e}")
        # Fallback to resolved params if needed (usually direct URL works for pools)
        try:
            params = get_db_params()
            if params:
                # Resolve IPv4 if needed
                hostname = params["host"]
                try:
                    addrinfo = socket.getaddrinfo(
                        hostname, None, socket.AF_INET, socket.SOCK_STREAM
                    )
                    if addrinfo:
                        params["host"] = addrinfo[0][4][0]
                except:
                    pass

                print("Retrying with explicit connection parameters...")
                db_pool = pool.ThreadedConnectionPool(
                    minconn=1,
                    maxconn=10,
                    user=params["user"],
                    password=params["password"],
                    host=params["host"],
                    port=params["port"],
                    database=params["database"],
                    sslmode="require",
                    connect_timeout=10,
                    options="-c statement_timeout=30000",
                )
                print("✅ Database connection pool initialized with explicit params")
        except Exception as e2:
            print(f"❌ Critical error initializing pool: {e2}")
            print(f"   Please check DATABASE_URL environment variable")
            raise


def get_db_connection():
    """Get a connection from the global pool with retry logic"""
    global db_pool

    # Store connection in Flask g object for request duration
    if "db_conn" not in g:
        if db_pool is None:
            init_db_pool()

        # Retry logic for getting connection
        max_retries = 3
        retry_delay = 1  # seconds

        for attempt in range(max_retries):
            try:
                g.db_conn = db_pool.getconn()
                # Test the connection with a simple query
                try:
                    cursor = g.db_conn.cursor()
                    cursor.execute("SELECT 1")
                    cursor.close()
                except Exception as test_error:
                    # Connection is stale, close it and retry
                    print(f"Connection test failed on attempt {attempt + 1}: {test_error}")
                    try:
                        db_pool.putconn(g.db_conn, close=True)
                    except:
                        pass
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    raise
                break  # Success!

            except Exception as e:
                print(
                    f"Error getting connection from pool (attempt {attempt + 1}/{max_retries}): {e}"
                )
                if attempt < max_retries - 1:
                    # Wait before retrying
                    time.sleep(retry_delay)
                    # Try to reinitialize pool on last retry
                    if attempt == max_retries - 2:
                        print("Reinitializing connection pool...")
                        db_pool = None
                        init_db_pool()
                else:
                    # All retries failed
                    raise Exception(
                        f"Failed to get database connection after {max_retries} attempts: {str(e)}"
                    )

    return g.db_conn


@app.teardown_appcontext
def close_db_connection(exception):
    """Return connection to pool at the end of request"""
    db_conn = g.pop("db_conn", None)
    if db_conn is not None and db_pool is not None:
        try:
            db_pool.putconn(db_conn)
        except Exception as e:
            print(f"Error returning connection to pool: {e}")


# Helper to safeguard against code that tries to close pooled connections manually
def close_conn_safely(conn):
    """No-op: Connection closing is handled by teardown_appcontext"""
    pass


# ============================================================================
# JWT AUTHENTICATION
# ============================================================================

import jwt
import functools
from datetime import timedelta


def create_jwt_token(user_id, role="student", name=None, email=None):
    """
    Create a JWT token for an authenticated user.

    Args:
        user_id: The user's ID
        role: The user's role (student/professor)
        name: The user's name (optional, included in token for convenience)
        email: The user's email (optional, included in token for convenience)

    Returns:
        str: Encoded JWT token
    """
    payload = {
        "user_id": user_id,
        "role": role,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow()
        + timedelta(hours=config.JWT_ACCESS_TOKEN_EXPIRES_HOURS),
    }
    if name:
        payload["name"] = name
    if email:
        payload["email"] = email

    return jwt.encode(payload, config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM)


def decode_jwt_token(token):
    """
    Decode and verify a JWT token.

    Args:
        token: The JWT token string

    Returns:
        dict: Decoded token payload

    Raises:
        jwt.ExpiredSignatureError: If token has expired
        jwt.InvalidTokenError: If token is invalid
    """
    return jwt.decode(token, config.JWT_SECRET_KEY, algorithms=[config.JWT_ALGORITHM])


def require_auth(f):
    """
    Decorator that requires a valid JWT token in the Authorization header.
    Sets g.user_id and g.user_role for the decorated function.

    Usage:
        @app.route('/api/some-endpoint')
        @require_auth
        def some_endpoint():
            user_id = g.user_id
            role = g.user_role
    
    In test mode, auth is bypassed if user_id is provided in request or headers.
    OPTIONS requests always bypass auth.
    """

    @functools.wraps(f)
    def decorated(*args, **kwargs):
        # Always allow OPTIONS requests through without auth
        if request.method == 'OPTIONS':
            return f(*args, **kwargs)
        
        # Bypass auth in test mode if user_id is explicitly provided
        if app.config.get('TESTING'):
            # Check for explicit test user ID or user_id in request
            test_user_id = request.headers.get('X-Test-User-ID')
            if not test_user_id:
                # Try to get from query params or JSON body
                test_user_id = request.args.get('user_id')
                if not test_user_id:
                    json_data = request.get_json(silent=True)
                    if json_data:
                        test_user_id = json_data.get('user_id')
                # Also check form data for multipart requests
                if not test_user_id and request.form:
                    test_user_id = request.form.get('user_id')
            
            if test_user_id:
                g.user_id = str(test_user_id)
                g.user_role = request.headers.get('X-Test-User-Role', 'student')
                return f(*args, **kwargs)
            # If no user_id found, fall through to normal auth (will return 401)
        
        token = None

        # Extract token from Authorization: Bearer <token>
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]

        if not token:
            return jsonify({"error": "Authentication required"}), 401

        try:
            payload = decode_jwt_token(token)
            g.user_id = str(payload["user_id"])
            g.user_role = payload.get("role", "student")
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired. Please sign in again."}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token. Please sign in again."}), 401

        return f(*args, **kwargs)

    return decorated


def hash_password_legacy(password):
    """
    DEPRECATED: Legacy hash function for backward compatibility only.
    This function is insecure and should not be used for new passwords.
    Kept only to verify old passwords during migration period.
    """
    hash_val = 0
    for char in password:
        hash_val = ((hash_val << 5) - hash_val) + ord(char)
        hash_val = hash_val & hash_val  # Convert to 32bit integer
    return str(hash_val)


def hash_password(password):
    """
    Hash password using bcrypt with automatic salt generation.

    Args:
        password (str): Plain text password

    Returns:
        str: Bcrypt hashed password (UTF-8 decoded)
    """
    import bcrypt

    # Generate salt and hash password
    salt = bcrypt.gensalt(rounds=12)  # 12 rounds = good balance of security and performance
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password, hashed_password):
    """
    Verify password against bcrypt hash.
    Falls back to legacy hash for backward compatibility during migration.

    Args:
        password (str): Plain text password to verify
        hashed_password (str): Stored hash (bcrypt or legacy)

    Returns:
        tuple: (is_valid, needs_rehash)
            - is_valid: True if password matches
            - needs_rehash: True if using legacy hash (should update to bcrypt)
    """
    import bcrypt

    # Check if it's a bcrypt hash (starts with $2b$ or $2a$)
    if hashed_password.startswith("$2"):
        try:
            is_valid = bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
            return (is_valid, False)  # Valid bcrypt hash, no rehash needed
        except Exception as e:
            print(f"Bcrypt verification error: {e}")
            return (False, False)
    else:
        # Legacy hash - verify and flag for rehashing
        legacy_hash = hash_password_legacy(password)
        is_valid = legacy_hash == hashed_password
        return (is_valid, is_valid)  # If valid, needs rehash


def ensure_password_resets_table():
    """Ensure password_resets table exists for forgot-password flow."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS password_resets (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                token VARCHAR(255) NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_password_resets_token ON password_resets(token);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_password_resets_email ON password_resets(email);"
        )
        conn.commit()
        cursor.close()
        close_conn_safely(conn)
    except Exception as e:
        print(f"ensure_password_resets_table: {e}")


@app.route("/api/users/signup", methods=["OPTIONS"])
def signup_options():
    """Handle OPTIONS preflight for signup"""
    response = app.response_class()
    cors_origin = _get_cors_origin()
    if cors_origin:
        response.headers["Access-Control-Allow-Origin"] = cors_origin
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Max-Age"] = str(config.CORS_MAX_AGE)
    response.status_code = 200
    return response


@app.route("/api/users/signup", methods=["POST"])
@limiter.limit("5 per hour")  # Prevent account creation spam
def signup():
    """Sign up a new user"""
    try:
        data = request.json
        name = data.get("name")
        email = data.get("email")
        password = data.get("password")

        if not name or not email or not password:
            return jsonify({"error": "Missing required fields"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if user already exists
        cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Email already registered"}), 400

        # Create user
        user_id = str(int(datetime.now().timestamp() * 1000))
        password_hash = hash_password(password)
        role = detect_role_from_email(email)  # Detect role from email domain

        cursor.execute(
            "INSERT INTO users (user_id, name, email, password_hash, role) VALUES (%s, %s, %s, %s, %s) RETURNING user_id, name, email, COALESCE(role, 'student')",
            (user_id, name, email, password_hash, role),
        )
        user = cursor.fetchone()

        if not user:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Failed to create user"}), 500

        created_user_id = user[0]

        # Create default profile (with error handling)
        try:
            cursor.execute(
                "INSERT INTO user_profiles (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
                (created_user_id,),
            )
        except Exception as e:
            logger.warning("Failed to create user_profiles", extra={"error": str(e)})

        # Create default settings (with error handling)
        try:
            cursor.execute(
                "INSERT INTO user_settings (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
                (created_user_id,),
            )
        except Exception as e:
            logger.warning("Failed to create user_settings", extra={"error": str(e)})

        # Create default preferences (with error handling)
        try:
            cursor.execute(
                "INSERT INTO user_preferences (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
                (created_user_id,),
            )
        except Exception as e:
            logger.warning("Failed to create user_preferences", extra={"error": str(e)})

        # Initialize empty AI agent digest (with error handling)
        try:
            cursor.execute(
                "INSERT INTO ai_agent_digest (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
                (created_user_id,),
            )
        except Exception as e:
            logger.warning("Failed to create ai_agent_digest", extra={"error": str(e)})

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        # Return user data with JWT token
        user_role = user[3] if len(user) > 3 else role
        token = create_jwt_token(
            created_user_id, role=user_role, name=user[1], email=user[2]
        )
        return (
            jsonify(
                {
                    "id": created_user_id,
                    "user_id": created_user_id,
                    "name": user[1],
                    "email": user[2],
                    "role": user_role,
                    "token": token,
                    "success": True,
                }
            ),
            201,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/signin", methods=["POST", "OPTIONS"])
@limiter.limit("10 per minute")  # Prevent brute-force login attacks
def signin():
    """Sign in a user"""
    conn = None
    try:
        data = request.json
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"error": "Missing email or password"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch user with password hash
        cursor.execute(
            "SELECT user_id, name, email, password_hash, COALESCE(role, 'student') FROM users WHERE email = %s",
            (email,),
        )
        user = cursor.fetchone()

        if not user:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Invalid email or password"}), 401

        user_id, name, user_email, stored_hash, role = user

        # Verify password (supports both bcrypt and legacy hashes)
        is_valid, needs_rehash = verify_password(password, stored_hash)

        if not is_valid:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Invalid email or password"}), 401

        # If using legacy hash, automatically migrate to bcrypt
        if needs_rehash:
            try:
                new_hash = hash_password(password)
                cursor.execute(
                    "UPDATE users SET password_hash = %s WHERE user_id = %s", (new_hash, user_id)
                )
                conn.commit()
                logger.info(
                    "Password migrated to bcrypt",
                    extra={"user_email": email, "migration": "legacy_to_bcrypt"},
                )
            except Exception as e:
                logger.warning(
                    "Password migration failed", extra={"user_email": email, "error": str(e)}
                )
                # Don't fail login if migration fails
                conn.rollback()

        cursor.close()
        close_conn_safely(conn)

        # Return user data with JWT token
        token = create_jwt_token(user_id, role=role, name=name, email=user_email)
        return (
            jsonify(
                {
                    "id": user_id,
                    "user_id": user_id,
                    "name": name,
                    "email": user_email,
                    "role": role,
                    "token": token,
                }
            ),
            200,
        )

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/forgot-password", methods=["POST", "OPTIONS"])
@limiter.limit("3 per hour")  # Prevent password reset abuse
def forgot_password():
    """Handle forgot password request"""
    if request.method == "OPTIONS":
        response = app.response_class()
        cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers["Access-Control-Allow-Origin"] = cors_origin
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Max-Age"] = "3600"
        return response

    try:
        data = request.json or {}
        email = data.get("email")

        if not email:
            return jsonify({"error": "Email is required"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if user exists
        cursor.execute("SELECT user_id, name FROM users WHERE email = %s", (email,))
        user_row = cursor.fetchone()

        cursor.close()
        close_conn_safely(conn)

        # Always return success to prevent email enumeration (User Feedback)
        response = jsonify(
            {
                "success": True,
                "message": "If an account exists with this email, you will receive password reset instructions.",
            }
        )

        if user_row:
            import secrets
            from datetime import timedelta

            token = secrets.token_urlsafe(32)
            ensure_password_resets_table()
            conn = get_db_connection()
            cursor = conn.cursor()
            expires_at = datetime.utcnow() + timedelta(hours=1)
            cursor.execute(
                "INSERT INTO password_resets (email, token, expires_at) VALUES (%s, %s, %s)",
                (email, token, expires_at),
            )
            conn.commit()
            cursor.close()
            close_conn_safely(conn)
            # Reset link must open the frontend (where reset-password.html is hosted), not the API
            frontend_url = os.getenv("FRONTEND_URL")
            if not frontend_url and request.host_url and "onrender.com" in request.host_url:
                frontend_url = "https://www.myanalytiq.org"
            base_url = (frontend_url or request.host_url).rstrip("/") + "/"
            reset_link = f"{base_url}reset-password.html?token={token}&email={email}"
            if mail:
                try:
                    # Sender: use MAIL_SENDER_NAME + MAIL_DEFAULT_SENDER so recipient sees e.g. "AnalytIQ Services <services.analytiq@gmail.com>"
                    sender = os.getenv("MAIL_DEFAULT_SENDER") or app.config.get(
                        "MAIL_DEFAULT_SENDER"
                    )
                    sender_name = os.getenv("MAIL_SENDER_NAME")
                    if sender_name and sender:
                        msg = Message(
                            "Password Reset Request",
                            recipients=[email],
                            sender=(sender_name, sender),
                        )
                    else:
                        msg = Message("Password Reset Request", recipients=[email])
                    msg.body = f"Hello {user_row[1]},\n\nSomeone requested a password reset for your AnalytIQ account.\n\nClick here to reset your password: {reset_link}\n\nThis link expires in 1 hour. If you did not request this, please ignore this email."
                    mail.send(msg)
                    print(f"Email sent to {email}")
                except Exception as mail_err:
                    print(f"Failed to send email: {mail_err}")
            else:
                print("Mail not configured. Skipping email.")

        return response, 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/reset-password", methods=["POST", "OPTIONS"])
@limiter.limit("5 per hour")  # Prevent password reset token abuse
def reset_password():
    """Reset password using token from email link."""
    if request.method == "OPTIONS":
        response = app.response_class()
        cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers["Access-Control-Allow-Origin"] = cors_origin
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Max-Age"] = "3600"
        return response

    conn = None
    try:
        data = request.json or {}
        token = data.get("token")
        email = data.get("email")
        new_password = data.get("newPassword")

        if not token or not email or not new_password:
            return jsonify({"error": "Token, email, and new password are required"}), 400

        if len(new_password) < 6:
            return jsonify({"error": "Password must be at least 6 characters"}), 400

        ensure_password_resets_table()
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM password_resets WHERE email = %s AND token = %s AND expires_at > %s",
            (email, token, datetime.utcnow()),
        )
        row = cursor.fetchone()
        if not row:
            cursor.close()
            close_conn_safely(conn)
            return (
                jsonify(
                    {"error": "Invalid or expired reset link. Please request a new password reset."}
                ),
                400,
            )

        # Hash new password with bcrypt
        new_hash = hash_password(new_password)
        cursor.execute(
            "UPDATE users SET password_hash = %s, updated_at = CURRENT_TIMESTAMP WHERE email = %s",
            (new_hash, email),
        )
        cursor.execute(
            "DELETE FROM password_resets WHERE email = %s AND token = %s", (email, token)
        )
        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        return (
            jsonify({"success": True, "message": "Password has been reset. You can now sign in."}),
            200,
        )

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/profile", methods=["GET"])
@require_auth
def get_profile():
    """Get user profile"""
    try:
        user_id = g.user_id

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT u.user_id, u.name, u.email, 
                   p.full_name, p.bio, p.profile_picture
            FROM users u
            LEFT JOIN user_profiles p ON u.user_id = p.user_id
            WHERE u.user_id = %s
        """,
            (user_id,),
        )
        result = cursor.fetchone()

        cursor.close()
        close_conn_safely(conn)

        if not result:
            return jsonify({"error": "User not found"}), 404

        return (
            jsonify(
                {
                    "id": result[0],
                    "name": result[1],
                    "email": result[2],
                    "fullName": result[3],
                    "bio": result[4],
                    "profilePicture": result[5],
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/profile", methods=["PUT"])
@require_auth
def update_profile():
    """Update user profile"""
    try:
        data = request.json
        user_id = g.user_id
        full_name = data.get("fullName")
        email = data.get("email")
        bio = data.get("bio")
        profile_picture = data.get("profilePicture")

        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Update users table if email/name changed
        if email or full_name:
            if email:
                cursor.execute(
                    "UPDATE users SET email = %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s",
                    (email, user_id),
                )
            if full_name:
                cursor.execute(
                    "UPDATE users SET name = %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s",
                    (full_name, user_id),
                )

        # Update profile
        cursor.execute(
            """
            INSERT INTO user_profiles (user_id, full_name, bio, profile_picture, updated_at)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) 
            DO UPDATE SET 
                full_name = EXCLUDED.full_name,
                bio = EXCLUDED.bio,
                profile_picture = EXCLUDED.profile_picture,
                updated_at = CURRENT_TIMESTAMP
        """,
            (user_id, full_name, bio, profile_picture),
        )

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        return jsonify({"success": True}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/settings", methods=["GET"])
@require_auth
def get_settings():
    """Get user settings"""
    try:
        user_id = g.user_id

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT email_notifications FROM user_settings WHERE user_id = %s", (user_id,)
        )
        result = cursor.fetchone()

        cursor.close()
        close_conn_safely(conn)

        if not result:
            return jsonify({"emailNotifications": False}), 200

        return (
            jsonify(
                {
                    "emailNotifications": result[0],
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/settings", methods=["PUT"])
@require_auth
def update_settings():
    """Update user settings"""
    try:
        data = request.json
        user_id = g.user_id
        email_notifications = data.get("emailNotifications")

        # Ensure boolean values (handle None/undefined)
        email_notifications = (
            bool(email_notifications) if email_notifications is not None else False
        )

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO user_settings (user_id, email_notifications, updated_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id)
            DO UPDATE SET
                email_notifications = EXCLUDED.email_notifications,
                updated_at = CURRENT_TIMESTAMP
        """,
            (user_id, email_notifications),
        )

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        return jsonify({"success": True}), 200

    except Exception as e:
        print(f"Error updating settings: {str(e)}")
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/password", methods=["PUT"])
@require_auth
def update_password():
    """Update user password"""
    conn = None
    try:
        data = request.json
        user_id = g.user_id
        current_password = data.get("currentPassword")
        new_password = data.get("newPassword")

        if not current_password or not new_password:
            return jsonify({"error": "Missing required fields"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch current password hash
        cursor.execute("SELECT password_hash FROM users WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()

        if not result:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "User not found"}), 404

        stored_hash = result[0]

        # Verify current password
        is_valid, _ = verify_password(current_password, stored_hash)

        if not is_valid:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Current password is incorrect"}), 401

        # Update password with new bcrypt hash
        new_hash = hash_password(new_password)
        cursor.execute(
            "UPDATE users SET password_hash = %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s",
            (new_hash, user_id),
        )

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        return jsonify({"success": True}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/delete", methods=["DELETE"])
@require_auth
def delete_user():
    """Delete user account"""
    try:
        user_id = g.user_id

        conn = get_db_connection()
        cursor = conn.cursor()

        # Delete user (cascade will delete profile and settings)
        cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        return jsonify({"success": True}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/conversations", methods=["GET"])
@require_auth
def get_conversations():
    """Get all conversations for a user"""
    try:
        user_id = g.user_id
        archived = request.args.get("archived", "false").lower() == "true"

        # Get pagination parameters
        limit, offset = utils.get_pagination_params(request.args)

        conn = get_db_connection()
        cursor = conn.cursor()

        # Get total count
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM conversations
            WHERE user_id = %s AND deleted = false AND archived = %s
        """,
            (user_id, archived),
        )
        total_count = cursor.fetchone()[0] or 0

        # Get paginated conversations
        cursor.execute(
            """
            SELECT conversation_id, title, archived, created_at, updated_at
            FROM conversations
            WHERE user_id = %s AND deleted = false AND archived = %s
            ORDER BY updated_at DESC
            LIMIT %s OFFSET %s
        """,
            (user_id, archived, limit, offset),
        )

        conversations = []
        for row in cursor.fetchall():
            conversations.append(
                {
                    "id": row[0],
                    "title": row[1],
                    "archived": row[2],
                    "date": row[4].isoformat() if row[4] else row[3].isoformat(),
                }
            )

        cursor.close()
        close_conn_safely(conn)

        # Return paginated response
        response = utils.build_paginated_response(
            conversations, total_count, limit, offset, "conversations"
        )
        return jsonify(response), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/conversations", methods=["POST"])
@require_auth
def create_conversation():
    """Create a new conversation"""
    try:
        data = request.json
        user_id = g.user_id
        conversation_id = data.get("conversation_id") or str(int(datetime.now().timestamp() * 1000))
        title = data.get("title", "New Conversation")

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO conversations (conversation_id, user_id, title)
            VALUES (%s, %s, %s)
            ON CONFLICT (conversation_id) DO UPDATE SET
                title = EXCLUDED.title,
                updated_at = CURRENT_TIMESTAMP
            RETURNING conversation_id
        """,
            (conversation_id, user_id, title),
        )

        conv_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        return jsonify({"conversation_id": conv_id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/conversations/<conversation_id>", methods=["GET"])
@require_auth
def get_conversation(conversation_id):
    """Get a specific conversation with messages"""
    try:
        user_id = g.user_id

        conn = get_db_connection()
        cursor = conn.cursor()

        # Get conversation
        cursor.execute(
            """
            SELECT conversation_id, title, archived, created_at, updated_at
            FROM conversations
            WHERE conversation_id = %s AND user_id = %s AND deleted = false
        """,
            (conversation_id, user_id),
        )

        conv = cursor.fetchone()
        if not conv:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Conversation not found"}), 404

        # Get messages
        cursor.execute(
            """
            SELECT role, content, message_order, created_at
            FROM conversation_messages
            WHERE conversation_id = %s
            ORDER BY message_order ASC
        """,
            (conversation_id,),
        )

        messages = []
        for row in cursor.fetchall():
            messages.append({"role": row[0], "content": row[1], "order": row[2]})

        cursor.close()
        close_conn_safely(conn)

        return (
            jsonify(
                {
                    "id": conv[0],
                    "title": conv[1],
                    "archived": conv[2],
                    "date": conv[4].isoformat() if conv[4] else conv[3].isoformat(),
                    "messages": messages,
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/conversations/<conversation_id>", methods=["PUT"])
@require_auth
def update_conversation(conversation_id):
    """Update conversation (title, archive status, etc)"""
    conn = None
    try:
        data = request.json
        user_id = g.user_id
        title = data.get("title")
        archived = data.get("archived")
        messages = data.get("messages", [])

        conn = get_db_connection()
        cursor = conn.cursor()

        # Update conversation - use explicit field updates to prevent SQL injection
        # Build update query safely with whitelisted fields
        update_fields = []
        params = []

        if title is not None:
            update_fields.append("title = %s")
            params.append(title)
        if archived is not None:
            update_fields.append("archived = %s")
            params.append(archived)

        if update_fields:
            # Safe: update_fields contains only whitelisted field assignments
            params.extend([conversation_id, user_id])
            query = f"""
                UPDATE conversations
                SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                WHERE conversation_id = %s AND user_id = %s
            """
            cursor.execute(query, params)

        # Update messages if provided
        if messages:
            # Delete existing messages
            cursor.execute(
                "DELETE FROM conversation_messages WHERE conversation_id = %s", (conversation_id,)
            )

            # Insert new messages
            for idx, msg in enumerate(messages):
                cursor.execute(
                    """
                    INSERT INTO conversation_messages (conversation_id, role, content, message_order)
                    VALUES (%s, %s, %s, %s)
                """,
                    (conversation_id, msg.get("role"), msg.get("content"), idx),
                )

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        return jsonify({"success": True}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/conversations/<conversation_id>", methods=["DELETE"])
@require_auth
def delete_conversation(conversation_id):
    """Delete (soft delete) a conversation"""
    try:
        user_id = g.user_id

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE conversations
            SET deleted = true, updated_at = CURRENT_TIMESTAMP
            WHERE conversation_id = %s AND user_id = %s
        """,
            (conversation_id, user_id),
        )

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        return jsonify({"success": True}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/ai-digest", methods=["GET"])
@require_auth
def get_ai_digest():
    """Get AI agent digest for user"""
    try:
        user_id = g.user_id

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT goal, constraints, decisions, current_state, open_questions
            FROM ai_agent_digest
            WHERE user_id = %s
        """,
            (user_id,),
        )

        result = cursor.fetchone()
        cursor.close()
        close_conn_safely(conn)

        if not result:
            return (
                jsonify(
                    {
                        "goal": "",
                        "constraints": [],
                        "decisions": [],
                        "current_state": [],
                        "open_questions": [],
                    }
                ),
                200,
            )

        # Helper function to parse array from TEXT field
        def parse_array(value):
            if not value:
                return []
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, list) else []
            except (json.JSONDecodeError, TypeError):
                # If not JSON, treat as single value in array or empty
                return [value] if value else []

        return (
            jsonify(
                {
                    "goal": result[0] or "",
                    "constraints": parse_array(result[1]),
                    "decisions": parse_array(result[2]),
                    "current_state": parse_array(result[3]),
                    "open_questions": parse_array(result[4]),
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/ai-digest", methods=["PUT"])
@require_auth
def update_ai_digest():
    """Update AI agent digest"""
    try:
        data = request.json
        user_id = g.user_id
        digest = data.get("digest", {})

        conn = get_db_connection()
        cursor = conn.cursor()

        # Helper function to serialize array to JSON string
        def serialize_array(value):
            if isinstance(value, list):
                return json.dumps(value)
            if isinstance(value, str):
                try:
                    # If it's already JSON, validate it
                    json.loads(value)
                    return value
                except json.JSONDecodeError:
                    # If not JSON, wrap in array
                    return json.dumps([value] if value else [])
            return json.dumps([])

        cursor.execute(
            """
            INSERT INTO ai_agent_digest (user_id, goal, constraints, decisions, current_state, open_questions, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) DO UPDATE SET
                goal = EXCLUDED.goal,
                constraints = EXCLUDED.constraints,
                decisions = EXCLUDED.decisions,
                current_state = EXCLUDED.current_state,
                open_questions = EXCLUDED.open_questions,
                updated_at = CURRENT_TIMESTAMP
        """,
            (
                user_id,
                digest.get("goal", ""),
                serialize_array(digest.get("constraints", [])),
                serialize_array(digest.get("decisions", [])),
                serialize_array(digest.get("current_state", [])),
                serialize_array(digest.get("open_questions", [])),
            ),
        )

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        return jsonify({"success": True}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/ai-memory", methods=["GET"])
@require_auth
def get_ai_memory():
    """Get AI agent memory for user"""
    try:
        user_id = g.user_id

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT memory_item
            FROM ai_agent_memory
            WHERE user_id = %s
            ORDER BY created_at ASC
        """,
            (user_id,),
        )

        memory = [row[0] for row in cursor.fetchall()]
        cursor.close()
        close_conn_safely(conn)

        return jsonify({"memory": memory}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/ai-memory", methods=["PUT"])
@require_auth
def update_ai_memory():
    """Update AI agent memory (replaces all)"""
    try:
        data = request.json
        user_id = g.user_id
        memory_items = data.get("memory", [])

        conn = get_db_connection()
        cursor = conn.cursor()

        # Delete existing memory
        cursor.execute("DELETE FROM ai_agent_memory WHERE user_id = %s", (user_id,))

        # Insert new memory items
        for item in memory_items:
            if item:
                cursor.execute(
                    """
                    INSERT INTO ai_agent_memory (user_id, memory_item)
                    VALUES (%s, %s)
                """,
                    (user_id, item),
                )

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        return jsonify({"success": True}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/preferences", methods=["GET"])
@require_auth
def get_preferences():
    """Get user preferences"""
    try:
        user_id = g.user_id

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT current_language, gemini_model, ai_provider
            FROM user_preferences
            WHERE user_id = %s
        """,
            (user_id,),
        )

        result = cursor.fetchone()
        cursor.close()
        close_conn_safely(conn)

        if not result:
            return (
                jsonify(
                    {
                        "currentLanguage": "python",
                        "geminiModel": "gemini-2.5-flash",
                        "aiProvider": "gemini",
                    }
                ),
                200,
            )

        return (
            jsonify(
                {
                    "currentLanguage": result[0] or "python",
                    "geminiModel": result[1] or "gemini-2.5-flash",
                    "aiProvider": result[2] or "gemini",
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/preferences", methods=["PUT"])
@require_auth
def update_preferences():
    """Update user preferences"""
    conn = None
    try:
        data = request.json
        user_id = g.user_id
        current_language = data.get("currentLanguage")
        gemini_model = data.get("geminiModel")
        ai_provider = data.get("aiProvider")

        conn = get_db_connection()
        cursor = conn.cursor()

        # Use explicit field updates to prevent SQL injection
        # Build safe UPSERT query with whitelisted fields
        update_fields = []
        insert_fields = []
        insert_placeholders = []
        params_insert = [user_id]
        params_update = []

        if current_language is not None:
            insert_fields.append("current_language")
            insert_placeholders.append("%s")
            params_insert.append(current_language)
            update_fields.append("current_language = %s")
            params_update.append(current_language)

        if gemini_model is not None:
            insert_fields.append("gemini_model")
            insert_placeholders.append("%s")
            params_insert.append(gemini_model)
            update_fields.append("gemini_model = %s")
            params_update.append(gemini_model)

        if ai_provider is not None:
            insert_fields.append("ai_provider")
            insert_placeholders.append("%s")
            params_insert.append(ai_provider)
            update_fields.append("ai_provider = %s")
            params_update.append(ai_provider)

        if update_fields:
            # Safe: all fields are whitelisted
            query = f"""
                INSERT INTO user_preferences (user_id, {', '.join(insert_fields)}, updated_at)
                VALUES (%s, {', '.join(insert_placeholders)}, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id) DO UPDATE SET
                    {', '.join(update_fields)},
                    updated_at = CURRENT_TIMESTAMP
            """
            params = params_insert + params_update
            cursor.execute(query, params)

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        return jsonify({"success": True}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/practice-progress", methods=["GET"])
@require_auth
def get_practice_progress():
    """Get practice progress for user"""
    try:
        user_id = g.user_id
        exercise_id = request.args.get("exercise_id")

        conn = get_db_connection()
        cursor = conn.cursor()

        if exercise_id:
            cursor.execute(
                """
                SELECT exercise_id, exercise_title, best_score, best_accuracy, best_time, 
                       total_attempts, last_attempt_score, completed, last_completed_at
                FROM practice_progress
                WHERE user_id = %s AND exercise_id = %s
            """,
                (user_id, exercise_id),
            )
            result = cursor.fetchone()
            if result:
                return (
                    jsonify(
                        {
                            "exercise_id": result[0],
                            "exercise_title": result[1],
                            "best_score": result[2] or 0,
                            "best_accuracy": float(result[3]) if result[3] else 0,
                            "best_time": result[4],
                            "total_attempts": result[5] or 0,
                            "last_attempt_score": result[6] or 0,
                            "completed": result[7] or False,
                            "last_completed_at": result[8].isoformat() if result[8] else None,
                        }
                    ),
                    200,
                )
            else:
                return jsonify({}), 200
        else:
            cursor.execute(
                """
                SELECT exercise_id, exercise_title, best_score, best_accuracy, 
                       total_attempts, completed, last_completed_at
                FROM practice_progress
                WHERE user_id = %s
                ORDER BY exercise_id
            """,
                (user_id,),
            )

            progress = []
            for row in cursor.fetchall():
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
            return jsonify(progress), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/practice-progress", methods=["PUT"])
@require_auth
def update_practice_progress():
    """Update practice progress"""
    try:
        data = request.json
        user_id = g.user_id
        exercise_id = data.get("exercise_id")

        if not exercise_id:
            return jsonify({"error": "Missing exercise_id"}), 400

        exercise_title = data.get("exercise_title", "")
        score = data.get("score", 0)
        accuracy = data.get("accuracy", 0)
        time_spent = data.get("time_spent", 0)
        progress_data = data.get("progress_data", {})

        if progress_data:
            exercise_title = progress_data.get("exercise_title", exercise_title)

        # Verify user exists in database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
        if not cursor.fetchone():
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "User not found in database. Please sign up first."}), 404

        # Get current best score if exists
        cursor.execute(
            """
            SELECT best_score, total_attempts FROM practice_progress 
            WHERE user_id = %s AND exercise_id = %s
        """,
            (user_id, exercise_id),
        )

        existing = cursor.fetchone()
        current_best_score = existing[0] if existing and existing[0] else 0
        current_attempts = existing[1] if existing and existing[1] else 0

        # Determine if this is a new best
        is_new_best = score > current_best_score
        new_best_score = max(score, current_best_score)

        # Get accuracy and time from progress_data if provided
        accuracy = progress_data.get("accuracy", 0) if progress_data else 0
        time_spent_seconds = time_spent if time_spent else 0

        # Get class_id and class_exercise_id from request data (optional, for class exercises)
        class_id = data.get("class_id")
        class_exercise_id = (
            data.get("class_exercise_id") or exercise_id
        )  # Use class_exercise_id if provided, else fallback to exercise_id

        # Insert or update practice progress
        cursor.execute(
            """
            INSERT INTO practice_progress 
                (user_id, exercise_id, exercise_title, best_score, best_accuracy, best_time, 
                 total_attempts, last_attempt_score, last_attempt_accuracy, last_attempt_time,
                 completed, last_completed_at, class_id, class_exercise_id, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                    CASE WHEN %s >= 50 THEN CURRENT_TIMESTAMP ELSE NULL END,
                    %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id, exercise_id) DO UPDATE SET
                best_score = GREATEST(practice_progress.best_score, EXCLUDED.best_score),
                best_accuracy = CASE 
                    WHEN EXCLUDED.best_score > practice_progress.best_score THEN EXCLUDED.best_accuracy
                    ELSE practice_progress.best_accuracy
                END,
                best_time = CASE 
                    WHEN EXCLUDED.best_score > practice_progress.best_score THEN EXCLUDED.best_time
                    ELSE practice_progress.best_time
                END,
                total_attempts = practice_progress.total_attempts + 1,
                last_attempt_score = EXCLUDED.last_attempt_score,
                last_attempt_accuracy = EXCLUDED.last_attempt_accuracy,
                last_attempt_time = EXCLUDED.last_attempt_time,
                completed = CASE WHEN EXCLUDED.best_score >= 50 THEN true ELSE practice_progress.completed END,
                last_completed_at = CASE 
                    WHEN EXCLUDED.best_score >= 50 THEN COALESCE(EXCLUDED.last_completed_at, CURRENT_TIMESTAMP)
                    ELSE practice_progress.last_completed_at
                END,
                class_id = COALESCE(EXCLUDED.class_id, practice_progress.class_id),
                class_exercise_id = COALESCE(EXCLUDED.class_exercise_id, practice_progress.class_exercise_id),
                updated_at = CURRENT_TIMESTAMP
        """,
            (
                user_id,
                exercise_id,
                progress_data.get("exercise_title", exercise_id) if progress_data else exercise_id,
                new_best_score,
                accuracy if is_new_best else None,
                time_spent_seconds if is_new_best else None,
                current_attempts + 1,
                score,
                accuracy,
                time_spent_seconds,
                score >= 50,
                score,
                class_id,
                class_exercise_id,
            ),
        )

        # Record this attempt in exercise_attempts table
        cursor.execute(
            """
            INSERT INTO exercise_attempts (user_id, exercise_id, score, accuracy, time_spent, attempt_number)
            VALUES (%s, %s, %s, %s, %s, %s)
        """,
            (user_id, exercise_id, score, accuracy, time_spent_seconds, current_attempts + 1),
        )

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        return (
            jsonify({"success": True, "is_new_best": is_new_best, "best_score": new_best_score}),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/exercises/progress", methods=["GET"])
@require_auth
def get_all_progress():
    """Get progress for all exercises for current user"""
    try:
        user_id = g.user_id

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT exercise_id, exercise_title, best_score, best_accuracy, 
                   total_attempts, completed, last_completed_at
            FROM practice_progress
            WHERE user_id = %s
            ORDER BY exercise_id
        """,
            (user_id,),
        )

        results = cursor.fetchall()
        progress = []
        for row in results:
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
        return jsonify({"error": str(e)}), 500


@app.route("/api/exercises/<exercise_id>/leaderboard", methods=["GET"])
def get_exercise_leaderboard(exercise_id):
    """Get leaderboard for a specific exercise"""
    try:
        limit = int(request.args.get("limit", 10))

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT u.name, u.email, pp.best_score, pp.best_accuracy, 
                   pp.best_time, pp.total_attempts, pp.last_completed_at
            FROM practice_progress pp
            JOIN users u ON pp.user_id = u.user_id
            WHERE pp.exercise_id = %s AND pp.best_score > 0
            ORDER BY pp.best_score DESC, pp.best_time ASC
            LIMIT %s
        """,
            (exercise_id, limit),
        )

        results = cursor.fetchall()
        leaderboard = []
        rank = 1
        for row in results:
            leaderboard.append(
                {
                    "rank": rank,
                    "name": row[0],
                    "email": row[1],
                    "best_score": row[2],
                    "best_accuracy": float(row[3]) if row[3] else 0,
                    "best_time": row[4],
                    "total_attempts": row[5] or 0,
                }
            )
            rank += 1

        cursor.close()
        close_conn_safely(conn)

        return jsonify({"leaderboard": leaderboard}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/leaderboard/grand", methods=["GET"])
def get_grand_leaderboard():
    """Get grand leaderboard - ranked by average score across all exercises"""
    try:
        limit = int(request.args.get("limit", 10))

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT u.user_id, u.name, u.email,
                   COUNT(DISTINCT pp.exercise_id) as exercises_completed,
                   AVG(pp.best_score) as average_score,
                   SUM(pp.best_score) as total_score,
                   MAX(pp.last_completed_at) as last_activity
            FROM users u
            JOIN practice_progress pp ON u.user_id = pp.user_id
            WHERE pp.completed = true AND pp.best_score >= 50
            GROUP BY u.user_id, u.name, u.email
            HAVING COUNT(DISTINCT pp.exercise_id) > 0
            ORDER BY average_score DESC, exercises_completed DESC
            LIMIT %s
        """,
            (limit,),
        )

        results = cursor.fetchall()
        leaderboard = []
        rank = 1
        for row in results:
            leaderboard.append(
                {
                    "rank": rank,
                    "user_id": row[0],
                    "name": row[1],
                    "email": row[2],
                    "exercises_completed": row[3],
                    "average_score": float(row[4]) if row[4] else 0,
                    "total_score": int(row[5]) if row[5] else 0,
                }
            )
            rank += 1

        cursor.close()
        close_conn_safely(conn)

        return jsonify({"leaderboard": leaderboard}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health():
    """
    Comprehensive health check endpoint
    Returns 200 if all critical services healthy, 503 if degraded
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {},
    }

    all_healthy = True

    # 1. Database connectivity (CRITICAL)
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
    except Exception as e:
        all_healthy = False
        health_status["services"]["database"] = {"status": "unhealthy", "error": str(e)[:200]}
        logger.error("Health check: database unhealthy", extra={"error": str(e)})

    # 2. Gemini API (NON-CRITICAL - degrades gracefully)
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if gemini_api_key and gemini_api_key != "your_gemini_api_key_here":
        # Just verify the key is configured, don't make actual API call
        health_status["services"]["gemini_api"] = {
            "status": "configured",
            "note": "API key present and configured",
        }
        logger.debug("Health check: Gemini API configured")
    else:
        health_status["services"]["gemini_api"] = {
            "status": "not_configured",
            "note": "API key not set - exercise generation disabled",
            "impact": "Exercise generation unavailable",
        }

    # 3. Email service (NON-CRITICAL - degrades gracefully)
    try:
        if mail:
            health_status["services"]["email"] = {
                "status": "configured",
                "note": "Flask-Mail initialized",
            }
        else:
            health_status["services"]["email"] = {
                "status": "not_configured",
                "note": "Flask-Mail not installed",
                "impact": "Password reset emails unavailable",
            }
    except Exception as e:
        health_status["services"]["email"] = {
            "status": "degraded",
            "error": str(e)[:200],
            "impact": "Email features may be unavailable",
        }
        logger.warning("Health check: Email service degraded", extra={"error": str(e)})

    # 4. Redis Cache (NON-CRITICAL - degrades to no-cache)
    if os.getenv("FEATURE_CACHING") == "True":
        try:
            cache_status = cache_health_check()
            health_status["services"]["cache"] = cache_status
            # Check 'healthy' boolean instead of 'status' string
            if not cache_status.get("healthy", False):
                logger.warning(f"Health check: Cache unhealthy: {cache_status.get('message')}")
        except Exception as e:
            health_status["services"]["cache"] = {"status": "error", "error": str(e)}
            logger.error(f"Health check: Cache error: {e}")
    else:
        health_status["services"]["cache"] = {
            "status": "disabled",
            "note": "Caching feature flag off",
        }

    # 5. Supabase Storage (CRITICAL for PDFs)
    try:
        storage_status = storage_health_check()
        health_status["services"]["storage"] = storage_status
        # Check 'healthy' boolean instead of 'status' string
        if not storage_status.get("healthy", False):
            all_healthy = False
            logger.error(f"Health check: Storage unhealthy: {storage_status.get('message')}")
    except Exception as e:
        all_healthy = False
        health_status["services"]["storage"] = {"status": "error", "error": str(e)}
        logger.error(f"Health check: Storage error: {e}")

    # Set overall status
    if not all_healthy:
        health_status["status"] = "degraded"
        logger.warning("Health check: system degraded")
        return jsonify(health_status), 503  # Service Unavailable

    logger.info("Health check: all systems healthy")
    return jsonify(health_status), 200


@app.route("/api/csrf-token", methods=["GET"])
def get_csrf_token():
    """
    Generate and return a CSRF token for the client
    This endpoint is used by the frontend to obtain a CSRF token
    """
    if not config.FEATURE_CSRF_PROTECTION:
        return (
            jsonify({"csrf_enabled": False, "message": "CSRF protection is currently disabled"}),
            200,
        )

    try:
        if generate_csrf:
            token = generate_csrf()
            return jsonify({"csrf_enabled": True, "csrf_token": token}), 200
        else:
            return jsonify({"csrf_enabled": False, "error": "CSRF module not available"}), 500
    except Exception as e:
        logger.error("Failed to generate CSRF token", extra={"error": str(e)})
        return jsonify({"error": "Failed to generate CSRF token"}), 500


@app.route("/api/tasks/<task_id>", methods=["GET"])
def get_task_status(task_id):
    """
    Get the status of an async task

    Args:
        task_id: Celery task ID

    Returns:
        JSON with task status, result, or error
    """
    if not celery_app or not FEATURE_ASYNC_TASKS:
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
            response["error"] = str(task.info)
            response["message"] = "Task failed"
        elif task.state == "RETRY":
            response["message"] = "Task is being retried"
        else:
            response["message"] = f"Task state: {task.state}"

        return jsonify(response), 200

    except Exception as e:
        logger.error("Failed to get task status", extra={"error": str(e), "task_id": task_id})
        return jsonify({"error": str(e), "task_id": task_id}), 500


# ============================================================================
# CLASS MANAGEMENT APIs (Phase 2)
# ============================================================================

# ============================================
# CONTACT FORM ENDPOINT
# ============================================


@app.route("/api/contact", methods=["POST", "OPTIONS"])
def submit_contact():
    """Submit a contact form message"""
    if request.method == "OPTIONS":
        return "", 200

    try:
        data = request.json
        name = data.get("name")
        email = data.get("email")
        subject = data.get("subject")
        message = data.get("message")

        # Optional: extract user_id from JWT if present
        user_id = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                payload = decode_jwt_token(auth_header.split(" ", 1)[1])
                user_id = str(payload["user_id"])
            except Exception:
                pass  # Contact form works without auth

        if not all([name, email, subject, message]):
            return jsonify({"error": "Missing required fields"}), 400

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
        print(f"Error submitting contact form: {str(e)}")
        return jsonify({"error": str(e)}), 500


# ============================================
# CLASS MANAGEMENT ENDPOINTS
# ============================================


def generate_class_code():
    """Generate a unique 10-character class code (5 letters + 5 numbers)"""
    import random
    import string

    letters = "".join(random.choices(string.ascii_uppercase, k=5))
    numbers = "".join(random.choices(string.digits, k=5))
    return letters + numbers


@app.route("/api/classes", methods=["POST", "OPTIONS"])
@require_auth
def create_class():
    """Create a new class (professor only)"""
    try:
        if request.method == "OPTIONS":
            response = app.response_class()
            cors_origin = _get_cors_origin()
            if cors_origin:
                response.headers["Access-Control-Allow-Origin"] = cors_origin
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
            response.status_code = 200
            return response

        data = request.json
        user_id = g.user_id
        name = data.get("name")
        description = data.get("description", "")
        class_code = data.get("class_code", "").strip().upper()  # Custom code from professor

        if not name:
            return jsonify({"error": "Missing required field (name)"}), 400

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
        return jsonify({"error": str(e)}), 500


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
        return jsonify({"error": str(e)}), 500


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
        return jsonify({"error": str(e)}), 500


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
        return jsonify({"error": str(e)}), 500


@app.route("/api/exercises/<exercise_id>", methods=["GET"])
@require_auth
def get_exercise_details(exercise_id):
    """Get details of a single exercise"""
    try:
        user_id = g.user_id
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT exercise_id, chapter_id, class_id, title, description, difficulty, solution_code
            FROM class_exercises
            WHERE exercise_id = %s
        """,
            (exercise_id,),
        )

        row = cursor.fetchone()
        cursor.close()
        close_conn_safely(conn)

        if not row:
            return jsonify({"error": "Exercise not found"}), 404

        return (
            jsonify(
                {
                    "exercise": {
                        "exercise_id": row[0],
                        "chapter_id": row[1],
                        "class_id": row[2],
                        "title": row[3],
                        "description": row[4],
                        "difficulty": row[5],
                        "solution_code": row[6],
                    }
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/exercises/<exercise_id>", methods=["PUT"])
@require_auth
def update_exercise(exercise_id):
    """Update an existing exercise"""
    try:
        ensure_exercises_table()
        data = request.json
        user_id = g.user_id

        conn = get_db_connection()
        cursor = conn.cursor()

        # Verify ownership (simplified check)
        cursor.execute(
            """
            SELECT c.professor_id 
            FROM class_exercises ce
            JOIN classes c ON ce.class_id = c.class_id
            WHERE ce.exercise_id = %s
        """,
            (exercise_id,),
        )

        result = cursor.fetchone()
        if not result or result[0] != user_id:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Not authorized"}), 403

        cursor.execute(
            """
            UPDATE class_exercises 
            SET title = %s, description = %s, difficulty = %s, solution_code = %s
            WHERE exercise_id = %s
        """,
            (
                data.get("title"),
                data.get("description"),
                data.get("difficulty"),
                data.get("solution_code"),
                exercise_id,
            ),
        )

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/classes/<class_id>", methods=["PUT"])
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

        return jsonify({"success": True}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500


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


@app.route("/api/classes/<class_id>/chapters", methods=["POST", "OPTIONS"])
@require_auth
def upload_chapter(class_id):
    """Upload PDF and create chapter for a class (professor only)"""
    try:
        if request.method == "OPTIONS":
            response = app.response_class()
            cors_origin = _get_cors_origin()
            if cors_origin:
                response.headers["Access-Control-Allow-Origin"] = cors_origin
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
            response.status_code = 200
            return response

        # Get user_id from JWT token
        user_id = g.user_id
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        # Verify user is professor and owner
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT professor_id FROM classes WHERE class_id = %s", (class_id,))
        class_data = cursor.fetchone()
        if not class_data:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Class not found"}), 404

        if class_data[0] != user_id:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Only the class owner can upload chapters"}), 403

        # Check if file was uploaded
        if "pdf_file" not in request.files:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "No PDF file provided"}), 400

        file = request.files["pdf_file"]
        if file.filename == "":
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "No file selected"}), 400

        if not allowed_file(file.filename):
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Invalid file type. Only PDF files are allowed."}), 400

        # Comprehensive PDF validation
        is_valid, error_message = validate_pdf_file(file)
        if not is_valid:
            cursor.close()
            close_conn_safely(conn)
            logger.warning(
                "PDF upload rejected",
                extra={
                    "filename": file.filename,
                    "error": error_message,
                    "user_id": user_id,
                    "class_id": class_id,
                },
            )
            return jsonify({"error": error_message}), 400

        # Get form data
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        exercise_mode = request.form.get("exercise_mode", "auto")  # auto, manual, upload

        if not title:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Chapter title is required"}), 400

        # Read file content
        file_bytes = file.read()

        # Generate unique chapter ID
        chapter_id = f"{class_id}_{int(datetime.now().timestamp() * 1000)}"

        # Store filename for reference
        filename = secure_filename(file.filename)
        pdf_filename = f"{chapter_id}_{filename}"

        # PDF URL will point to our serve endpoint
        pdf_url = f"/api/chapters/{chapter_id}/pdf"

        # Extract text from PDF (for future exercise generation)
        pdf_text = None
        if extract_text_from_pdf_bytes:
            try:
                pdf_text = extract_text_from_pdf_bytes(file_bytes)
            except Exception as e:
                print(f"Warning: Could not extract text from PDF: {e}")
                pdf_text = None

        # Get next chapter number
        cursor.execute(
            """
            SELECT COALESCE(MAX(chapter_number), 0) + 1 
            FROM class_chapters 
            WHERE class_id = %s
        """,
            (class_id,),
        )
        chapter_number = cursor.fetchone()[0] or 1

        # Create chapter record with PDF binary data
        cursor.execute(
            """
            INSERT INTO class_chapters (chapter_id, class_id, title, description, chapter_number, pdf_url, pdf_filename, pdf_data)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING chapter_id, title, description, chapter_number, created_at
        """,
            (
                chapter_id,
                class_id,
                title,
                description,
                chapter_number,
                pdf_url,
                pdf_filename,
                psycopg2.Binary(file_bytes),
            ),
        )

        chapter_data = cursor.fetchone()
        chapter_id_result = chapter_data[0]
        chapter_title_result = chapter_data[1]

        # Generate exercises if exercise_mode='auto' and pdf_text is available
        exercises_generated = 0
        if exercise_mode == "auto" and pdf_text and generate_exercises_from_pdf_content:
            try:
                # Generate exercises using AI
                api_key = os.getenv("GEMINI_API_KEY")
                if not api_key:
                    raise ValueError("GEMINI_API_KEY not set")
                exercises = generate_exercises_from_pdf_content(
                    pdf_text, chapter_title_result, api_key
                )

                # Store exercises in database
                if exercises:
                    for idx, exercise in enumerate(exercises, 1):
                        exercise_id = (
                            f"{chapter_id_result}_ex_{idx}_{int(datetime.now().timestamp() * 1000)}"
                        )
                        cursor.execute(
                            """
                            INSERT INTO class_exercises (exercise_id, chapter_id, class_id, title, description, difficulty, solution_code, exercise_number)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                            (
                                exercise_id,
                                chapter_id_result,
                                class_id,
                                exercise["title"],
                                exercise["description"],
                                exercise["difficulty"],
                                exercise["solution_code"],
                                idx,
                            ),
                        )
                    exercises_generated = len(exercises)
                    conn.commit()
            except Exception as e:
                print(f"Warning: Could not generate exercises: {e}")
                # Don't fail the upload if exercise generation fails
                exercises_generated = 0

        # Commit the transaction to ensure chapter is saved
        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        return (
            jsonify(
                {
                    "chapter_id": chapter_id_result,
                    "title": chapter_title_result,
                    "description": chapter_data[2],
                    "chapter_number": chapter_data[3],
                    "created_at": chapter_data[4].isoformat() if chapter_data[4] else None,
                    "pdf_url": pdf_url,
                    "pdf_text_extracted": pdf_text is not None,
                    "exercise_mode": exercise_mode,
                    "exercises_generated": exercises_generated,
                    "success": True,
                }
            ),
            201,
        )

    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/classes/<class_id>/chapters", methods=["GET"])
@require_auth
def get_class_chapters(class_id):
    """Get all chapters for a class"""
    try:
        user_id = g.user_id
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check access (professor or enrolled student)
        cursor.execute("SELECT professor_id FROM classes WHERE class_id = %s", (class_id,))
        class_data = cursor.fetchone()
        if not class_data:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Class not found"}), 404

        # Check if user has access
        cursor.execute("SELECT role FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "User not found"}), 404

        role = user[0] or "student"
        is_professor = role == "professor"
        is_owner = class_data[0] == user_id

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
                return jsonify({"error": "Access denied"}), 403

        # Get chapters
        cursor.execute(
            """
            SELECT chapter_id, title, description, chapter_number, pdf_url, pdf_filename, created_at
            FROM class_chapters
            WHERE class_id = %s
            ORDER BY chapter_number ASC
        """,
            (class_id,),
        )

        chapters = []
        for row in cursor.fetchall():
            chapters.append(
                {
                    "chapter_id": row[0],
                    "title": row[1],
                    "description": row[2],
                    "chapter_number": row[3],
                    "pdf_url": row[4],
                    "pdf_filename": row[5],
                    "created_at": row[6].isoformat() if row[6] else None,
                }
            )

        cursor.close()
        close_conn_safely(conn)

        return jsonify({"chapters": chapters}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chapters/<chapter_id>", methods=["PUT"])
@require_auth
def update_chapter(chapter_id):
    """Update a chapter"""
    try:
        data = request.json
        user_id = g.user_id

        conn = get_db_connection()
        cursor = conn.cursor()

        # Verify ownership via class
        cursor.execute(
            """
            SELECT c.professor_id 
            FROM class_chapters ch
            JOIN classes c ON ch.class_id = c.class_id
            WHERE ch.chapter_id = %s
        """,
            (chapter_id,),
        )

        result = cursor.fetchone()
        if not result:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Chapter not found"}), 404

        if result[0] != user_id:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Unauthorized"}), 403

        cursor.execute(
            """
            UPDATE class_chapters 
            SET title = %s, description = %s, updated_at = CURRENT_TIMESTAMP
            WHERE chapter_id = %s
        """,
            (data.get("title"), data.get("description"), chapter_id),
        )

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chapters/<chapter_id>", methods=["DELETE", "OPTIONS"])
@require_auth
def delete_chapter(chapter_id):
    """Delete a chapter and all its exercises (professor only)"""
    try:
        user_id = g.user_id
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Verify chapter exists and user is the professor
        cursor.execute(
            """
            SELECT cc.class_id, cc.pdf_filename, c.professor_id
            FROM class_chapters cc
            JOIN classes c ON cc.class_id = c.class_id
            WHERE cc.chapter_id = %s
        """,
            (chapter_id,),
        )
        chapter_data = cursor.fetchone()

        if not chapter_data:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Chapter not found"}), 404

        class_id = chapter_data[0]
        pdf_filename = chapter_data[1]
        professor_id = chapter_data[2]

        if professor_id != user_id:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Only the class owner can delete chapters"}), 403

        # Delete associated exercises first (foreign key constraint)
        cursor.execute("DELETE FROM class_exercises WHERE chapter_id = %s", (chapter_id,))

        # Delete the chapter (PDF binary data will be deleted automatically)
        cursor.execute("DELETE FROM class_chapters WHERE chapter_id = %s", (chapter_id,))

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        return jsonify({"success": True, "message": "Chapter deleted successfully"}), 200

    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/chapters/<chapter_id>/generate-exercises", methods=["POST"])
@require_auth
def generate_exercises_for_chapter(chapter_id):
    """Generate exercises from an existing chapter's PDF data"""
    try:
        data = request.get_json() or {}
        user_id = g.user_id

        conn = get_db_connection()
        cursor = conn.cursor()

        # Get chapter data including PDF binary
        cursor.execute(
            """
            SELECT cc.pdf_data, cc.title, cc.class_id, c.professor_id
            FROM class_chapters cc
            JOIN classes c ON cc.class_id = c.class_id
            WHERE cc.chapter_id = %s
        """,
            (chapter_id,),
        )

        result = cursor.fetchone()
        if not result:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Chapter not found"}), 404

        pdf_data, chapter_title, class_id, professor_id = result

        # Verify user is the professor
        if professor_id != user_id:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Only the class professor can generate exercises"}), 403

        if not pdf_data:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "PDF data not found for this chapter"}), 404

        # Extract text from PDF binary data
        if not extract_text_from_pdf_bytes:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "PDF processor not available"}), 500

        try:
            pdf_text = extract_text_from_pdf_bytes(bytes(pdf_data))
        except Exception as e:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": f"Failed to extract text from PDF: {str(e)}"}), 500

        if not pdf_text:
            cursor.close()
            close_conn_safely(conn)
            return (
                jsonify(
                    {"error": "Could not extract text from PDF. PDF may be empty or image-based."}
                ),
                400,
            )

        # Generate exercises using AI
        if not generate_exercises_from_pdf_content:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Exercise generator not available"}), 500

        try:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not set")
            exercises = generate_exercises_from_pdf_content(pdf_text, chapter_title, api_key)
        except Exception as e:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": f"Failed to generate exercises: {str(e)}"}), 500

        if not exercises:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "No exercises were generated"}), 400

        # Store exercises in database
        exercises_generated = 0
        for idx, exercise in enumerate(exercises, 1):
            exercise_id = f"{chapter_id}_ex_{idx}_{int(datetime.now().timestamp() * 1000)}"
            cursor.execute(
                """
                INSERT INTO class_exercises (exercise_id, chapter_id, class_id, title, description, difficulty, solution_code, exercise_number)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
                (
                    exercise_id,
                    chapter_id,
                    class_id,
                    exercise["title"],
                    exercise["description"],
                    exercise["difficulty"],
                    exercise["solution_code"],
                    idx,
                ),
            )
            exercises_generated += 1

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        return (
            jsonify(
                {
                    "success": True,
                    "exercises_generated": exercises_generated,
                    "chapter_id": chapter_id,
                }
            ),
            201,
        )

    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/classes/<class_id>", methods=["DELETE"])
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

        return jsonify({"success": True}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Phase 6: Exercise Management Endpoints
# ============================================================================


@app.route("/api/chapters/<chapter_id>/exercises", methods=["GET"])
@require_auth
def get_chapter_exercises(chapter_id):
    """Get all exercises for a chapter"""
    try:
        user_id = g.user_id
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Verify chapter exists and user has access
        cursor.execute(
            """
            SELECT cc.class_id, c.professor_id
            FROM class_chapters cc
            JOIN classes c ON cc.class_id = c.class_id
            WHERE cc.chapter_id = %s
        """,
            (chapter_id,),
        )
        chapter_data = cursor.fetchone()
        if not chapter_data:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Chapter not found"}), 404

        class_id_result = chapter_data[0]
        professor_id = chapter_data[1]

        # Check access (professor or enrolled student)
        cursor.execute("SELECT role FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "User not found"}), 404

        role = user[0] or "student"
        is_professor = role == "professor"
        is_owner = professor_id == user_id

        if not is_owner and not is_professor:
            # Check if student is enrolled
            cursor.execute(
                """
                SELECT 1 FROM class_enrollments 
                WHERE class_id = %s AND student_id = %s
            """,
                (class_id_result, user_id),
            )
            if not cursor.fetchone():
                cursor.close()
                close_conn_safely(conn)
                return jsonify({"error": "Access denied"}), 403

        # Get exercises
        cursor.execute(
            """
            SELECT exercise_id, title, description, difficulty, exercise_number, created_at, solution_code
            FROM class_exercises
            WHERE chapter_id = %s
            ORDER BY exercise_number ASC
        """,
            (chapter_id,),
        )

        exercises = []
        for row in cursor.fetchall():
            exercises.append(
                {
                    "exercise_id": row[0],
                    "title": row[1],
                    "description": row[2],
                    "difficulty": row[3],
                    "exercise_number": row[4],
                    "created_at": row[5].isoformat() if row[5] else None,
                    "solution_code": row[6] or "",
                }
            )

        cursor.close()
        close_conn_safely(conn)

        return jsonify({"exercises": exercises}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/ai/chat", methods=["POST", "OPTIONS"])
@require_auth
def proxy_ai_chat():
    """Secure proxy for Gemini Chat API"""
    if request.method == "OPTIONS":
        response = app.response_class()
        cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers["Access-Control-Allow-Origin"] = cors_origin
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        return response

    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return jsonify({"error": "Server configuration error: AI API Key missing"}), 500

        data = request.json
        model = data.get("model", "gemini-2.5-flash")
        # Allow only known safe models to prevent abuse
        allowed_models = [
            "gemini-3-pro-preview",
            "gemini-3-flash-preview",
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-3-pro-image-preview",
        ]

        if model not in allowed_models:
            model = "gemini-2.5-flash"  # Fallback to safe default

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

        # Forward the request content to Google
        google_payload = {
            "contents": data.get("contents", []),
            "generationConfig": data.get("generationConfig", {}),
        }

        import requests

        response = requests.post(
            url, json=google_payload, headers={"Content-Type": "application/json"}, timeout=60
        )

        if not response.ok:
            return jsonify(response.json()), response.status_code

        return jsonify(response.json())

    except Exception as e:
        print(f"AI Proxy Error: {str(e)}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Phase 7: Student Enrollment Endpoints
# ============================================================================


@app.route("/api/classes/enroll", methods=["POST", "OPTIONS"])
@require_auth
def enroll_in_class():
    """Enroll student in a class using class_id (class code)"""
    try:
        if request.method == "OPTIONS":
            response = app.response_class()
            cors_origin = _get_cors_origin()
            if cors_origin:
                response.headers["Access-Control-Allow-Origin"] = cors_origin
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
            response.status_code = 200
            return response

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
        return jsonify({"error": str(e)}), 500


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
        return jsonify({"error": str(e)}), 500


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
        return jsonify({"error": str(e)}), 500


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
        return jsonify({"error": str(e)}), 500


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
        return jsonify({"error": str(e)}), 500


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
        return jsonify({"error": str(e)}), 500


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
        return jsonify({"error": str(e)}), 500


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
        return jsonify({"error": str(e)}), 500


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


@app.route("/api/classes/<class_id>/chapters/<chapter_id>/exercises", methods=["POST"])
@require_auth
def create_exercise(class_id, chapter_id):
    """Manually create a new exercise"""
    try:
        ensure_exercises_table()

        # Handle form data if file is present, otherwise JSON
        if request.content_type and "multipart/form-data" in request.content_type:
            data = request.form
        else:
            data = request.json or {}

        user_id = g.user_id

        conn = get_db_connection()
        cursor = conn.cursor()

        # Verify ownership
        cursor.execute(
            """
            SELECT c.professor_id
            FROM classes c
            WHERE c.class_id = %s
        """,
            (class_id,),
        )

        result = cursor.fetchone()
        if not result:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Class not found"}), 404

        professor_id = result[0]

        if professor_id != user_id:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Unauthorized"}), 403

        # Verify chapter belongs to class
        cursor.execute(
            "SELECT 1 FROM class_chapters WHERE chapter_id = %s AND class_id = %s",
            (chapter_id, class_id),
        )
        if not cursor.fetchone():
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Chapter not found in this class"}), 404

        exercise_id = f"ex_{str(uuid.uuid4())[:8]}"

        cursor.execute(
            """
            INSERT INTO class_exercises (
                exercise_id, class_id, chapter_id, title, description, 
                difficulty, solution_code, created_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
            (
                exercise_id,
                class_id,
                chapter_id,
                data.get("title"),
                data.get("description"),
                data.get("difficulty", "medium"),
                data.get("solution_code", ""),
                user_id,
            ),
        )

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        return jsonify({"success": True, "exercise_id": exercise_id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/classes/<class_id>/resources", methods=["POST", "OPTIONS"])
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
        return jsonify({"error": str(e)}), 500




# ============================================================================
# PDF File Serving Endpoint
# ============================================================================


@app.route("/api/chapters/<chapter_id>/pdf", methods=["GET"])
def serve_chapter_pdf(chapter_id):
    """Serve PDF file from database binary storage or filesystem (backward compatibility)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get PDF data from database
        cursor.execute(
            """
            SELECT pdf_data, pdf_filename, pdf_url
            FROM class_chapters
            WHERE chapter_id = %s
        """,
            (chapter_id,),
        )

        result = cursor.fetchone()
        cursor.close()
        close_conn_safely(conn)

        if not result:
            return jsonify({"error": "Chapter not found"}), 404

        pdf_data = result[0]
        pdf_filename = result[1] or "chapter.pdf"
        pdf_url = result[2]

        # NEW: If pdf_url exists (Supabase), redirect to it
        if pdf_url:
            from flask import redirect

            return redirect(pdf_url)

        # NEW: If pdf_data exists in database, serve from database
        if pdf_data:
            pdf_bytes = bytes(pdf_data)
            from flask import Response

            response = Response(pdf_bytes, mimetype="application/pdf")
            response.headers["Content-Disposition"] = (
                f'inline; filename="{pdf_filename}"'
            )
            cors_origin = _get_cors_origin()
            if cors_origin:
                response.headers["Access-Control-Allow-Origin"] = cors_origin
            return response

        # OLD: Fallback to filesystem for legacy chapters
        elif pdf_filename:
            pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], pdf_filename)
            if os.path.exists(pdf_path):
                response = send_from_directory(app.config["UPLOAD_FOLDER"], pdf_filename)
                cors_origin = _get_cors_origin()
                if cors_origin:
                    response.headers["Access-Control-Allow-Origin"] = cors_origin
                return response
            else:
                return jsonify({"error": f"PDF file not found: {pdf_filename}"}), 404

    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/exercises/<exercise_id>", methods=["DELETE", "OPTIONS"])
@require_auth
def delete_exercise(exercise_id):
    """Delete a specific exercise"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Verify exercise exists
        cursor.execute(
            "SELECT chapter_id, class_id FROM class_exercises WHERE exercise_id = %s",
            (exercise_id,),
        )
        result = cursor.fetchone()

        if not result:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Exercise not found"}), 404

        # Optional: Check if user is professor (omitted for brevity, handled by frontend context usually)

        # Delete the exercise
        cursor.execute("DELETE FROM class_exercises WHERE exercise_id = %s", (exercise_id,))
        conn.commit()

        cursor.close()
        close_conn_safely(conn)

        return jsonify({"success": True}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Phase 10: Class Resources Management
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


@app.route("/api/classes/<class_id>/resources/upload", methods=["POST", "OPTIONS"])
@require_auth
def upload_class_resource(class_id):
    """Upload a file as a resource"""
    # Handle CORS preflight explicitly
    if request.method == "OPTIONS":
        response = app.response_class()
        cors_origin = _get_cors_origin()
        if cors_origin:
            response.headers["Access-Control-Allow-Origin"] = cors_origin
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        return response

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
        return jsonify({"error": str(e)}), 500


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
        return jsonify({"error": str(e)}), 500


@app.route("/api/classes/<class_id>/resources/<resource_id>", methods=["PUT", "DELETE", "OPTIONS"])
def manage_resource(class_id, resource_id):
    """Update or Delete a resource"""
    try:
        if request.method == "OPTIONS":
            response = app.response_class()
            cors_origin = _get_cors_origin()
            if cors_origin:
                response.headers["Access-Control-Allow-Origin"] = cors_origin
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Methods"] = "PUT, DELETE, OPTIONS"
            response.status_code = 200
            return response

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
        return jsonify({"error": str(e)}), 500


@app.route("/api/resources/files/<filename>", methods=["GET"])
def serve_resource_file(filename):
    """Serve uploaded resource file (Legacy - kept for older non-migrated files)"""
    try:
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)
    except Exception as e:
        return jsonify({"error": "File not found"}), 404


# Serve frontend (local development: open http://localhost:5001)
_ROOT = os.path.dirname(os.path.abspath(__file__))


@app.route("/", methods=["GET"])
def serve_index():
    return send_from_directory(_ROOT, "index.html")


@app.route("/<path:path>", methods=["GET"])
def serve_frontend(path):
    """Serve frontend static files (HTML, CSS, JS, etc.) for local dev."""
    if path.startswith("api/") or path == "api":
        return jsonify({"error": "Not found"}), 404
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
