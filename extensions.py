"""
AnalytIQ Extensions
Shared Flask extension instances that are created without an app object
and later configured via init_app() in app.py.
"""

# Email (Resend)
# Using resend Python SDK directly, no Flask extension needed.
mail = None

# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------

try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address

    limiter = Limiter(key_func=get_remote_address)
except ImportError:
    limiter = None

# ---------------------------------------------------------------------------
# CSRF Protection
# ---------------------------------------------------------------------------

# csrf is set to the CSRFProtect instance by app.py after init_app() is
# called (only when FEATURE_CSRF_PROTECTION is True).  It remains None when
# CSRF is disabled so that csrf_exempt() degrades gracefully.
csrf = None


def csrf_exempt(view_func):
    """
    Wrapper decorator so we can safely exempt JSON API endpoints from CSRF
    checks even when CSRF is disabled or Flask-WTF is not installed.
    """
    if csrf is not None:
        return csrf.exempt(view_func)
    return view_func
