"""
Comprehensive Tests for Celery Tasks
Target: Increase tasks.py coverage from 24% to 80%+
"""
import pytest
from unittest.mock import patch, MagicMock, Mock
import os


class TestDatabaseTask:
    """Test DatabaseTask base class"""

    def test_get_db_connection_creates_pool(self):
        """Test database connection pool creation"""
        from workers.tasks import DatabaseTask

        task = DatabaseTask()
        
        with patch.dict("os.environ", {"DATABASE_URL": "postgresql://test"}):
            with patch("psycopg2.pool.SimpleConnectionPool") as mock_pool:
                mock_conn = MagicMock()
                mock_pool.return_value.getconn.return_value = mock_conn

                conn = task.get_db_connection()

                assert conn == mock_conn
                mock_pool.assert_called_once()

    def test_get_db_connection_reuses_connection(self):
        """Test that connection is reused"""
        from workers.tasks import DatabaseTask

        task = DatabaseTask()
        
        with patch.dict("os.environ", {"DATABASE_URL": "postgresql://test"}):
            with patch("psycopg2.pool.SimpleConnectionPool") as mock_pool:
                mock_conn = MagicMock()
                mock_pool.return_value.getconn.return_value = mock_conn

                conn1 = task.get_db_connection()
                conn2 = task.get_db_connection()

                assert conn1 == conn2
                # Pool should only be created once
                assert mock_pool.call_count == 1

    def test_get_db_connection_no_url(self):
        """Test error when DATABASE_URL is missing"""
        from workers.tasks import DatabaseTask

        task = DatabaseTask()
        
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                task.get_db_connection()
            assert "DATABASE_URL" in str(exc_info.value)

    def test_close_db_connection(self):
        """Test closing database connection"""
        from workers.tasks import DatabaseTask

        task = DatabaseTask()
        
        with patch.dict("os.environ", {"DATABASE_URL": "postgresql://test"}):
            with patch("psycopg2.pool.SimpleConnectionPool") as mock_pool:
                mock_conn = MagicMock()
                mock_pool.return_value.getconn.return_value = mock_conn

                task.get_db_connection()
                task.close_db_connection()

                mock_pool.return_value.putconn.assert_called_once_with(mock_conn)
                assert task._db_conn is None


class TestProcessPDFTask:
    """Test PDF processing task"""

    def test_process_pdf_success(self):
        """Test successful PDF processing"""
        from workers.tasks import process_pdf_and_extract_text

        pdf_bytes = b"fake pdf content"
        chapter_id = "chapter123"

        with patch("workers.tasks.extract_text_from_pdf_bytes") as mock_extract:
            mock_extract.return_value = "Extracted text from PDF"
            
            with patch.object(process_pdf_and_extract_text, "get_db_connection") as mock_get_conn:
                mock_conn = MagicMock()
                mock_cursor = MagicMock()
                mock_conn.cursor.return_value = mock_cursor
                mock_get_conn.return_value = mock_conn

                result = process_pdf_and_extract_text(pdf_bytes, chapter_id)

                assert result["success"] is True
                assert result["text_length"] > 0
                assert result["chapter_id"] == chapter_id
                mock_cursor.execute.assert_called()

    def test_process_pdf_no_processor(self):
        """Test when PDF processor is not available"""
        from workers.tasks import process_pdf_and_extract_text

        with patch("workers.tasks.extract_text_from_pdf_bytes", None):
            result = process_pdf_and_extract_text(b"pdf bytes", "chapter123")

            assert result["success"] is False
            assert "not available" in result["error"]

    def test_process_pdf_extraction_fails(self):
        """Test when PDF extraction fails"""
        from workers.tasks import process_pdf_and_extract_text

        with patch("workers.tasks.extract_text_from_pdf_bytes") as mock_extract:
            mock_extract.return_value = None  # Extraction failed
            
            with patch.object(process_pdf_and_extract_text, "get_db_connection") as mock_get_conn:
                mock_conn = MagicMock()
                mock_get_conn.return_value = mock_conn

                result = process_pdf_and_extract_text(b"pdf bytes", "chapter123")

                assert result["success"] is False


class TestGenerateExercisesTask:
    """Test exercise generation task"""

    def test_generate_exercises_success(self):
        """Test successful exercise generation"""
        from workers.tasks import generate_exercises_async

        pdf_text = "Sample chapter content"
        chapter_title = "Chapter 1"
        chapter_id = "chapter123"
        class_id = "class123"
        api_key = "test_key"

        mock_exercises = [
            {"title": "Exercise 1", "description": "Test", "difficulty": "easy", "solution_code": "print('test')"}
        ]

        with patch("workers.tasks.generate_exercises_from_pdf_content") as mock_generate:
            mock_generate.return_value = mock_exercises
            
            with patch.object(generate_exercises_async, "get_db_connection") as mock_get_conn:
                mock_conn = MagicMock()
                mock_cursor = MagicMock()
                mock_conn.cursor.return_value = mock_cursor
                mock_get_conn.return_value = mock_conn

                result = generate_exercises_async(pdf_text, chapter_title, chapter_id, class_id, api_key)

                assert result["success"] is True
                assert result["exercise_count"] == 1

    def test_generate_exercises_no_generator(self):
        """Test when exercise generator is not available"""
        from workers.tasks import generate_exercises_async

        with patch("workers.tasks.generate_exercises_from_pdf_content", None):
            result = generate_exercises_async("text", "title", "chapter123", "class123", "key")

            assert result["success"] is False
            assert "not available" in result["error"]

    def test_generate_exercises_api_error(self):
        """Test when API fails and retries are exhausted"""
        from workers.tasks import generate_exercises_async
        from celery.exceptions import MaxRetriesExceededError

        with patch("workers.tasks.generate_exercises_from_pdf_content") as mock_generate:
            mock_generate.side_effect = Exception("API error")
            with patch.object(generate_exercises_async, "retry", side_effect=MaxRetriesExceededError()):
                result = generate_exercises_async("text", "title", "chapter123", "class123", "key")

                assert result["success"] is False
                assert "error" in result


class TestSendEmailTask:
    """Test email sending task"""

    def test_send_email_async_exists(self):
        """Test that send_email_async function exists"""
        from workers.tasks import send_email_async
        
        # Just verify the function exists
        assert callable(send_email_async)



class TestProcessChapterTask:
    """Test chapter processing task"""

    def test_process_chapter_with_pdf(self):
        """Test processing chapter with PDF"""
        from workers.tasks import process_chapter_upload

        with patch("workers.tasks.process_pdf_and_extract_text") as mock_pdf:
            with patch("workers.tasks.generate_exercises_async") as mock_exercises:
                mock_pdf.return_value = {"success": True, "text_length": 1000, "pdf_text": "Sample text"}
                mock_exercises.return_value = {"success": True, "exercise_count": 3}

                result = process_chapter_upload(
                    chapter_id="chapter123",
                    pdf_bytes=b"pdf content",
                    auto_generate_exercises=True,
                    class_id="class123",
                    chapter_title="Chapter 1",
                    api_key="test_key"
                )

                assert result["success"] is True
                assert result["text_extracted"] is True

    def test_process_chapter_without_exercises(self):
        """Test processing chapter without generating exercises"""
        from workers.tasks import process_chapter_upload

        with patch("workers.tasks.process_pdf_and_extract_text") as mock_pdf:
            mock_pdf.return_value = {"success": True, "text_length": 1000, "pdf_text": "Sample text"}

            result = process_chapter_upload(
                chapter_id="chapter123",
                pdf_bytes=b"pdf content",
                auto_generate_exercises=False,
                class_id="class123",
                chapter_title="Chapter 1",
                api_key="test_key"
            )

            assert result["success"] is True
            assert result["text_extracted"] is True
            assert result["exercises_generated"] is False
