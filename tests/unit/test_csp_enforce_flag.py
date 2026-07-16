"""
tests/unit/test_csp_enforce_flag.py — the CSP_ENFORCE toggle (core/factory.py).

script-src enforcement is gated behind config.CSP_ENFORCE so it can be turned on
and reverted from the Render env without a redeploy. Off (default): script-src
stays in Report-Only, enforced policy is just object-src/base-uri. On: script-src
(nonce-based) moves into the enforced Content-Security-Policy.
"""
import re

import config


def _headers(client):
    resp = client.get("/")
    return (
        resp.headers.get("Content-Security-Policy", ""),
        resp.headers.get("Content-Security-Policy-Report-Only", ""),
    )


class TestCspEnforceOff:
    def test_script_src_not_enforced_by_default(self, client, monkeypatch):
        monkeypatch.setattr(config, "CSP_ENFORCE", False)
        enforced, report_only = _headers(client)
        assert "object-src 'none'" in enforced
        assert "base-uri 'self'" in enforced
        assert "script-src" not in enforced
        # It is still monitored in Report-Only, nonce-based, no unsafe-inline.
        assert "script-src 'self' 'nonce-" in report_only
        assert "'unsafe-inline'" not in report_only.split("style-src")[0]


class TestCspEnforceOn:
    def test_script_src_enforced_when_flag_on(self, client, monkeypatch):
        monkeypatch.setattr(config, "CSP_ENFORCE", True)
        enforced, report_only = _headers(client)
        assert "object-src 'none'" in enforced
        assert re.search(r"script-src 'self' 'nonce-[^']+'", enforced), enforced
        assert "https://cdn.jsdelivr.net" in enforced
        # No 'unsafe-inline' and no 'strict-dynamic' in the enforced script-src.
        assert "'unsafe-inline'" not in enforced
        assert "'strict-dynamic'" not in enforced
        # Once enforced, script-src is dropped from Report-Only (no duplication).
        assert "script-src" not in report_only

    def test_enforced_nonce_matches_the_rendered_page(self, client, monkeypatch):
        monkeypatch.setattr(config, "CSP_ENFORCE", True)
        resp = client.get("/")
        enforced = resp.headers.get("Content-Security-Policy", "")
        m = re.search(r"script-src 'self' 'nonce-([^']+)'", enforced)
        assert m, enforced
        nonce = m.group(1)
        # The same nonce must be on the page's inline scripts, or they'd be blocked.
        assert f'<script nonce="{nonce}">' in resp.get_data(as_text=True)
