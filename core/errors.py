"""
Centralized error response helpers.

All API error responses must go through these helpers to guarantee a single,
consistent JSON shape across every blueprint:

    { "error": "<human-readable message>", "code": "<MACHINE_CODE>" }

The `code` field is optional but should always be included for errors that
clients need to handle programmatically (e.g. "INVALID_CREDENTIALS").

Usage
-----
    from core.errors import bad_request, unauthorized, not_found, server_error

    return bad_request("Email is required")
    return unauthorized()
    return not_found("Class not found")
    return server_error()                          # generic 500
    return error_response("Custom message", 422, code="UNPROCESSABLE")
"""

from flask import jsonify


def error_response(message: str, status_code: int, *, code: str | None = None):
    """
    Build a JSON error response with a consistent shape.

    Args:
        message:     Human-readable error description.
        status_code: HTTP status code (4xx or 5xx).
        code:        Optional machine-readable error code (e.g. "NOT_FOUND").

    Returns:
        A (Response, int) tuple suitable for returning from a Flask view.
    """
    payload: dict = {"error": message}
    if code:
        payload["code"] = code
    return jsonify(payload), status_code


# ---------------------------------------------------------------------------
# 400-level shortcuts
# ---------------------------------------------------------------------------


def bad_request(message: str = "Bad request", *, code: str | None = None):
    """400 Bad Request."""
    return error_response(message, 400, code=code)


def unauthorized(message: str = "Authentication required", *, code: str | None = None):
    """401 Unauthorized."""
    return error_response(message, 401, code=code)


def forbidden(message: str = "Access denied", *, code: str | None = None):
    """403 Forbidden."""
    return error_response(message, 403, code=code)


def not_found(message: str = "Resource not found", *, code: str | None = None):
    """404 Not Found."""
    return error_response(message, 404, code=code)


def conflict(message: str = "Resource already exists", *, code: str | None = None):
    """409 Conflict."""
    return error_response(message, 409, code=code)


def unprocessable(message: str = "Unprocessable request", *, code: str | None = None):
    """422 Unprocessable Entity."""
    return error_response(message, 422, code=code)


def too_many_requests(message: str = "Too many requests", *, code: str | None = None):
    """429 Too Many Requests."""
    return error_response(message, 429, code=code)


# ---------------------------------------------------------------------------
# 500-level shortcuts
# ---------------------------------------------------------------------------

_GENERIC_500 = "An unexpected error occurred. Please try again."


def server_error(message: str = _GENERIC_500, *, code: str | None = None):
    """500 Internal Server Error — always use the generic message for public responses."""
    return error_response(message, 500, code=code)


def service_unavailable(
    message: str = "Service temporarily unavailable", *, code: str | None = None
):
    """503 Service Unavailable."""
    return error_response(message, 503, code=code)
