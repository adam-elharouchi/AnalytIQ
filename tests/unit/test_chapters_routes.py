"""
tests/test_chapters_routes.py — Behavioral tests for chapter routes.

Covers:
  GET  /api/chapters/upload-url
  POST /api/classes/<class_id>/chapters              (upload chapter)
  GET  /api/classes/<class_id>/chapters              (list chapters)
  PUT  /api/chapters/<chapter_id>                    (update chapter)
  DELETE /api/chapters/<chapter_id>                  (delete chapter)
  POST /api/chapters/<chapter_id>/generate-exercises
  GET  /api/chapters/<chapter_id>/exercises
  POST /api/classes/<class_id>/chapters/<chapter_id>/exercises  (create exercise)
"""
import pytest
import io
from datetime import datetime
from unittest.mock import patch, MagicMock

AUTH_STUDENT = {"X-Test-User-ID": "student-user-id", "X-Test-User-Role": "student"}
AUTH_PROF = {"X-Test-User-ID": "prof-user-id", "X-Test-User-Role": "professor"}


# ---------------------------------------------------------------------------
# GET /api/chapters/upload-url — presigned upload URL
# ---------------------------------------------------------------------------

class TestGetUploadUrl:
    def test_returns_upload_url_and_storage_path(self, client, mock_db):
        """Authenticated user gets presigned upload URL and storage_path."""
        with patch("core.storage.get_presigned_upload_url") as mock_presigned:
            mock_presigned.return_value = {"signedURL": "https://supabase.example.com/upload"}

            resp = client.get(
                "/api/chapters/upload-url?filename=lecture.pdf",
                headers=AUTH_PROF,
            )

        assert resp.status_code == 200
        data = resp.get_json()
        assert "upload_url" in data
        assert "storage_path" in data

    def test_returns_503_when_storage_unavailable(self, client, mock_db):
        """When storage returns None, endpoint returns 503."""
        with patch("core.storage.get_presigned_upload_url") as mock_presigned:
            mock_presigned.return_value = None

            resp = client.get(
                "/api/chapters/upload-url",
                headers=AUTH_PROF,
            )

        assert resp.status_code == 503
        assert "error" in resp.get_json()

    def test_no_auth_returns_401(self, client, mock_db):
        """Unauthenticated request returns 401."""
        resp = client.get("/api/chapters/upload-url")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /api/classes/<class_id>/chapters — upload chapter
# ---------------------------------------------------------------------------

def _make_pdf_bytes():
    """Minimal valid PDF-like bytes for test uploads."""
    return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n%%EOF"


class TestUploadChapter:
    def test_upload_chapter_not_owner_returns_403(self, client, mock_db):
        """Non-owner professor cannot upload chapters to a class."""
        cursor = mock_db.cursor()
        # get_class_owner -> different owner
        cursor.fetchone.return_value = ("different-prof-id",)

        pdf_bytes = _make_pdf_bytes()
        data = {
            "title": "Chapter 1",
            "description": "First chapter",
            "exercise_mode": "none",
        }
        resp = client.post(
            "/api/classes/class-abc/chapters",
            headers=AUTH_PROF,
            data={**data, "pdf_file": (io.BytesIO(pdf_bytes), "lecture.pdf")},
            content_type="multipart/form-data",
        )

        assert resp.status_code == 403

    def test_upload_chapter_class_not_found_returns_404(self, client, mock_db):
        """Uploading to non-existent class returns 404."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None  # class not found

        pdf_bytes = _make_pdf_bytes()
        resp = client.post(
            "/api/classes/nonexistent/chapters",
            headers=AUTH_PROF,
            data={"title": "Ch1", "pdf_file": (io.BytesIO(pdf_bytes), "test.pdf")},
            content_type="multipart/form-data",
        )

        assert resp.status_code == 404

    def test_upload_chapter_no_file_returns_400(self, client, mock_db):
        """Request without a file returns 400."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = ("prof-user-id",)  # owner

        resp = client.post(
            "/api/classes/class-abc/chapters",
            headers=AUTH_PROF,
            json={"title": "Chapter 1"},
        )

        assert resp.status_code == 400

    def test_upload_chapter_no_title_returns_400(self, client, mock_db):
        """Request without title returns 400."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = ("prof-user-id",)

        pdf_bytes = _make_pdf_bytes()
        resp = client.post(
            "/api/classes/class-abc/chapters",
            headers=AUTH_PROF,
            data={"pdf_file": (io.BytesIO(pdf_bytes), "lecture.pdf")},
            content_type="multipart/form-data",
        )

        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_upload_chapter_success_returns_201(self, client, mock_db):
        """Owner uploads valid PDF and gets 201 with chapter data."""
        cursor = mock_db.cursor()
        cursor.fetchone.side_effect = [
            ("prof-user-id",),  # get_class_owner
            (1,),               # get_next_chapter_number
            ("ch-id", "Chapter 1", "Desc", 1, datetime.now()),  # insert_chapter
        ]

        pdf_bytes = _make_pdf_bytes()
        mock_extractor = MagicMock()
        mock_extractor.extract_text.return_value = "some text"
        with patch("blueprints.chapters.content_extractor", mock_extractor), \
             patch("blueprints.chapters.generate_exercises_from_pdf_content", return_value=None):
            resp = client.post(
                "/api/classes/class-abc/chapters",
                headers=AUTH_PROF,
                data={
                    "title": "Chapter 1",
                    "exercise_mode": "none",
                    "pdf_file": (io.BytesIO(pdf_bytes), "lecture.pdf"),
                },
                content_type="multipart/form-data",
            )

        assert resp.status_code == 201
        data = resp.get_json()
        assert "chapter_id" in data
        assert data["success"] is True


# ---------------------------------------------------------------------------
# GET /api/classes/<class_id>/chapters — list chapters
# ---------------------------------------------------------------------------

class TestGetClassChapters:
    def test_owner_gets_chapters_list(self, client, mock_db):
        """Class owner gets list of chapters."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = ("prof-user-id",)  # owner
        cursor.fetchall.return_value = [
            ("ch-1", "Chapter 1", "Desc", 1, "/api/chapters/ch-1/pdf", "ch-1.pdf", datetime.now()),
        ]

        resp = client.get("/api/classes/class-abc/chapters", headers=AUTH_PROF)

        assert resp.status_code == 200
        data = resp.get_json()
        assert "chapters" in data
        assert len(data["chapters"]) == 1
        assert "chapter_id" in data["chapters"][0]
        assert "title" in data["chapters"][0]

    def test_unenrolled_student_gets_403(self, client, mock_db):
        """Student not enrolled in class is denied."""
        cursor = mock_db.cursor()
        cursor.fetchone.side_effect = [
            ("other-prof-id",),  # class exists but owner is different
            None,                # check_enrollment -> not enrolled
        ]

        resp = client.get("/api/classes/class-abc/chapters", headers=AUTH_STUDENT)

        assert resp.status_code == 403

    def test_class_not_found_returns_404(self, client, mock_db):
        """Non-existent class returns 404."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None

        resp = client.get("/api/classes/nonexistent/chapters", headers=AUTH_PROF)

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/chapters/<chapter_id> — update chapter
# ---------------------------------------------------------------------------

class TestUpdateChapter:
    def test_update_chapter_owner_returns_200(self, client, mock_db):
        """Professor who owns the class can update a chapter."""
        cursor = mock_db.cursor()
        # get_chapter_for_delete returns (class_id, chapter_number, professor_id)
        cursor.fetchone.return_value = ("class-abc", 1, "prof-user-id")

        resp = client.put(
            "/api/chapters/ch-1",
            headers=AUTH_PROF,
            json={"title": "Updated Title"},
        )

        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_update_chapter_non_owner_returns_403(self, client, mock_db):
        """Non-owner cannot update chapter."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = ("class-abc", 1, "different-prof-id")

        resp = client.put(
            "/api/chapters/ch-1",
            headers=AUTH_PROF,
            json={"title": "Hacked Title"},
        )

        assert resp.status_code == 403

    def test_update_chapter_not_found_returns_404(self, client, mock_db):
        """Non-existent chapter returns 404."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None

        resp = client.put(
            "/api/chapters/nonexistent",
            headers=AUTH_PROF,
            json={"title": "X"},
        )

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/chapters/<chapter_id> — delete chapter
# ---------------------------------------------------------------------------

class TestDeleteChapter:
    def test_delete_chapter_owner_returns_200(self, client, mock_db):
        """Chapter owner can delete chapter."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = ("class-abc", 1, "prof-user-id")

        resp = client.delete("/api/chapters/ch-1", headers=AUTH_PROF)

        assert resp.status_code == 200

    def test_delete_chapter_non_owner_returns_403(self, client, mock_db):
        """Non-owner cannot delete chapter."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = ("class-abc", 1, "different-prof-id")

        resp = client.delete("/api/chapters/ch-1", headers=AUTH_PROF)

        assert resp.status_code == 403

    def test_delete_chapter_not_found_returns_404(self, client, mock_db):
        """Non-existent chapter returns 404."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None

        resp = client.delete("/api/chapters/nonexistent", headers=AUTH_PROF)

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/chapters/<chapter_id>/generate-exercises
# ---------------------------------------------------------------------------

class TestGenerateExercises:
    def test_generate_exercises_not_owner_returns_403(self, client, mock_db):
        """Only the class professor can generate exercises."""
        cursor = mock_db.cursor()
        # get_chapter_pdf_data -> (pdf_data, title, class_id, professor_id)
        cursor.fetchone.return_value = (b"fake-pdf", "Chapter 1", "class-abc", "different-prof-id")

        resp = client.post(
            "/api/chapters/ch-1/generate-exercises",
            headers=AUTH_PROF,
            json={},
        )

        assert resp.status_code == 403

    def test_generate_exercises_chapter_not_found_returns_404(self, client, mock_db):
        """Non-existent chapter returns 404."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None

        resp = client.post(
            "/api/chapters/nonexistent/generate-exercises",
            headers=AUTH_PROF,
            json={},
        )

        assert resp.status_code == 404

    def test_generate_exercises_no_pdf_data_returns_404(self, client, mock_db):
        """Chapter with no PDF data returns 404."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (None, "Chapter 1", "class-abc", "prof-user-id")

        resp = client.post(
            "/api/chapters/ch-1/generate-exercises",
            headers=AUTH_PROF,
            json={},
        )

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/chapters/<chapter_id>/exercises — list exercises
# ---------------------------------------------------------------------------

class TestGetChapterExercises:
    def test_owner_gets_exercises_list(self, client, mock_db):
        """Chapter owner gets list of exercises."""
        cursor = mock_db.cursor()
        # get_chapter_class_info -> (class_id, professor_id)
        cursor.fetchone.return_value = ("class-abc", "prof-user-id")
        cursor.fetchall.return_value = [
            ("ex-1", "Ex Title", "Description", "medium", 1, datetime.now(), "print('hi')"),
        ]

        resp = client.get("/api/chapters/ch-1/exercises", headers=AUTH_PROF)

        assert resp.status_code == 200
        data = resp.get_json()
        assert "exercises" in data
        assert len(data["exercises"]) == 1
        assert "exercise_id" in data["exercises"][0]
        assert "title" in data["exercises"][0]

    def test_chapter_not_found_returns_404(self, client, mock_db):
        """Non-existent chapter returns 404."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None

        resp = client.get("/api/chapters/nonexistent/exercises", headers=AUTH_PROF)

        assert resp.status_code == 404

    def test_unenrolled_student_gets_403(self, client, mock_db):
        """Unenrolled student cannot view chapter exercises."""
        cursor = mock_db.cursor()
        cursor.fetchone.side_effect = [
            ("class-abc", "other-prof-id"),  # chapter exists, different owner
            None,                             # check_enrollment -> not enrolled
        ]

        resp = client.get("/api/chapters/ch-1/exercises", headers=AUTH_STUDENT)

        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /api/classes/<class_id>/chapters/<chapter_id>/exercises — create exercise
# ---------------------------------------------------------------------------

class TestCreateExercise:
    def test_create_exercise_owner_returns_201(self, client, mock_db):
        """Professor creates an exercise manually — 201 with exercise_id."""
        cursor = mock_db.cursor()
        cursor.fetchone.side_effect = [
            ("prof-user-id",),  # get_class_owner
            ("ch-1",),          # chapter_belongs_to_class
        ]

        resp = client.post(
            "/api/classes/class-abc/chapters/ch-1/exercises",
            headers=AUTH_PROF,
            json={
                "title": "Write a loop",
                "description": "Print 1 to 10",
                "difficulty": "easy",
                "solution_code": "for i in range(1, 11): print(i)",
            },
        )

        assert resp.status_code == 201
        data = resp.get_json()
        assert data["success"] is True
        assert "exercise_id" in data

    def test_create_exercise_non_owner_returns_403(self, client, mock_db):
        """Non-owner cannot create exercises in a class."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = ("different-prof-id",)  # get_class_owner

        resp = client.post(
            "/api/classes/class-abc/chapters/ch-1/exercises",
            headers=AUTH_PROF,
            json={"title": "Exercise", "description": "Desc"},
        )

        assert resp.status_code == 403

    def test_create_exercise_class_not_found_returns_404(self, client, mock_db):
        """Non-existent class returns 404."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None  # class not found

        resp = client.post(
            "/api/classes/nonexistent/chapters/ch-1/exercises",
            headers=AUTH_PROF,
            json={"title": "Exercise", "description": "Desc"},
        )

        assert resp.status_code == 404
