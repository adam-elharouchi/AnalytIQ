"""
tests/unit/test_csp_no_inline_handlers.py — CSP Phase 2 progress guard.

Scans the template SOURCE of every page whose inline on* handlers have been
refactored to addEventListener and asserts none remain (static attributes or
handlers embedded in JS template-literal HTML). Add a filename to _DONE as each
page is finished; the test then guards it against regressions. When _DONE covers
every template, script-src can be moved into the enforced CSP.
"""
import os
import re

_TEMPLATES = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "templates"))

# Matches an inline event-handler attribute: whitespace + on<word> + = + quote.
# Standalone ` onclick="` only occurs in HTML markup or HTML-in-JS strings (the
# thing we refactor); JS property assignments read `el.onclick =` (dot, not space).
_HANDLER_RE = re.compile(r'\son[a-z]+\s*=\s*"')

# Pages refactored so far (kept in sync with the CSP Phase 2 work).
_DONE = [
    "base.html",
    "login.html",
    "reset-password.html",
    "index.html",
    "profile.html",
    "landing.html",
    "chapter-view.html",
    "lti-deep-link.html",
    "professor-dashboard.html",
    "modules.html",
    "resources.html",
    "student-classes.html",
    "student-class.html",
    "upload-assistant.html",
    "lti-setup.html",
]


def test_completed_templates_have_no_inline_handlers():
    offenders = {}
    for name in _DONE:
        path = os.path.join(_TEMPLATES, name)
        with open(path, encoding="utf-8") as fh:
            hits = _HANDLER_RE.findall(fh.read())
        if hits:
            offenders[name] = hits
    assert not offenders, f"inline on* handlers still present: {offenders}"
