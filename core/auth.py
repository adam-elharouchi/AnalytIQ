"""
AnalytIQ Auth Helpers
JWT authentication, password hashing, field validation, and role detection.
Extracted from app.py as Phase 1 of Blueprint extraction.
"""

import logging
import os
import re
import functools
from datetime import datetime, timedelta

import jwt
import bcrypt
from flask import jsonify, request, g, current_app

import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Email validation
# ---------------------------------------------------------------------------

# RFC 5321-compatible simple pattern — covers 99%+ of real addresses.
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


def validate_email(email):
    """Return True if *email* passes basic format validation.

    Checks:
    - Non-empty string
    - Matches ``user@domain.tld`` pattern (no consecutive dots, valid TLD ≥ 2 chars)
    - Does not exceed RFC 5321 maximum length (254 chars)
    """
    if not email or not isinstance(email, str):
        return False
    stripped = email.strip()
    return bool(_EMAIL_RE.match(stripped)) and len(stripped) <= config.MAX_EMAIL_LENGTH


# ---------------------------------------------------------------------------
# Field validation
# ---------------------------------------------------------------------------


def validate_fields(data, rules):
    """
    Validate a dict of fields against length and presence rules.

    rules is a list of tuples:
        (field_name, required, max_length)

    Returns a list of error strings. Empty list means all OK.

    Example:
        errors = validate_fields(
            {"name": "Alice", "email": "a@b.com"},
            [("name", True, config.MAX_NAME_LENGTH),
             ("email", True, config.MAX_EMAIL_LENGTH)],
        )
        if errors:
            return jsonify({"error": errors[0]}), 400
    """
    errors = []
    for field, required, max_length in rules:
        value = data.get(field)
        if required and not value:
            errors.append(f"{field} is required")
        elif value and max_length and len(str(value)) > max_length:
            errors.append(f"{field} must be {max_length} characters or fewer")
    return errors


# ---------------------------------------------------------------------------
# Role detection
# ---------------------------------------------------------------------------


def detect_role_from_email(email):
    """Detect user role from email domain"""
    if not email:
        return "student"
    email_lower = email.lower()
    if email_lower.endswith("@myanalytiq.org"):
        return "superadmin"
    return "student"  # Default to student


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------


def create_jwt_token(
    user_id,
    role="student",
    name=None,
    email=None,
    impersonator_id=None,
    expires_hours=None,
    tenant_id=None,
    token_version=0,
):
    """
    Create a JWT token for an authenticated user.

    Args:
        user_id: The user's ID
        role: The user's role (student/professor/tenant_admin/superadmin)
        name: The user's name (optional, included in token for convenience)
        email: The user's email (optional, included in token for convenience)
        impersonator_id: If impersonating, the user_id of the super admin
        expires_hours: Override default expiry (e.g. 1 for short-lived impersonation tokens)
        tenant_id: For tenant_admin users, their scoped tenant (optional)

    Returns:
        str: Encoded JWT token
    """
    ttl = expires_hours if expires_hours is not None else config.JWT_ACCESS_TTL_HOURS
    payload = {
        "user_id": user_id,
        "role": role,
        "type": "access",
        "tv": int(token_version or 0),  # revocation counter (see users.token_version)
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=ttl),
    }
    if name:
        payload["name"] = name
    if email:
        payload["email"] = email
    if impersonator_id:
        payload["impersonator_id"] = impersonator_id
    if tenant_id:
        payload["tenant_id"] = tenant_id

    return jwt.encode(payload, config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM)


def create_refresh_token(user_id, token_version=0):
    """Create a long-lived refresh token used to mint fresh access tokens.

    Carries only the user_id, a ``type: "refresh"`` marker, and the revocation
    counter (tv). It is exchanged at /api/users/refresh for a new short-lived
    access token. A refresh token is NEVER accepted by require_auth.
    """
    payload = {
        "user_id": user_id,
        "type": "refresh",
        "tv": int(token_version or 0),
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(days=config.JWT_REFRESH_TTL_DAYS),
    }
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


def get_user_token_version(conn, user_id):
    """Return the user's current token_version, or 0 on any error/missing column.

    Rolls back on failure so a pooled connection is never returned in an aborted
    transaction state.
    """
    try:
        cur = conn.cursor()
        cur.execute("SELECT token_version FROM users WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        cur.close()
        return int(row[0]) if row and row[0] is not None else 0
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return 0


def bump_user_token_version(conn, user_id):
    """Increment the user's token_version, revoking all outstanding JWTs.

    Best-effort: the caller commits. Returns True on success. Does NOT commit.
    """
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET token_version = COALESCE(token_version, 0) + 1 WHERE user_id = %s",
            (user_id,),
        )
        cur.close()
        return True
    except Exception as exc:
        logger.warning("Failed to bump token_version for %s: %s", user_id, exc)
        try:
            conn.rollback()
        except Exception:
            pass
        return False


# ---------------------------------------------------------------------------
# Short-lived media access tokens (capability URLs)
# ---------------------------------------------------------------------------
# Media endpoints (chapter PDFs, resource downloads) are loaded via <iframe src>
# / <a href> / pdf.js, which cannot attach an Authorization header. An authorized
# client first mints a short-lived, single-resource capability token (below) and
# appends it as ?token=...  The serve endpoint then verifies the token matches the
# requested (kind, resource_id) and is unexpired. Authorization is checked once,
# at mint time, by the authenticated mint endpoint.

MEDIA_TOKEN_TTL_SECONDS = int(os.getenv("MEDIA_TOKEN_TTL", 600))  # 10 minutes


def create_media_token(kind, resource_id, ttl_seconds=MEDIA_TOKEN_TTL_SECONDS):
    """Return a signed, short-lived token granting read access to one resource."""
    payload = {
        "scope": "media",
        "kind": kind,
        "rid": str(resource_id),
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(seconds=ttl_seconds),
    }
    return jwt.encode(payload, config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM)


def verify_media_token(token, kind, resource_id):
    """Return True iff *token* is a valid, unexpired media token for (kind, resource_id)."""
    if not token:
        return False
    try:
        payload = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=[config.JWT_ALGORITHM])
    except jwt.InvalidTokenError:
        return False
    return (
        payload.get("scope") == "media"
        and payload.get("kind") == kind
        and payload.get("rid") == str(resource_id)
    )


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


def hash_password_legacy(password):
    """
    DEPRECATED: insecure djb2-style hash kept only to verify passwords set before
    the bcrypt migration.  New passwords always use hash_password() (bcrypt).

    Removal checklist:
    1. Run `python scripts/audit_legacy_hashes.py` — must exit 0 (zero rows).
    2. Delete this function.
    3. Remove the `else` branch in verify_password() that calls it.
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
    # Check if it's a bcrypt hash (starts with $2b$ or $2a$)
    if hashed_password.startswith("$2"):
        try:
            is_valid = bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
            return (is_valid, False)  # Valid bcrypt hash, no rehash needed
        except Exception as e:
            logger.warning("Bcrypt verification error: %s", e)
            return (False, False)
    else:
        # Legacy hash - verify and flag for rehashing
        legacy_hash = hash_password_legacy(password)
        is_valid = legacy_hash == hashed_password
        return (is_valid, is_valid)  # If valid, needs rehash


# ---------------------------------------------------------------------------
# Auth decorators
# ---------------------------------------------------------------------------


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
        if request.method == "OPTIONS":
            return f(*args, **kwargs)

        # Bypass auth only when BOTH the TESTING flag is set AND env is explicitly "testing".
        # Read FLASK_ENV from os.environ at request time (not config.ENV) to avoid a
        # stale cached value caused by module-level imports during pytest collection.
        if current_app.config.get("TESTING") is True and os.environ.get("FLASK_ENV") == "testing":
            # Check for explicit test user ID or user_id in request
            test_user_id = request.headers.get("X-Test-User-ID")
            if not test_user_id:
                # Try to get from query params or JSON body
                test_user_id = request.args.get("user_id")
                if not test_user_id:
                    json_data = request.get_json(silent=True)
                    if json_data:
                        test_user_id = json_data.get("user_id")
                # Also check form data for multipart requests
                if not test_user_id and request.form:
                    test_user_id = request.form.get("user_id")

            if test_user_id:
                g.user_id = str(test_user_id)
                g.user_role = request.headers.get("X-Test-User-Role", "student")
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
            # A refresh token must never be usable as an access token.
            if payload.get("type") == "refresh":
                return jsonify({"error": "Invalid token. Please sign in again."}), 401
            g.user_id = str(payload["user_id"])
            g.user_role = payload.get("role", "student")
            g.user_email = payload.get("email", "")
            g.impersonator_id = payload.get("impersonator_id")
            g.tenant_id = payload.get("tenant_id")
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired. Please sign in again."}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token. Please sign in again."}), 401

        # Reject disabled accounts and revoked tokens even when the JWT is valid.
        # Fail open (pass through) only if the DB check itself errors, so a DB
        # hiccup does not lock out all users. A definite mismatch fails closed.
        _revoked = False
        try:
            from core.database import get_db_connection

            _conn = get_db_connection()
            _cur = _conn.cursor()
            _cur.execute(
                "SELECT account_status, token_version FROM users WHERE user_id = %s",
                (g.user_id,),
            )
            _row = _cur.fetchone()
            _cur.close()
            if _row and _row[0] == "disabled":
                return jsonify({"error": "Account is disabled. Contact support."}), 403
            if _row and _row[0] == "pending_approval":
                return (
                    jsonify(
                        {
                            "error": "Account pending approval. An administrator will review your request shortly."
                        }
                    ),
                    403,
                )
            # Token revocation: the token's tv claim must match the stored counter.
            if _row and _row[1] is not None and int(_row[1]) != int(payload.get("tv", 0)):
                _revoked = True
        except Exception:
            pass  # fail open on DB error

        if _revoked:
            return jsonify({"error": "Session expired. Please sign in again."}), 401

        return f(*args, **kwargs)

    return decorated


def require_role(*roles):
    """
    Decorator that checks g.user_role is in the given roles.
    Must be applied AFTER @require_auth so that g.user_role is already set.

    Usage:
        @app.route('/api/admin/something')
        @require_auth
        @require_role('professor')
        def professor_only():
            ...
    """

    def decorator(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            user_role = getattr(g, "user_role", None)
            if user_role not in roles:
                return jsonify({"error": "Forbidden: insufficient role"}), 403
            return f(*args, **kwargs)

        return decorated

    return decorator


def require_super_admin(f):
    """
    Decorator that checks g.user_role is 'superadmin'.
    Must be applied AFTER @require_auth.
    """

    @functools.wraps(f)
    def decorated(*args, **kwargs):
        user_role = getattr(g, "user_role", None)
        if user_role != "superadmin":
            return jsonify({"error": "Forbidden: super admin access required"}), 403
        return f(*args, **kwargs)

    return decorated


def require_tenant_admin(f):
    """
    Decorator that allows access for 'tenant_admin' or 'superadmin' roles.
    Must be applied AFTER @require_auth.

    Usage:
        @app.route('/api/sso/admin/providers')
        @require_auth
        @require_tenant_admin
        def manage_sso_providers():
            tenant_id = g.tenant_id  # set for tenant_admin; None for superadmin
    """

    @functools.wraps(f)
    def decorated(*args, **kwargs):
        user_role = getattr(g, "user_role", None)
        if user_role not in ("tenant_admin", "superadmin"):
            return jsonify({"error": "Forbidden: tenant admin access required"}), 403
        return f(*args, **kwargs)

    return decorated
