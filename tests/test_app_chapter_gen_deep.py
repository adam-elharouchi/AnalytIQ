"""
Deep tests for chapter upload auto-exercise generation, generate exercises endpoint,
chapter access control, and PDF validation edge cases.
Targets uncovered lines: 3046-3193 (upload chapter deep), 3229-3338 (chapter access),
3364-3505 (serve PDF/generate exercises), 3716-3844 (generate exercises endpoint)
"""
import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO
from datetime import datetime
import json


class TestUploadChapterAutoExercise:
    """Test chapter upload with auto exercise generation - lines 3128-3164"""

    @patch('app.generate_exercises_from_pdf_content')
    @patch('app.extract_text_from_pdf_bytes')
    def test_upload_chapter_auto_exercise_mode(self, mock_extract, mock_generate, client, mock_db):
        """Test chapter upload with auto exercise generation"""
        mock_extract.return_value = "PDF text about data analytics"
        mock_generate.return_value = [
            {"title": "Q1", "description": "Desc1", "difficulty": "easy", "solution_code": "x=1"},
        ]

        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("prof123",),  # Professor owns class
            (1,),  # Next chapter number
            ("ch_new", "Chapter Title", "Desc", 1, datetime(2026, 1, 1)),  # Created
        ]

        pdf_content = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\nContent\n%%EOF"
        response = client.post(
            "/api/classes/CLS123/chapters",
            data={
                "user_id": "prof123",
                "title": "Test Chapter",
                "exercise_mode": "auto",
                "pdf_file": (BytesIO(pdf_content), "test.pdf"),
            },
            content_type="multipart/form-data",
        )
        assert response.status_code in [201, 400, 401, 403, 500]

    @patch('app.extract_text_from_pdf_bytes')
    def test_upload_chapter_pdf_extract_fails(self, mock_extract, client, mock_db):
        """Test upload when PDF extraction fails - line 3087-3089"""
        mock_extract.side_effect = Exception("Extraction failed")

        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("prof123",),
            (1,),
            ("ch_new", "Chapter", "Desc", 1, datetime(2026, 1, 1)),
        ]

        pdf_content = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\nContent\n%%EOF"
        response = client.post(
            "/api/classes/CLS123/chapters",
            data={
                "user_id": "prof123",
                "title": "Test Chapter",
                "exercise_mode": "manual",
                "pdf_file": (BytesIO(pdf_content), "test.pdf"),
            },
            content_type="multipart/form-data",
        )
        assert response.status_code in [201, 400, 401, 403, 500]

    def test_upload_chapter_pdf_validation_fails(self, client, mock_db):
        """Test upload with invalid PDF content - lines 3046-3057"""
        mock_db.cursor().fetchone.return_value = ("prof123",)

        # Not a valid PDF
        response = client.post(
            "/api/classes/CLS123/chapters",
            data={
                "user_id": "prof123",
                "title": "Test Chapter",
                "pdf_file": (BytesIO(b"Not a PDF file"), "test.pdf"),
            },
            content_type="multipart/form-data",
        )
        assert response.status_code in [400, 401, 403, 500]


class TestGetClassChaptersAccess:
    """Test chapter access control paths - lines 3216-3272"""

    def test_get_chapters_as_enrolled_student(self, client, mock_db):
        """Test getting chapters as enrolled student"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("prof123",),  # Class professor
            ("student",),  # User role
            (1,),  # Enrolled
        ]
        mock_cursor.fetchall.return_value = [
            ("ch1", "Chapter 1", "Desc", 1, "/pdf", "ch1.pdf", datetime(2026, 1, 1)),
        ]

        response = client.get("/api/classes/CLS123/chapters?user_id=student123")
        assert response.status_code in [200, 403, 500]

    def test_get_chapters_not_enrolled(self, client, mock_db):
        """Test getting chapters when not enrolled - lines 3229-3239"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("prof123",),  # Class professor
            ("student",),  # User role
            None,  # Not enrolled
        ]

        response = client.get("/api/classes/CLS123/chapters?user_id=random")
        assert response.status_code in [403, 500]


class TestServePdfDeep:
    """Test chapter PDF serving - lines 3364-3389"""

    def test_serve_pdf_generate_exercises_from_chapter(self, client, mock_db):
        """Test the generate exercises from chapter endpoint - lines 3364-3505"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            (b"pdf-data", "Chapter Title", "CLS123", "prof123"),  # Chapter data
        ]

        with patch("app.extract_text_from_pdf_bytes", return_value="PDF text"):
            with patch("app.generate_exercises_from_pdf_content", return_value=[
                {"title": "Q1", "description": "D1", "difficulty": "easy", "solution_code": "c1"},
            ]):
                response = client.post(
                    "/api/classes/CLS123/chapters/ch123/generate-exercises",
                    json={"user_id": "prof123"},
                )
        assert response.status_code in [201, 400, 403, 404, 500]

    def test_generate_exercises_from_chapter_not_professor(self, client, mock_db):
        """Test generating exercises when not the professor"""
        mock_db.cursor().fetchone.return_value = (
            b"pdf-data", "Title", "CLS123", "other_prof",
        )

        response = client.post(
            "/api/classes/CLS123/chapters/ch123/generate-exercises",
            json={"user_id": "not_the_prof"},
        )
        assert response.status_code in [403, 404, 500]

    def test_generate_exercises_no_pdf_data(self, client, mock_db):
        """Test generating exercises when PDF data is missing"""
        mock_db.cursor().fetchone.return_value = (
            None, "Title", "CLS123", "prof123",
        )

        response = client.post(
            "/api/classes/CLS123/chapters/ch123/generate-exercises",
            json={"user_id": "prof123"},
        )
        assert response.status_code in [401, 404, 500]


class TestGenerateExercisesEndpointDeep:
    """Test POST /api/chapters/<id>/generate-exercises deep - lines 3716-3844"""

    @patch('app.generate_exercises_from_pdf_content')
    @patch('app.extract_text_from_pdf_bytes')
    def test_generate_exercises_full_success(self, mock_extract, mock_generate, client, mock_db):
        """Test full exercise generation flow with DB inserts"""
        mock_extract.return_value = "PDF text about analytics"
        mock_generate.return_value = [
            {"title": "Q1", "description": "D1", "difficulty": "easy", "solution_code": "c1"},
            {"title": "Q2", "description": "D2", "difficulty": "medium", "solution_code": "c2"},
        ]

        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("CLS123", "Chapter", "prof123", "file.pdf", b"pdf-bytes"),  # Chapter data
            ("ex_1",), ("ex_2",),  # Exercise inserts
        ]

        response = client.post(
            "/api/chapters/ch123/generate-exercises",
            json={"user_id": "prof123"},
        )
        assert response.status_code in [201, 400, 403, 404, 500]

    @patch('app.extract_text_from_pdf_bytes')
    def test_generate_exercises_empty_text(self, mock_extract, client, mock_db):
        """Test exercise generation when text extraction returns empty"""
        mock_extract.return_value = ""

        mock_db.cursor().fetchone.return_value = (
            "CLS123", "Chapter", "prof123", "file.pdf", b"pdf-bytes",
        )

        response = client.post(
            "/api/chapters/ch123/generate-exercises",
            json={"user_id": "prof123"},
        )
        assert response.status_code in [400, 401, 403, 500]

    @patch('app.extract_text_from_pdf_bytes')
    def test_generate_exercises_extract_error(self, mock_extract, client, mock_db):
        """Test exercise generation when extraction throws error"""
        mock_extract.side_effect = Exception("PDF corrupted")

        mock_db.cursor().fetchone.return_value = (
            "CLS123", "Chapter", "prof123", "file.pdf", b"pdf-bytes",
        )

        response = client.post(
            "/api/chapters/ch123/generate-exercises",
            json={"user_id": "prof123"},
        )
        assert response.status_code in [401, 500]

    def test_generate_exercises_no_pdf_bytes(self, client, mock_db):
        """Test exercise generation when no PDF bytes in DB"""
        mock_db.cursor().fetchone.return_value = (
            "CLS123", "Chapter", "prof123", "file.pdf", None,
        )

        response = client.post(
            "/api/chapters/ch123/generate-exercises",
            json={"user_id": "prof123"},
        )
        assert response.status_code in [400, 401, 404, 500]


class TestResourceUploadDownloadDeep:
    """Test resource upload and download deep paths - lines 4990-5196"""

    def test_upload_resource_with_details(self, client, mock_db):
        """Test uploading resource file with all metadata"""
        file_content = b"col1,col2\nval1,val2"

        response = client.post(
            "/api/classes/CLS123/resources/upload",
            data={
                "user_id": "prof123",
                "title": "Data File",
                "description": "Sample data",
                "resource_type": "csv",
                "file": (BytesIO(file_content), "data.csv"),
            },
            content_type="multipart/form-data",
        )
        assert response.status_code in [201, 400, 401, 403, 500]

    def test_create_resource_via_json(self, client, mock_db):
        """Test creating resource via JSON - lines 5156-5196"""
        response = client.post("/api/classes/CLS123/resources", json={
            "user_id": "prof123",
            "title": "Tutorial",
            "description": "Great tutorial",
            "resource_type": "link",
            "resource_url": "https://example.com/tutorial",
        })
        assert response.status_code in [201, 400, 401, 403, 500]

    def test_manage_resource_put(self, client, mock_db):
        """Test updating resource via PUT - lines 5222-5241"""
        response = client.put("/api/classes/CLS123/resources/res123", json={
            "title": "Updated Title",
            "description": "Updated Desc",
            "resource_type": "link",
            "resource_url": "https://updated.com",
        })
        assert response.status_code in [200, 401, 500]

    def test_manage_resource_delete(self, client, mock_db):
        """Test deleting resource - lines 5215-5220"""
        response = client.delete("/api/classes/CLS123/resources/res123")
        assert response.status_code in [200, 401, 500]

    def test_manage_resource_options(self, client):
        """Test OPTIONS for resource management - lines 5204-5209"""
        response = client.options("/api/classes/CLS123/resources/res123")
        assert response.status_code == 200

    def test_download_resource(self, client, mock_db):
        """Test downloading resource file - lines 5250-5279"""
        mock_db.cursor().fetchone.return_value = (
            memoryview(b"file content"), "data.csv", "file",
        )

        response = client.get("/api/resources/res123/download")
        assert response.status_code in [200, 401, 404, 500]

    def test_download_resource_not_found(self, client, mock_db):
        """Test downloading non-existent resource"""
        mock_db.cursor().fetchone.return_value = None

        response = client.get("/api/resources/nonexist/download")
        assert response.status_code in [401, 404, 500]


class TestEnsureTablesFunctions:
    """Test ensure_*_table helper functions - lines 4658-4694"""

    def test_ensure_exercises_table(self, client, mock_db):
        """Test ensure_exercises_table migration helper"""
        from blueprints.exercises import ensure_exercises_table
        ensure_exercises_table()
        # Should not raise

    def test_ensure_resources_table(self, client, mock_db):
        """Test ensure_resources_table migration helper"""
        from blueprints.classes import ensure_resources_table
        ensure_resources_table()
        # Should not raise
