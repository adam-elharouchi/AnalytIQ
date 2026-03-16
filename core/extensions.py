"""
AnalytIQ Extensions
Shared Flask extension instances that are created without an app object
and later configured via init_app() in app.py.
"""

# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------

try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address

    limiter = Limiter(key_func=get_remote_address)
except ImportError:
    limiter = None


def rate_limit(rate: str):
    """Apply a Flask-Limiter rate limit only when the limiter is available."""

    def decorator(f):
        if limiter is not None:
            return limiter.limit(rate)(f)
        return f

    return decorator


# ---------------------------------------------------------------------------
# CSRF Protection
# ---------------------------------------------------------------------------

# csrf is set to the CSRFProtect instance by app.py after init_app() is
# called (only when FEATURE_CSRF_PROTECTION is True).  It remains None when
# CSRF is disabled so that csrf_exempt() degrades gracefully.
csrf = None


def csrf_exempt(view_func):
    """
    Mark a view function as exempt from CSRF checks.

    Uses flask_wtf.csrf.csrf_exempt which stamps `view_func.csrf_exempt = True`
    on the function itself.  CSRFProtect reads that flag at *request* time, so
    this works correctly even though blueprints are decorated before app.py
    calls csrf_instance.init_app(app).  Falls back to a no-op when Flask-WTF
    is not installed.
    """
    try:
        from flask_wtf.csrf import csrf_exempt as _wtf_csrf_exempt

        return _wtf_csrf_exempt(view_func)
    except ImportError:
        return view_func
