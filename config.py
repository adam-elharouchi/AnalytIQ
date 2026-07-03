"""
AnalytIQ Configuration
Centralized configuration management for the application
"""

import os
from datetime import timedelta

# ============================================================================
# ENVIRONMENT
# ============================================================================

ENV = os.getenv("FLASK_ENV", "development")
DEBUG = ENV == "development"
TESTING = ENV == "testing"

# ============================================================================
# FLASK APPLICATION
# ============================================================================

SEND_FILE_MAX_AGE_DEFAULT = 0
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB max file size
UPLOAD_FOLDER = "Course Content"

# ============================================================================
# DATABASE
# ============================================================================

# Connection Pool Configuration
DB_POOL_MIN_CONNECTIONS = int(os.getenv("DB_POOL_MIN", 1))
DB_POOL_MAX_CONNECTIONS = int(os.getenv("DB_POOL_MAX", 5))

# Connection Timeouts
DB_CONNECTION_TIMEOUT = int(os.getenv("DB_CONNECTION_TIMEOUT", 10))  # seconds
DB_STATEMENT_TIMEOUT = int(os.getenv("DB_STATEMENT_TIMEOUT", 30))  # seconds

# ============================================================================
# FILE UPLOAD
# ============================================================================

# File Size Limits
MAX_PDF_SIZE_MB = int(os.getenv("MAX_PDF_SIZE_MB", 50))
MAX_PDF_SIZE_BYTES = MAX_PDF_SIZE_MB * 1024 * 1024

# Allowed Extensions
ALLOWED_EXTENSIONS = {"pdf", "csv", "xlsx", "xls", "json", "txt", "ipynb", "docx"}

# PDF Validation
PDF_HEADER_CHECK_BYTES = 1024
PDF_CONTENT_SAMPLE_BYTES = 10240  # 10KB for malicious content detection

# Suspicious PDF Patterns
SUSPICIOUS_PDF_PATTERNS = [
    b"/JavaScript",  # Embedded JavaScript
    b"/JS",  # JavaScript shorthand
    b"/Launch",  # Launch external programs
    b"/EmbeddedFile",  # Embedded executables
]

# ============================================================================
# RATE LIMITING
# ============================================================================

# Default Rate Limits (much higher in development so localhost doesn't hit 429)
_default_day = 200
_default_hour = 50
if ENV == "development" or DEBUG:
    _default_day = 50000
    _default_hour = 2000
RATE_LIMIT_DEFAULT_PER_DAY = int(os.getenv("RATE_LIMIT_DAY", _default_day))
RATE_LIMIT_DEFAULT_PER_HOUR = int(os.getenv("RATE_LIMIT_HOUR", _default_hour))

# Endpoint-Specific Limits
RATE_LIMIT_SIGNUP_PER_HOUR = int(os.getenv("RATE_LIMIT_SIGNUP", 5))
RATE_LIMIT_SIGNIN_PER_MINUTE = int(os.getenv("RATE_LIMIT_SIGNIN", 10))
RATE_LIMIT_FORGOT_PASSWORD_PER_HOUR = int(os.getenv("RATE_LIMIT_FORGOT_PW", 3))
RATE_LIMIT_RESET_PASSWORD_PER_HOUR = int(os.getenv("RATE_LIMIT_RESET_PW", 5))

# ============================================================================
# PLATFORM OWNER
# ============================================================================

# The platform owner has unrestricted superadmin access (can delete/impersonate
# any account including other superadmins). Override via env var if needed.
PLATFORM_OWNER_EMAIL = os.getenv("PLATFORM_OWNER_EMAIL", "aelharouchi@myanalytiq.org")

# ============================================================================
# SECURITY
# ============================================================================

# Password Hashing
BCRYPT_LOG_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", 12))

# Session
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
SESSION_COOKIE_SECURE = ENV == "production"
SESSION_COOKIE_HTTPONLY = True
# "None" required for LTI 1.3: the tool runs inside an LMS iframe (cross-origin),
# so SameSite=Lax/Strict blocks the session cookie entirely.
# SameSite=None is safe here because SESSION_COOKIE_SECURE=True in production.
SESSION_COOKIE_SAMESITE = "None" if ENV == "production" else "Lax"

# JWT Authentication
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
JWT_ACCESS_TOKEN_EXPIRES_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", 168))  # legacy (unused default)
# Short-lived access token + long-lived refresh token (see /api/users/refresh).
# Conservative default (24h) for a safe rollout; lower to 1 once the refresh
# flow is verified in staging. Fully env-tunable — no code change/deploy needed.
JWT_ACCESS_TTL_HOURS = int(os.getenv("JWT_ACCESS_TTL_HOURS", 24))
JWT_REFRESH_TTL_DAYS = int(os.getenv("JWT_REFRESH_TTL_DAYS", 30))
JWT_ALGORITHM = "HS256"

# ============================================================================
# LTI 1.3
# ============================================================================
# RSA key pair (PEM format). Generate with: python3 scripts/generate_lti_keys.py
LTI_PRIVATE_KEY = os.getenv("LTI_PRIVATE_KEY", "")
LTI_PUBLIC_KEY = os.getenv("LTI_PUBLIC_KEY", "")
LTI_KEY_ID = os.getenv("LTI_KEY_ID", "analytiq-lti-key-1")
# Canonical base URL of this tool — used in deep linking and JWKS references
LTI_TOOL_URL = os.getenv("LTI_TOOL_URL", "https://myanalytiq.org")
# Lifetime of LTI launch sessions stored in DB (seconds)
LTI_SESSION_TTL = int(os.getenv("LTI_SESSION_TTL", 3600))

# CORS — in production an explicit allowlist must be provided via the
# CORS_ORIGINS env var; if it is missing the list is empty so no cross-origin
# request is permitted (same-origin only). Non-production envs keep the "*"
# convenience default. This prevents an accidentally wide-open prod deployment.
_cors_default = "" if ENV == "production" else "*"
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", _cors_default).split(",") if o.strip()]
CORS_MAX_AGE = int(os.getenv("CORS_MAX_AGE", 3600))

# ============================================================================
# API CONFIGURATION
# ============================================================================

# Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
GEMINI_TIMEOUT = int(os.getenv("GEMINI_TIMEOUT", 60))  # seconds

# ============================================================================
# EMAIL CONFIGURATION
# ============================================================================

MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "True").lower() == "true"
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "noreply@analytiq.com")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")

# ============================================================================
# LOGGING
# ============================================================================

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO" if ENV == "production" else "DEBUG")
LOG_FORMAT = os.getenv("LOG_FORMAT", "json")  # 'json' or 'text'

# ============================================================================
# PAGINATION
# ============================================================================

DEFAULT_PAGE_SIZE = int(os.getenv("DEFAULT_PAGE_SIZE", 20))
MAX_PAGE_SIZE = int(os.getenv("MAX_PAGE_SIZE", 100))

# ============================================================================
# HEALTH CHECK
# ============================================================================

HEALTH_CHECK_TIMEOUT = int(os.getenv("HEALTH_CHECK_TIMEOUT", 5))  # seconds

# ============================================================================
# PASSWORD RESET
# ============================================================================

PASSWORD_RESET_TOKEN_EXPIRY_HOURS = int(os.getenv("PW_RESET_EXPIRY_HOURS", 24))
PASSWORD_RESET_TOKEN_EXPIRY = timedelta(hours=PASSWORD_RESET_TOKEN_EXPIRY_HOURS)

# ============================================================================
# FEATURE FLAGS
# ============================================================================

FEATURE_AI_EXERCISES = os.getenv("FEATURE_AI_EXERCISES", "True").lower() == "true"
FEATURE_EMAIL_NOTIFICATIONS = os.getenv("FEATURE_EMAIL", "False").lower() == "true"
FEATURE_ANALYTICS = os.getenv("FEATURE_ANALYTICS", "True").lower() == "true"
FEATURE_CSRF_PROTECTION = os.getenv("FEATURE_CSRF", "True").lower() == "true"
FEATURE_ASYNC_TASKS = os.getenv("FEATURE_ASYNC_TASKS", "False").lower() == "true"


# ============================================================================
# CSRF PROTECTION
# ============================================================================

# CSRF Configuration
WTF_CSRF_ENABLED = FEATURE_CSRF_PROTECTION
WTF_CSRF_TIME_LIMIT = int(os.getenv("CSRF_TIME_LIMIT", 3600))  # 1 hour default
WTF_CSRF_SSL_STRICT = ENV == "production"
WTF_CSRF_CHECK_DEFAULT = FEATURE_CSRF_PROTECTION


# ============================================================================
# SUPABASE STORAGE
# ============================================================================

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "pdfs")


# ============================================================================
# SSO (Single Sign-On)
# ============================================================================

FEATURE_SSO = os.getenv("FEATURE_SSO", "False").lower() == "true"
# Seconds an OAuth2 state token remains valid in Redis
SSO_STATE_TTL = int(os.getenv("SSO_STATE_TTL", 600))  # 10 minutes
# Base URL used to build SSO callback URIs and post-login redirects
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://myanalytiq.org")
SSO_REDIRECT_BASE_URL = FRONTEND_URL

# ============================================================================
# REDIS CACHING
# ============================================================================

# Redis Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_DEFAULT_TTL = int(os.getenv("CACHE_TTL", 300))  # 5 minutes default
FEATURE_CACHING = os.getenv("FEATURE_CACHING", "False").lower() == "true"


# ============================================================================
# INPUT FIELD LIMITS
# ============================================================================

# User fields
MAX_EMAIL_LENGTH = 254  # RFC 5321
MAX_NAME_LENGTH = 100
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 72  # bcrypt hard limit

# Class / chapter fields
MAX_CLASS_NAME_LENGTH = 200
MAX_CLASS_DESCRIPTION_LENGTH = 2000
MAX_CHAPTER_TITLE_LENGTH = 300

# Exercise fields
MAX_EXERCISE_TITLE_LENGTH = 300
MAX_EXERCISE_DESCRIPTION_LENGTH = 5000
MAX_SOLUTION_CODE_LENGTH = 20000

# AI chat
MAX_AI_MESSAGE_LENGTH = 50_000  # ~50KB per message
MAX_AI_CONVERSATION_MESSAGES = 100

# Generic text
MAX_GENERIC_TEXT_LENGTH = 10_000

# Portfolio
PORTFOLIO_ENABLED = True
PORTFOLIO_MAX_ITEMS = 100
PORTFOLIO_MAX_CODE_LENGTH = 50_000
PORTFOLIO_EXECUTION_TIMEOUT = 30  # seconds
PORTFOLIO_AUTOSAVE_INTERVAL = 30_000  # milliseconds (frontend)

# GitHub OAuth (for portfolio GitHub sync)
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI")
GITHUB_DEFAULT_REPO_NAME = "analytiq-portfolio"


# ============================================================================
# VALIDATION
# ============================================================================


def validate_config():
    """Validate critical configuration values"""
    errors = []

    # Check database URL
    if not os.getenv("DATABASE_URL"):
        errors.append("DATABASE_URL environment variable is required")

    # Check Gemini API key if AI features enabled
    if FEATURE_AI_EXERCISES and not GEMINI_API_KEY:
        errors.append("GEMINI_API_KEY required when FEATURE_AI_EXERCISES is enabled")

    # Check email config if notifications enabled
    if FEATURE_EMAIL_NOTIFICATIONS:
        if not MAIL_USERNAME or not MAIL_PASSWORD:
            errors.append("MAIL_USERNAME and MAIL_PASSWORD required when FEATURE_EMAIL is enabled")

    # Check secret key in production
    if ENV == "production" and SECRET_KEY == "dev-secret-key-change-in-production":
        errors.append("SECRET_KEY must be changed in production")

    return errors


# ============================================================================
# CONFIGURATION SUMMARY
# ============================================================================


def get_config_summary():
    """Get configuration summary for logging"""
    return {
        "environment": ENV,
        "debug": DEBUG,
        "database": {
            "pool_min": DB_POOL_MIN_CONNECTIONS,
            "pool_max": DB_POOL_MAX_CONNECTIONS,
            "connection_timeout": DB_CONNECTION_TIMEOUT,
            "statement_timeout": DB_STATEMENT_TIMEOUT,
        },
        "file_upload": {"max_pdf_size_mb": MAX_PDF_SIZE_MB},
        "rate_limiting": {
            "default_per_day": RATE_LIMIT_DEFAULT_PER_DAY,
            "default_per_hour": RATE_LIMIT_DEFAULT_PER_HOUR,
        },
        "features": {
            "ai_exercises": FEATURE_AI_EXERCISES,
            "email_notifications": FEATURE_EMAIL_NOTIFICATIONS,
            "analytics": FEATURE_ANALYTICS,
        },
    }
