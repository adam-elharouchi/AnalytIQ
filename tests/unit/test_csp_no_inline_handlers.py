"""
tests/unit/test_csp_no_inline_handlers.py — CSP inline-handler gate.

The CSP Phase 2 refactor removed every inline event handler across the frontend so
script-src can be enforced without 'unsafe-inline'. This is now a repo-wide gate
(not a per-file allowlist): it scans EVERY served template (including subdirs like
templates/portfolio/) and EVERY static/js module, and fails if any inline handler
reappears or any inline <script> is missing its nonce. Both would break under the
enforced script-src.
"""
import glob
import os
import re

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_TEMPLATES = os.path.join(_ROOT, "templates")
_JS = os.path.join(_ROOT, "static", "js")

# Inline event-handler attribute: whitespace + on<word> + = + quote. Standalone
# ` onclick="` only occurs in HTML markup or HTML-in-JS strings (what we refactor);
# JS property assignments read `el.onclick =` (dot, not space). The optional
# backslash catches handlers inside escaped strings in JS template literals.
_HANDLER_RE = re.compile(r"\son[a-z]+\s*=\s*\\?[\"']")

# A javascript: URL is script execution too, and is blocked by an enforced
# script-src just like an inline handler.
_JS_URI_RE = re.compile(r"""["']javascript:""")

# An inline <script> (no src=) must carry a nonce to run under the enforced policy.
_SCRIPT_OPEN_RE = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>", re.IGNORECASE)


def _templates():
    return sorted(glob.glob(os.path.join(_TEMPLATES, "**", "*.html"), recursive=True))


def _js_modules():
    return sorted(glob.glob(os.path.join(_JS, "*.js")))


def _rel(path):
    return os.path.relpath(path, _ROOT)


def test_no_inline_handlers_in_templates():
    offenders = {}
    for path in _templates():
        hits = _HANDLER_RE.findall(open(path, encoding="utf-8").read())
        if hits:
            offenders[_rel(path)] = hits
    assert not offenders, f"inline on* handlers present (breaks enforced script-src): {offenders}"


def test_no_inline_handlers_in_js_modules():
    offenders = {}
    for path in _js_modules():
        hits = _HANDLER_RE.findall(open(path, encoding="utf-8").read())
        if hits:
            offenders[_rel(path)] = hits
    assert not offenders, f"inline on* handlers built in JS template literals: {offenders}"


def test_no_javascript_uri_in_templates():
    offenders = {}
    for path in _templates():
        # ignore the string "javascript" used as a language key, e.g. {javascript:'#fff'}
        hits = _JS_URI_RE.findall(open(path, encoding="utf-8").read())
        if hits:
            offenders[_rel(path)] = len(hits)
    assert not offenders, f"javascript: URIs present (blocked by enforced script-src): {offenders}"


def test_every_inline_script_has_a_nonce():
    offenders = {}
    for path in _templates():
        bad = [
            tag
            for tag in _SCRIPT_OPEN_RE.findall(open(path, encoding="utf-8").read())
            if "nonce=" not in tag
        ]
        if bad:
            offenders[_rel(path)] = bad
    assert (
        not offenders
    ), f"un-nonced inline <script> (won't run under enforced script-src): {offenders}"
