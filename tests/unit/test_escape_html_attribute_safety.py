"""
tests/unit/test_escape_html_attribute_safety.py — guard for the escapeHtml XSS fix.

escapeHtml() is implemented as `div.textContent = text; return div.innerHTML`,
which escapes & < > but NOT quotes. Every dashboard embeds its result inside a
double-quoted HTML attribute, e.g.

    onclick="window.tenantAdminApp.openUserModal('${safeId}','${safeName}')"

so a display name of `x" onmouseover="alert(1)` broke out of the attribute and
injected a new event handler — stored XSS against admins, reachable because any
user can self-edit their own name. (Verified in a browser before the fix:
the rendered row gained a real onmouseover attribute.)

The fix appends .replace(/"/g, '&quot;') to every escapeHtml definition, which
renders the payload inert as plain string data. Single quotes are deliberately
left literal: call sites building a JS string still apply their own
.replace(/'/g, "\\'") for that context, and turning ' into &#39; here would
break those strings once the browser decodes the attribute.

This test pins the fix in every copy of the helper (they are duplicated globals).
"""
import os
import re

_JS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "static", "js"))

_DEF_RE = re.compile(r"function\s+escapeHtml\s*\([^)]*\)\s*\{(.*?)\n\}", re.DOTALL)


def _definitions():
    found = {}
    for name in sorted(os.listdir(_JS)):
        if not name.endswith(".js"):
            continue
        with open(os.path.join(_JS, name), encoding="utf-8") as fh:
            src = fh.read()
        for body in _DEF_RE.findall(src):
            found.setdefault(name, []).append(body)
    return found


def test_escape_html_definitions_exist():
    # If the helper is ever renamed/removed, this guard must be revisited.
    assert _definitions(), "no escapeHtml definitions found — update this guard"


def test_every_escape_html_escapes_double_quotes():
    offenders = [
        name for name, bodies in _definitions().items() for body in bodies if "&quot;" not in body
    ]
    assert not offenders, (
        "escapeHtml must escape double quotes or user-controlled text can break out "
        f"of the attributes it is embedded in (stored XSS): {offenders}"
    )


def test_escape_html_does_not_entity_encode_single_quotes():
    # Call sites embed the result in a single-quoted JS string inside the
    # attribute and escape ' themselves; encoding it here would break them.
    offenders = [
        name
        for name, bodies in _definitions().items()
        for body in bodies
        if "&#39;" in body or "&apos;" in body
    ]
    assert not offenders, f"escapeHtml must leave single quotes literal: {offenders}"
