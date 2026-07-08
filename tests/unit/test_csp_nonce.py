"""
tests/unit/test_csp_nonce.py — CSP nonce plumbing (Phase 1 of script-src hardening).

Every request gets a fresh nonce that appears BOTH in the Report-Only CSP header
and on every inline <script> tag, so script-src can eventually be enforced without
'unsafe-inline'. The enforced policy stays minimal for now (no script-src) so
nothing breaks while the ~220 inline handlers are still being refactored.
"""
import re


def _nonce_from_header(resp):
    ro = resp.headers.get("Content-Security-Policy-Report-Only", "")
    m = re.search(r"'nonce-([A-Za-z0-9_\-]+)'", ro)
    return m.group(1) if m else None, ro


class TestCspNoncePlumbing:
    def test_report_only_header_carries_a_nonce(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        nonce, ro = _nonce_from_header(resp)
        assert nonce, f"no nonce in Report-Only header: {ro!r}"

    def test_rendered_inline_script_uses_the_same_nonce(self, client):
        # The landing page has an inline <script>; its nonce must match the header.
        resp = client.get("/")
        nonce, _ = _nonce_from_header(resp)
        html = resp.get_data(as_text=True)
        assert f'<script nonce="{nonce}">' in html

    def test_report_only_script_src_drops_unsafe_inline(self, client):
        _, ro = _nonce_from_header(client.get("/"))
        # Isolate the script-src directive and confirm 'unsafe-inline' is gone.
        script_src = next((d for d in ro.split(";") if d.strip().startswith("script-src")), "")
        assert "'unsafe-inline'" not in script_src
        assert "'nonce-" in script_src

    def test_enforced_policy_stays_minimal(self, client):
        resp = client.get("/")
        enforced = resp.headers.get("Content-Security-Policy", "")
        assert "object-src 'none'" in enforced
        assert "base-uri 'self'" in enforced
        # script-src must NOT be enforced yet — inline handlers still exist.
        assert "script-src" not in enforced

    def test_nonce_is_per_request(self, client):
        n1, _ = _nonce_from_header(client.get("/"))
        n2, _ = _nonce_from_header(client.get("/"))
        assert n1 and n2 and n1 != n2
