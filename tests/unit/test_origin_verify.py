"""
tests/unit/test_origin_verify.py — Cloudflare origin-verify middleware (H-6).

When ORIGIN_VERIFY_SECRET is set, requests missing the matching X-Origin-Verify
header are refused (except /api/health). When unset, enforcement is off.
"""


class TestOriginVerify:
    def test_disabled_when_secret_unset(self, client, mock_db, monkeypatch):
        monkeypatch.setattr("config.ORIGIN_VERIFY_SECRET", None)
        assert client.get("/api/platform/status").status_code != 403

    def test_enforced_rejects_missing_header(self, client, mock_db, monkeypatch):
        monkeypatch.setattr("config.ORIGIN_VERIFY_SECRET", "s3cret")
        assert client.get("/api/platform/status").status_code == 403

    def test_enforced_allows_correct_header(self, client, mock_db, monkeypatch):
        monkeypatch.setattr("config.ORIGIN_VERIFY_SECRET", "s3cret")
        r = client.get("/api/platform/status", headers={"X-Origin-Verify": "s3cret"})
        assert r.status_code != 403

    def test_wrong_header_rejected(self, client, mock_db, monkeypatch):
        monkeypatch.setattr("config.ORIGIN_VERIFY_SECRET", "s3cret")
        r = client.get("/api/platform/status", headers={"X-Origin-Verify": "nope"})
        assert r.status_code == 403

    def test_health_is_exempt(self, client, mock_db, monkeypatch):
        # Render's health probe hits the origin directly without the header.
        monkeypatch.setattr("config.ORIGIN_VERIFY_SECRET", "s3cret")
        assert client.get("/api/health").status_code != 403
