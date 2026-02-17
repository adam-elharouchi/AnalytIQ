"""
Response helper functions for consistent API responses.
Use these in new routes and the global error handler.
Existing routes are not retrofitted to avoid breaking frontend contracts.
"""

from flask import jsonify


def api_success(data=None, message=None, status=200):
    """Return a successful JSON response."""
    body = {}
    if data is not None:
        body["data"] = data
    if message:
        body["message"] = message
    if not body:
        body["success"] = True
    return jsonify(body), status


def api_error(message="An unexpected error occurred. Please try again.", status=500):
    """Return an error JSON response."""
    return jsonify({"error": message}), status


def api_list(items, key="items"):
    """Return a JSON response wrapping a list."""
    return jsonify({key: items}), 200
