"""
tests/unit/test_media_access.py — Capability-token auth for media endpoints (C-3).

The chapter-PDF and resource-download endpoints are loaded via <iframe>/<a> and
cannot send an Authorization header. They are now protected by a short-lived,
resource-scoped capability token minted by an authenticated access-token
endpoint and passed as ?token=...
"""
from core.auth import create_media_token, verify_media_token

AUTH_PROF = {"X-Test-User-ID": "prof-id", "X-Test-User-Role": "professor"}
AUTH_STUDENT = {"X-Test-User-ID": "student-id", "X-Test-User-Role": "student"}


# ---------------------------------------------------------------------------
# Token helper unit tests
# ---------------------------------------------------------------------------


class TestMediaTokenHelper:
    def test_valid_token_round_trips(self):
        tok = create_media_token("chapter", "ch-1")
        assert verify_media_token(tok, "chapter", "ch-1") is True

    def test_wrong_kind_rejected(self):
        tok = create_media_token("chapter", "ch-1")
        assert verify_media_token(tok, "resource", "ch-1") is False

    def test_wrong_resource_id_rejected(self):
        tok = create_media_token("chapter", "ch-1")
        assert verify_media_token(tok, "chapter", "ch-2") is False

    def test_empty_token_rejected(self):
        assert verify_media_token("", "chapter", "ch-1") is False
        assert verify_media_token("garbage.token.value", "chapter", "ch-1") is False


# ---------------------------------------------------------------------------
# Chapter PDF endpoint
# ---------------------------------------------------------------------------


class TestServeChapterPdf:
    def test_no_token_returns_401(self, client, mock_db):
        resp = client.get("/api/chapters/ch-1/pdf")
        assert resp.status_code == 401

    def test_wrong_token_returns_401(self, client, mock_db):
        bad = create_media_token("chapter", "other-chapter")
        resp = client.get(f"/api/chapters/ch-1/pdf?token={bad}")
        assert resp.status_code == 401

    def test_valid_token_serves_pdf(self, client, mock_db):
        # get_chapter_pdf → (pdf_bytes, filename, pdf_url=None)
        mock_db.cursor().fetchone.return_value = (b"%PDF-1.4 test", "chapter.pdf", None)
        tok = create_media_token("chapter", "ch-1")
        resp = client.get(f"/api/chapters/ch-1/pdf?token={tok}")
        assert resp.status_code == 200
        assert resp.mimetype == "application/pdf"


class TestChapterAccessToken:
    def test_owner_gets_token(self, client, mock_db):
        # get_chapter_class_info → (class_id, professor_id)
        mock_db.cursor().fetchone.return_value = ("class-1", "prof-id")
        resp = client.get("/api/chapters/ch-1/access-token", headers=AUTH_PROF)
        assert resp.status_code == 200
        token = resp.get_json()["token"]
        assert verify_media_token(token, "chapter", "ch-1") is True

    def test_non_enrolled_student_denied(self, client, mock_db):
        # get_chapter_class_info → (class_id, prof-id); check_enrollment → None
        mock_db.cursor().fetchone.side_effect = [("class-1", "prof-id"), None]
        resp = client.get("/api/chapters/ch-1/access-token", headers=AUTH_STUDENT)
        assert resp.status_code == 403

    def test_no_auth_returns_401(self, client, mock_db):
        resp = client.get("/api/chapters/ch-1/access-token")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Resource download endpoint
# ---------------------------------------------------------------------------


class TestServeResourceDownload:
    def test_no_token_returns_401(self, client, mock_db):
        resp = client.get("/api/resources/res-1/download")
        assert resp.status_code == 401

    def test_valid_token_serves_file(self, client, mock_db):
        # get_resource_file → (file_data, filename, resource_type)
        mock_db.cursor().fetchone.return_value = (b"hello", "notes.txt", "file")
        tok = create_media_token("resource", "res-1")
        resp = client.get(f"/api/resources/res-1/download?token={tok}")
        assert resp.status_code == 200


class TestServeResourceFileLegacy:
    def test_no_auth_returns_401(self, client, mock_db):
        resp = client.get("/api/resources/files/something.pdf")
        assert resp.status_code == 401
