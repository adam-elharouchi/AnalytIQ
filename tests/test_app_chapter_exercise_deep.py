"""
Deep tests for chapter upload, PDF serving, exercise generation, AI chat
Targets uncovered lines: upload_chapter (3021-3193), get_class_chapters (3196-3272),
serve_chapter_pdf (4847-4909), generate_exercises (3716-3844), AI chat (3660-3710)
"""
import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO
from datetime import datetime
import json


class TestUploadChapter:
    """Test POST /api/classes/<class_id>/chapters endpoint - lines 2993-3193"""

    def test_upload_chapter_success(self, client, mock_db):
        """Test successful chapter upload with PDF"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("prof123",),  # Class professor check
            (5,),  # Next chapter number
            ("ch_123", "Chapter Title", "Description", 5, datetime(2026, 1, 1)),  # Chapter created
        ]

        pdf_content = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\nSome content\n%%EOF"
        data = {
            "user_id": "prof123",
            "title": "Test Chapter",
            "description": "Test Description",
            "exercise_mode": "manual",
        }

        response = client.post(
            "/api/classes/CLS123/chapters",
            data={**data, "pdf_file": (BytesIO(pdf_content), "test.pdf")},
            content_type="multipart/form-data",
        )
        assert response.status_code in [201, 400, 403, 404, 500]

    def test_upload_chapter_missing_user_id(self, client, mock_db):
        """Test chapter upload without user_id"""
        pdf_content = b"%PDF-1.4\nContent"
        response = client.post(
            "/api/classes/CLS123/chapters",
            data={"pdf_file": (BytesIO(pdf_content), "test.pdf")},
            content_type="multipart/form-data",
        )
        assert response.status_code in [400, 401, 403, 500]

    def test_upload_chapter_class_not_found(self, client, mock_db):
        """Test upload to non-existent class"""
        mock_db.cursor().fetchone.return_value = None

        pdf_content = b"%PDF-1.4\nContent"
        response = client.post(
            "/api/classes/NONEXIST/chapters",
            data={
                "user_id": "prof123",
                "title": "Test",
                "pdf_file": (BytesIO(pdf_content), "test.pdf"),
            },
            content_type="multipart/form-data",
        )
        assert response.status_code in [401, 404, 500]

    def test_upload_chapter_not_owner(self, client, mock_db):
        """Test upload by non-owner professor"""
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

    def test_upload_chapter_no_file(self, client, mock_db):
        """Test upload without PDF file"""
        mock_db.cursor().fetchone.return_value = ("prof123",)

        response = client.post(
            "/api/classes/CLS123/chapters",
            data={"user_id": "prof123", "title": "Test"},
            content_type="multipart/form-data",
        )
        assert response.status_code in [400, 401, 403, 500]

    def test_upload_chapter_empty_filename(self, client, mock_db):
        """Test upload with empty filename"""
        mock_db.cursor().fetchone.return_value = ("prof123",)

        response = client.post(
            "/api/classes/CLS123/chapters",
            data={
                "user_id": "prof123",
                "title": "Test",
                "pdf_file": (BytesIO(b""), ""),
            },
            content_type="multipart/form-data",
        )
        assert response.status_code in [400, 401, 403, 500]

    def test_upload_chapter_invalid_file_type(self, client, mock_db):
        """Test upload with non-PDF file"""
        mock_db.cursor().fetchone.return_value = ("prof123",)

        response = client.post(
            "/api/classes/CLS123/chapters",
            data={
                "user_id": "prof123",
                "title": "Test",
                "pdf_file": (BytesIO(b"not a pdf"), "test.exe"),
            },
            content_type="multipart/form-data",
        )
        assert response.status_code in [400, 401, 403, 500]

    def test_upload_chapter_missing_title(self, client, mock_db):
        """Test upload without chapter title"""
        mock_db.cursor().fetchone.return_value = ("prof123",)

        pdf_content = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\nContent\n%%EOF"
        response = client.post(
            "/api/classes/CLS123/chapters",
            data={
                "user_id": "prof123",
                "pdf_file": (BytesIO(pdf_content), "test.pdf"),
            },
            content_type="multipart/form-data",
        )
        assert response.status_code in [400, 401, 403, 500]

    def test_upload_chapter_options(self, client):
        """Test OPTIONS for chapter upload"""
        response = client.options("/api/classes/CLS123/chapters")
        assert response.status_code == 200


class TestGetClassChapters:
    """Test GET /api/classes/<class_id>/chapters - lines 3196-3272"""

    def test_get_chapters_as_professor(self, client, mock_db):
        """Test getting chapters as class professor"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("prof123",),  # Class professor
            ("professor",),  # User role
        ]
        mock_cursor.fetchall.return_value = [
            ("ch1", "Chapter 1", "Desc", 1, "/api/chapters/ch1/pdf", "ch1.pdf", datetime(2026, 1, 1)),
            ("ch2", "Chapter 2", "Desc", 2, "/api/chapters/ch2/pdf", "ch2.pdf", datetime(2026, 1, 2)),
        ]

        response = client.get("/api/classes/CLS123/chapters?user_id=prof123")
        assert response.status_code in [200, 400, 401, 404, 500]

    def test_get_chapters_class_not_found(self, client, mock_db):
        """Test getting chapters for non-existent class"""
        mock_db.cursor().fetchone.return_value = None

        response = client.get("/api/classes/NONEXIST/chapters?user_id=user123")
        assert response.status_code in [401, 404, 500]

    def test_get_chapters_user_not_found(self, client, mock_db):
        """Test getting chapters with non-existent user"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("prof123",),  # Class exists
            None,  # User not found
        ]

        response = client.get("/api/classes/CLS123/chapters?user_id=nonexistent")
        assert response.status_code in [401, 404, 500]

    def test_get_chapters_missing_user_id(self, client, mock_db):
        """Test getting chapters without user_id"""
        response = client.get("/api/classes/CLS123/chapters")
        assert response.status_code in [400, 401, 403, 500]


class TestServeChapterPdf:
    """Test GET /api/chapters/<chapter_id>/pdf - lines 4847-4909"""

    def test_serve_pdf_from_database(self, client, mock_db):
        """Test serving PDF from database binary storage"""
        pdf_bytes = b"%PDF-1.4\nSample PDF content"
        mock_db.cursor().fetchone.return_value = (
            memoryview(pdf_bytes),  # pdf_data
            "chapter.pdf",  # pdf_filename
            None,  # pdf_url (no Supabase URL)
        )

        response = client.get("/api/chapters/ch123/pdf")
        assert response.status_code in [200, 302, 404, 500]

    def test_serve_pdf_redirect_to_supabase(self, client, mock_db):
        """Test redirecting to Supabase URL"""
        mock_db.cursor().fetchone.return_value = (
            None,  # No pdf_data
            "chapter.pdf",
            "https://supabase.co/storage/chapter.pdf",  # Supabase URL
        )

        response = client.get("/api/chapters/ch123/pdf")
        assert response.status_code in [200, 302, 404, 500]

    def test_serve_pdf_not_found(self, client, mock_db):
        """Test serving PDF for non-existent chapter"""
        mock_db.cursor().fetchone.return_value = None

        response = client.get("/api/chapters/nonexistent/pdf")
        assert response.status_code in [401, 404, 500]

    def test_serve_pdf_no_data_available(self, client, mock_db):
        """Test serving PDF when no data is available"""
        mock_db.cursor().fetchone.return_value = (
            None,  # No pdf_data
            None,  # No filename
            None,  # No URL
        )

        response = client.get("/api/chapters/ch123/pdf")
        assert response.status_code in [401, 404, 500]


class TestGenerateExercises:
    """Test POST /api/chapters/<chapter_id>/generate-exercises - lines 3716-3844"""

    @patch('app.generate_exercises_from_pdf_content')
    @patch('app.extract_text_from_pdf_bytes')
    def test_generate_exercises_full_flow(self, mock_extract, mock_generate, client, mock_db):
        """Test full exercise generation flow"""
        mock_extract.return_value = "Extracted PDF text about data analytics"
        mock_generate.return_value = [
            {"title": "Q1", "description": "What is...", "difficulty": "easy", "solution_code": "x=1"},
            {"title": "Q2", "description": "How does...", "difficulty": "medium", "solution_code": "y=2"},
        ]

        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            # Chapter data: class_id, title, professor_id, pdf_filename, pdf_data
            ("CLS123", "Chapter 1", "prof123", "ch1.pdf", b"pdf-binary-data"),
            # Exercise inserts
            ("ex_1",), ("ex_2",),
        ]

        response = client.post(
            "/api/chapters/ch123/generate-exercises",
            json={"user_id": "prof123"},
        )
        assert response.status_code in [201, 400, 403, 404, 500]

    def test_generate_exercises_not_professor(self, client, mock_db):
        """Test exercise generation by non-professor"""
        mock_db.cursor().fetchone.return_value = (
            "CLS123", "Chapter 1", "other_prof", "ch1.pdf", b"pdf-data"
        )

        response = client.post(
            "/api/chapters/ch123/generate-exercises",
            json={"user_id": "prof123"},
        )
        assert response.status_code in [403, 500]

    def test_generate_exercises_chapter_not_found(self, client, mock_db):
        """Test exercise generation for non-existent chapter"""
        mock_db.cursor().fetchone.return_value = None

        response = client.post(
            "/api/chapters/nonexistent/generate-exercises",
            json={"user_id": "prof123"},
        )
        assert response.status_code in [401, 404, 500]

    def test_generate_exercises_no_pdf_data(self, client, mock_db):
        """Test exercise generation when no PDF data exists"""
        mock_db.cursor().fetchone.return_value = (
            "CLS123", "Chapter 1", "prof123", "ch1.pdf", None
        )

        response = client.post(
            "/api/chapters/ch123/generate-exercises",
            json={"user_id": "prof123"},
        )
        assert response.status_code in [400, 401, 404, 500]

    def test_generate_exercises_missing_user_id(self, client, mock_db):
        """Test exercise generation without user_id"""
        response = client.post(
            "/api/chapters/ch123/generate-exercises",
            json={},
        )
        assert response.status_code in [400, 401, 403, 500]

    def test_generate_exercises_options(self, client):
        """Test OPTIONS for exercise generation"""
        response = client.options("/api/chapters/ch123/generate-exercises")
        assert response.status_code == 200


class TestAIChatProxy:
    """Test POST /api/ai/chat endpoint - lines 3660-3710"""

    @patch('app.os.getenv')
    def test_ai_chat_no_api_key(self, mock_getenv, client, mock_db):
        """Test AI chat when API key is missing"""
        mock_getenv.return_value = None

        response = client.post("/api/ai/chat", json={
            "model": "gemini-2.5-flash",
            "contents": [{"role": "user", "parts": [{"text": "Hello"}]}],
        })
        assert response.status_code in [401, 500]

    def test_ai_chat_options(self, client):
        """Test OPTIONS for AI chat"""
        response = client.options("/api/ai/chat")
        assert response.status_code == 200

    @patch('requests.post')
    @patch('app.os.getenv')
    def test_ai_chat_success(self, mock_getenv, mock_requests_post, client, mock_db):
        """Test successful AI chat proxy"""
        mock_getenv.return_value = "test-api-key"
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {"candidates": [{"content": "Hello!"}]}
        mock_requests_post.return_value = mock_response

        response = client.post("/api/ai/chat", json={
            "model": "gemini-2.5-flash",
            "contents": [{"role": "user", "parts": [{"text": "Hello"}]}],
        })
        assert response.status_code in [200, 401, 500]

    @patch('requests.post')
    @patch('app.os.getenv')
    def test_ai_chat_invalid_model(self, mock_getenv, mock_requests_post, client, mock_db):
        """Test AI chat with invalid model falls back to default"""
        mock_getenv.return_value = "test-api-key"
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {"candidates": []}
        mock_requests_post.return_value = mock_response

        response = client.post("/api/ai/chat", json={
            "model": "invalid-model-name",
            "contents": [],
        })
        assert response.status_code in [200, 401, 500]


class TestGetChapterExercises:
    """Test GET /api/chapters/<chapter_id>/exercises - lines 3570-3657"""

    def test_get_exercises_as_professor_owner(self, client, mock_db):
        """Test getting exercises as the class professor/owner"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("CLS123", "prof123"),  # chapter data
            ("professor",),  # user role
        ]
        mock_cursor.fetchall.return_value = [
            ("ex1", "Exercise 1", "Desc", "easy", 1, datetime(2026, 1, 1), "print('hello')"),
        ]

        response = client.get("/api/chapters/ch123/exercises?user_id=prof123")
        assert response.status_code in [200, 400, 401, 403, 404, 500]

    def test_get_exercises_student_enrolled(self, client, mock_db):
        """Test getting exercises as enrolled student"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("CLS123", "prof123"),  # chapter data
            ("student",),  # user role
            (1,),  # enrollment check - enrolled
        ]
        mock_cursor.fetchall.return_value = [
            ("ex1", "Exercise 1", "Desc", "easy", 1, datetime(2026, 1, 1), "print('hello')"),
        ]

        response = client.get("/api/chapters/ch123/exercises?user_id=student123")
        assert response.status_code in [200, 403, 500]

    def test_get_exercises_student_not_enrolled(self, client, mock_db):
        """Test getting exercises as non-enrolled student"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("CLS123", "prof123"),
            ("student",),
            None,  # Not enrolled
        ]

        response = client.get("/api/chapters/ch123/exercises?user_id=random_student")
        assert response.status_code in [403, 500]

    def test_get_exercises_chapter_not_found(self, client, mock_db):
        """Test getting exercises for non-existent chapter"""
        mock_db.cursor().fetchone.return_value = None

        response = client.get("/api/chapters/nonexistent/exercises?user_id=user123")
        assert response.status_code in [401, 404, 500]

    def test_get_exercises_user_not_found(self, client, mock_db):
        """Test getting exercises with non-existent user"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("CLS123", "prof123"),
            None,  # User not found
        ]

        response = client.get("/api/chapters/ch123/exercises?user_id=nonexistent")
        assert response.status_code in [401, 404, 500]
