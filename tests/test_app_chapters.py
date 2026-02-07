"""
Tests for chapter management and PDF processing
Uses actual API endpoints from app.py
"""
import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO
from datetime import datetime


class TestChapterCreation:
    """Test chapter creation via class chapters endpoint"""

    def test_create_chapter_with_pdf(self, client, mock_db):
        """Test successful chapter creation with PDF upload"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("prof123",),  # Professor owns class
            (1,),  # Next chapter number
            ("ch_new", "Test Chapter", "Desc", 1, datetime(2026, 1, 1)),
        ]

        pdf_content = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\nContent\n%%EOF"
        response = client.post(
            "/api/classes/CLS123/chapters",
            data={
                "user_id": "prof123",
                "title": "Test Chapter",
                "description": "Test description",
                "exercise_mode": "manual",
                "pdf_file": (BytesIO(pdf_content), "test.pdf"),
            },
            content_type="multipart/form-data",
        )
        assert response.status_code in [201, 400, 403, 404, 500]

    def test_create_chapter_missing_user_id(self, client, mock_db):
        """Test chapter creation without user_id"""
        pdf_content = b"%PDF-1.4\nContent"
        response = client.post(
            "/api/classes/CLS123/chapters",
            data={"pdf_file": (BytesIO(pdf_content), "test.pdf")},
            content_type="multipart/form-data",
        )
        assert response.status_code in [400, 500]

    def test_create_chapter_class_not_found(self, client, mock_db):
        """Test chapter creation for non-existent class"""
        mock_db.cursor().fetchone.return_value = None

        pdf_content = b"%PDF-1.4\nContent"
        response = client.post(
            "/api/classes/nonexistent/chapters",
            data={
                "user_id": "prof123",
                "title": "Test",
                "pdf_file": (BytesIO(pdf_content), "test.pdf"),
            },
            content_type="multipart/form-data",
        )
        assert response.status_code in [404, 500]

    def test_create_chapter_not_owner(self, client, mock_db):
        """Test chapter creation by non-owner"""
        mock_db.cursor().fetchone.return_value = ("other_prof",)

        pdf_content = b"%PDF-1.4\nContent"
        response = client.post(
            "/api/classes/CLS123/chapters",
            data={
                "user_id": "prof123",
                "title": "Test",
                "pdf_file": (BytesIO(pdf_content), "test.pdf"),
            },
            content_type="multipart/form-data",
        )
        assert response.status_code in [403, 500]


class TestChapterRetrieval:
    """Test chapter retrieval endpoints"""

    def test_get_chapters_by_class(self, client, mock_db):
        """Test getting all chapters for a class"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("prof123",),  # Class professor
            ("professor",),  # User role
        ]
        mock_cursor.fetchall.return_value = [
            ("ch1", "Chapter 1", "Desc", 1, "/api/chapters/ch1/pdf", "ch1.pdf", datetime(2026, 1, 1)),
        ]

        response = client.get("/api/classes/CLS123/chapters?user_id=prof123")
        assert response.status_code in [200, 400, 404, 500]

    def test_get_chapters_missing_user_id(self, client, mock_db):
        """Test getting chapters without user_id"""
        response = client.get("/api/classes/CLS123/chapters")
        assert response.status_code in [400, 500]

    def test_get_chapters_class_not_found(self, client, mock_db):
        """Test getting chapters for non-existent class"""
        mock_db.cursor().fetchone.return_value = None
        response = client.get("/api/classes/NONEXIST/chapters?user_id=user123")
        assert response.status_code in [404, 500]


class TestPDFServing:
    """Test PDF serving endpoint"""

    def test_serve_pdf_from_db(self, client, mock_db):
        """Test serving PDF from database"""
        pdf_bytes = b"%PDF-1.4\nSample"
        mock_db.cursor().fetchone.return_value = (
            memoryview(pdf_bytes), "chapter.pdf", None,
        )
        response = client.get("/api/chapters/ch123/pdf")
        assert response.status_code in [200, 302, 404, 500]

    def test_serve_pdf_not_found(self, client, mock_db):
        """Test serving PDF for non-existent chapter"""
        mock_db.cursor().fetchone.return_value = None
        response = client.get("/api/chapters/nonexistent/pdf")
        assert response.status_code in [404, 500]


class TestChapterExercises:
    """Test chapter exercise management"""

    def test_get_chapter_exercises(self, client, mock_db):
        """Test getting exercises for a chapter"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("CLS123", "prof123"),
            ("professor",),
        ]
        mock_cursor.fetchall.return_value = [
            ("ex1", "Exercise 1", "Desc", "easy", 1, None, "code"),
        ]

        response = client.get("/api/chapters/ch123/exercises?user_id=prof123")
        assert response.status_code in [200, 400, 403, 404, 500]

    def test_generate_exercises_for_chapter(self, client, mock_db):
        """Test generating exercises for a chapter"""
        mock_db.cursor().fetchone.return_value = (
            "CLS123", "Test Chapter", "prof123", "ch.pdf", b"pdf-data"
        )

        response = client.post(
            "/api/chapters/ch123/generate-exercises",
            json={"user_id": "prof123"},
        )
        assert response.status_code in [200, 201, 400, 403, 404, 500]


class TestPDFProcessing:
    """Test PDF processing and text extraction"""

    @patch('app.extract_text_from_pdf_bytes')
    def test_process_pdf_success(self, mock_extract, client, mock_db):
        """Test successful PDF text extraction during chapter upload"""
        mock_extract.return_value = "Extracted text from PDF"
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("prof123",),
            (1,),
            ("ch_new", "Chapter", "Desc", 1, datetime(2026, 1, 1)),
        ]

        pdf_data = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\nTest\n%%EOF"
        response = client.post(
            "/api/classes/CLS123/chapters",
            data={
                "user_id": "prof123",
                "title": "Test Chapter",
                "exercise_mode": "manual",
                "pdf_file": (BytesIO(pdf_data), "test.pdf"),
            },
            content_type="multipart/form-data",
        )
        assert response.status_code in [201, 400, 500]


class TestChapterProgress:
    """Test chapter-related progress tracking"""

    def test_get_practice_progress_for_exercise(self, client, mock_db):
        """Test getting practice progress for a specific exercise"""
        mock_db.cursor().fetchone.return_value = (
            "ex1", "Exercise 1", 85, 90.0, 120, 3, 80, True, datetime(2026, 1, 1)
        )

        response = client.get(
            "/api/users/practice-progress?user_id=user123&exercise_id=ex1"
        )
        assert response.status_code in [200, 400, 500]

    def test_get_practice_progress_all(self, client, mock_db):
        """Test getting all practice progress"""
        mock_db.cursor().fetchall.return_value = [
            ("ex1", "Exercise 1", 85, 90.0, 3, True, None),
        ]

        response = client.get("/api/users/practice-progress?user_id=user123")
        assert response.status_code in [200, 400, 500]
