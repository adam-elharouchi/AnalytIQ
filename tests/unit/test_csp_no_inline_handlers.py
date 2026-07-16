"""
tests/unit/test_csp_no_inline_handlers.py — CSP Phase 2 progress guard.

Scans the SOURCE of every file whose inline on* handlers have been refactored to
addEventListener and asserts none remain. Two surfaces matter, because both break
under an enforced script-src:

  * templates/*.html — static markup AND handlers inside JS template-literal HTML
  * static/js/*.js   — handlers inside HTML built in template literals (innerHTML)

Add a filename to _DONE_TEMPLATES / _DONE_JS as each file is finished; the test
then guards it against regressions. When both lists cover every file, the
nonce-based script-src can move from Report-Only into the enforced CSP.
"""
import os
import re

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_TEMPLATES = os.path.join(_ROOT, "templates")
_JS = os.path.join(_ROOT, "static", "js")

# Matches an inline event-handler attribute: whitespace + on<word> + = + quote.
# Standalone ` onclick="` only occurs in HTML markup or HTML-in-JS strings (the
# thing we refactor); JS property assignments read `el.onclick =` (dot, not space).
# The optional backslash catches handlers inside escaped strings in JS.
_HANDLER_RE = re.compile(r"\son[a-z]+\s*=\s*\\?[\"']")

# Templates refactored so far (kept in sync with the CSP Phase 2 work).
_DONE_TEMPLATES = [
    "base.html",
    "login.html",
    "reset-password.html",
    "index.html",
    "profile.html",
    "landing.html",
    "chapter-view.html",
    "lti-deep-link.html",
    "professor-dashboard.html",
    "student-classes.html",
    "student-class.html",
    "upload-assistant.html",
    "lti-setup.html",
    "practice-playground.html",
    "code-assistant.html",
]

# JS modules refactored so far. Many build HTML via innerHTML template literals,
# so their handlers must become delegated listeners on a stable container.
# Still outstanding (not yet in this list): student-class.js, superadmin.js,
# professor-class.js, tenant-admin.js, content-import.js.
_DONE_JS = [
    "navigation.js",
    "code-assistant.js",
    "professor-dashboard.js",
    "student-classes.js",
    "upload-assistant.js",
]


def _scan(directory, names):
    offenders = {}
    for name in names:
        with open(os.path.join(directory, name), encoding="utf-8") as fh:
            hits = _HANDLER_RE.findall(fh.read())
        if hits:
            offenders[name] = hits
    return offenders


def test_completed_templates_have_no_inline_handlers():
    offenders = _scan(_TEMPLATES, _DONE_TEMPLATES)
    assert not offenders, f"inline on* handlers still present in templates: {offenders}"


def test_completed_js_modules_have_no_inline_handlers():
    offenders = _scan(_JS, _DONE_JS)
    assert not offenders, f"inline on* handlers still present in static/js: {offenders}"
