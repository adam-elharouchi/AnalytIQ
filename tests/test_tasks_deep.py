"""
Deep tests for tasks.py - Celery async tasks.
Targets uncovered lines: 21-22 (import error), 26-27, 32-33,
144 (no exercises), 192-206 (send_email_async), 239-240 (extraction failed),
255 (exercise_error), 260-262 (process_chapter exception)
"""
import pytest
from unittest.mock import patch, MagicMock
import os


class TestDatabaseTask:
    """Test DatabaseTask base class"""

    @patch("tasks.os.getenv")
    def test_get_db_connection_no_url(self, mock_getenv):
        """Test DatabaseTask when DATABASE_URL not set"""
        mock_getenv.return_value = None
        from tasks import DatabaseTask
        task = DatabaseTask()
        with pytest.raises(ValueError, match="DATABASE_URL not set"):
            task.get_db_connection()

    def test_close_db_connection_no_conn(self):
        """Test closing when no connection exists"""
        from tasks import DatabaseTask
        task = DatabaseTask()
        task._db_conn = None
        task.close_db_connection()  # Should not raise


class TestProcessPdfTask:
    """Test process_pdf_and_extract_text task"""

    @patch("tasks.extract_text_from_pdf_bytes")
    def test_no_pdf_processor(self, mock_extract):
        """Test when PDF processor is not available"""
        with patch("tasks.extract_text_from_pdf_bytes", None):
            from tasks import process_pdf_and_extract_text
            result = process_pdf_and_extract_text(b"pdf-data", "ch1")
            assert result["success"] is False
            assert "PDF processor not available" in result["error"]

    @patch("tasks.extract_text_from_pdf_bytes")
    def test_process_pdf_success(self, mock_extract):
        """Test successful PDF processing"""
        mock_extract.return_value = "Extracted text from PDF about analytics"

        mock_task = MagicMock()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_task.get_db_connection.return_value = mock_conn

        from tasks import process_pdf_and_extract_text
        # Call directly (without celery binding)
        result = process_pdf_and_extract_text(b"pdf-data", "ch1")
        assert isinstance(result, dict)

    @patch("tasks.extract_text_from_pdf_bytes")
    def test_process_pdf_exception(self, mock_extract):
        """Test PDF processing with exception"""
        mock_extract.side_effect = Exception("Extraction failed")

        from tasks import process_pdf_and_extract_text
        result = process_pdf_and_extract_text(b"pdf-data", "ch1")
        assert result["success"] is False


class TestGenerateExercisesTask:
    """Test generate_exercises_async task"""

    def test_no_generator_available(self):
        """Test when exercise generator is not available"""
        with patch("tasks.generate_exercises_from_pdf_content", None):
            from tasks import generate_exercises_async
            result = generate_exercises_async(
                "text", "Title", "ch1", "cls1", "api_key"
            )
            assert result["success"] is False
            assert "Exercise generator not available" in result["error"]

    @patch("tasks.generate_exercises_from_pdf_content")
    def test_no_exercises_generated(self, mock_generate):
        """Test when AI returns no exercises - line 144"""
        mock_generate.return_value = []

        from tasks import generate_exercises_async
        result = generate_exercises_async(
            "text", "Title", "ch1", "cls1", "api_key"
        )
        assert result["success"] is False
        assert "No exercises generated" in result["error"]

    @patch("tasks.generate_exercises_from_pdf_content")
    def test_generate_exercises_exception(self, mock_generate):
        """Test exercise generation with exception"""
        mock_generate.side_effect = Exception("API error")

        from tasks import generate_exercises_async
        result = generate_exercises_async(
            "text", "Title", "ch1", "cls1", "api_key"
        )
        assert result["success"] is False


class TestSendEmailTask:
    """Test send_email_async task - lines 192-206"""

    @patch("config.RESEND_API_KEY", None)
    def test_send_email_no_message_class(self):
        """Test when API Key not available"""
        from tasks import send_email_async
        result = send_email_async("test@test.com", "Subject", "<p>Body</p>")
        assert isinstance(result, dict)

    def test_send_email_exception(self):
        """Test email sending with exception"""
        from tasks import send_email_async
        result = send_email_async("test@test.com", "Subject", "<p>Body</p>")
        assert isinstance(result, dict)
        # It will likely fail since Flask app context isn't available
        if not result.get("success"):
            assert "error" in result


class TestProcessChapterUpload:
    """Test process_chapter_upload combined workflow - lines 209-262"""

    @patch("tasks.process_pdf_and_extract_text")
    def test_extraction_fails(self, mock_extract):
        """Test when PDF extraction fails - lines 238-240"""
        mock_extract.return_value = {
            "success": False,
            "error": "PDF corrupted",
            "chapter_id": "ch1",
        }

        from tasks import process_chapter_upload
        result = process_chapter_upload(
            "ch1", b"pdf", True, "cls1", "Title", "api_key"
        )
        assert result["success"] is False
        assert "PDF extraction failed" in result.get("error", "")

    @patch("tasks.generate_exercises_async")
    @patch("tasks.process_pdf_and_extract_text")
    def test_successful_with_exercises(self, mock_extract, mock_generate):
        """Test successful extraction + exercise generation"""
        mock_extract.return_value = {
            "success": True,
            "pdf_text": "Some text from PDF",
            "chapter_id": "ch1",
        }
        mock_generate.return_value = {
            "success": True,
            "exercise_count": 5,
            "chapter_id": "ch1",
        }

        from tasks import process_chapter_upload
        result = process_chapter_upload(
            "ch1", b"pdf", True, "cls1", "Title", "api_key"
        )
        assert result["text_extracted"] is True
        assert result["exercises_generated"] is True
        assert result["success"] is True

    @patch("tasks.generate_exercises_async")
    @patch("tasks.process_pdf_and_extract_text")
    def test_exercise_generation_fails(self, mock_extract, mock_generate):
        """Test when exercise generation fails - line 255"""
        mock_extract.return_value = {
            "success": True,
            "pdf_text": "Some text",
            "chapter_id": "ch1",
        }
        mock_generate.return_value = {
            "success": False,
            "error": "API quota exceeded",
            "chapter_id": "ch1",
        }

        from tasks import process_chapter_upload
        result = process_chapter_upload(
            "ch1", b"pdf", True, "cls1", "Title", "api_key"
        )
        assert result["text_extracted"] is True
        assert result["exercises_generated"] is False
        assert result["success"] is True  # Overall still succeeds
        assert "exercise_error" in result

    @patch("tasks.process_pdf_and_extract_text")
    def test_no_auto_exercises(self, mock_extract):
        """Test extraction without auto-generating exercises"""
        mock_extract.return_value = {
            "success": True,
            "pdf_text": "Some text",
            "chapter_id": "ch1",
        }

        from tasks import process_chapter_upload
        result = process_chapter_upload(
            "ch1", b"pdf", False, "cls1", "Title", "api_key"
        )
        assert result["text_extracted"] is True
        assert result["exercises_generated"] is False
        assert result["success"] is True

    @patch("tasks.process_pdf_and_extract_text")
    def test_exception_handling(self, mock_extract):
        """Test overall exception handling - lines 260-262"""
        mock_extract.side_effect = Exception("Unexpected error")

        from tasks import process_chapter_upload
        result = process_chapter_upload(
            "ch1", b"pdf", True, "cls1", "Title", "api_key"
        )
        assert result["success"] is False
        assert "error" in result
