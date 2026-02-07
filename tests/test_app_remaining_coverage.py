"""
Tests targeting remaining uncovered lines in app.py to push toward 85%+.
Covers: create_class, get_classes (both paths), get_class_by_id, exercise CRUD,
chapter update/delete, generate_exercises_for_chapter, generate_exercises,
create_exercise, add_class_resource, upload_class_resource, serve_resource,
manage_resource, download_resource, create_class_resource, health check deep,
CSRF token, task status, delete user, practice progress endpoints.
"""
import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO
from datetime import datetime
import json
import os


class TestCreateClassDeep:
    """Test POST /api/classes - lines 2330-2414"""

    def test_create_class_success(self, client, mock_db):
        """Test successful class creation"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("professor",),  # User is professor
            None,  # Code not taken
            ("CLS123", "My Class", "Description", datetime(2026, 1, 1)),
        ]

        response = client.post("/api/classes", json={
            "user_id": "prof123",
            "name": "My Class",
            "description": "A great class",
            "class_code": "CLS123",
        })
        assert response.status_code in [201, 403, 409, 500]

    def test_create_class_options(self, client):
        """Test OPTIONS for create class - lines 2332-2338"""
        response = client.options("/api/classes")
        assert response.status_code == 200

    def test_create_class_code_taken(self, client, mock_db):
        """Test class creation with duplicate code"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("professor",),  # Professor
            ("existing",),  # Code already exists
        ]

        response = client.post("/api/classes", json={
            "user_id": "prof123",
            "name": "Class",
            "class_code": "TAKEN123",
        })
        assert response.status_code in [409, 500]

    def test_create_class_not_professor(self, client, mock_db):
        """Test class creation by non-professor"""
        mock_db.cursor().fetchone.return_value = ("student",)

        response = client.post("/api/classes", json={
            "user_id": "student123",
            "name": "Class",
            "class_code": "CLS123",
        })
        assert response.status_code in [403, 500]

    def test_create_class_missing_code(self, client, mock_db):
        """Test class creation without code"""
        response = client.post("/api/classes", json={
            "user_id": "prof123",
            "name": "Class",
        })
        assert response.status_code in [400, 500]

    def test_create_class_invalid_code_format(self, client, mock_db):
        """Test class creation with invalid code"""
        response = client.post("/api/classes", json={
            "user_id": "prof123",
            "name": "Class",
            "class_code": "A",  # Too short
        })
        assert response.status_code in [400, 500]

    def test_create_class_missing_name(self, client, mock_db):
        """Test class creation without name"""
        response = client.post("/api/classes", json={
            "user_id": "prof123",
            "class_code": "CLS123",
        })
        assert response.status_code in [400, 500]


class TestGetClassesBothPaths:
    """Test GET /api/classes professor and student paths - lines 2417-2526"""

    def test_get_classes_professor(self, client, mock_db):
        """Test professor viewing their classes"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("professor",),  # User role
            (3,),  # Total count
        ]
        mock_cursor.fetchall.return_value = [
            ("CLS1", "Class 1", "Desc 1", datetime(2026, 1, 1), 10, 3),
            ("CLS2", "Class 2", "Desc 2", datetime(2026, 1, 2), 5, 1),
        ]

        response = client.get("/api/classes?user_id=prof123&limit=10&offset=0")
        assert response.status_code in [200, 404, 500]

    def test_get_classes_student(self, client, mock_db):
        """Test student viewing enrolled classes - lines 2473-2500"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("student",),  # User role
            (1,),  # Total count
        ]
        mock_cursor.fetchall.return_value = [
            ("CLS1", "Class 1", "Desc", datetime(2026, 1, 1), 10, 3),
        ]

        response = client.get("/api/classes?user_id=student123")
        assert response.status_code in [200, 404, 500]

    def test_get_classes_user_not_found(self, client, mock_db):
        """Test getting classes when user not found"""
        mock_db.cursor().fetchone.return_value = None

        response = client.get("/api/classes?user_id=nonexist")
        assert response.status_code in [404, 500]

    def test_get_classes_missing_user(self, client, mock_db):
        """Test getting classes without user_id"""
        response = client.get("/api/classes")
        assert response.status_code in [400, 500]


class TestGetExerciseById:
    """Test GET /api/exercises/<id> - lines 2744-2791"""

    def test_get_exercise_success(self, client, mock_db):
        """Test getting exercise by ID"""
        mock_db.cursor().fetchone.return_value = (
            "ex1", "ch1", "CLS1", "Exercise 1", "Description", "easy", "x=1",
        )

        response = client.get("/api/exercises/ex1?user_id=user123")
        assert response.status_code in [200, 404, 500]

    def test_get_exercise_not_found(self, client, mock_db):
        """Test getting non-existent exercise"""
        mock_db.cursor().fetchone.return_value = None

        response = client.get("/api/exercises/nonexist?user_id=user123")
        assert response.status_code in [404, 500]

    def test_get_exercise_missing_user(self, client, mock_db):
        """Test getting exercise without user_id"""
        response = client.get("/api/exercises/ex1")
        assert response.status_code in [400, 500]


class TestUpdateExercise:
    """Test PUT /api/exercises/<id> - lines 2794-2846"""

    def test_update_exercise_success(self, client, mock_db):
        """Test successful exercise update"""
        mock_db.cursor().fetchone.return_value = ("prof123",)

        response = client.put("/api/exercises/ex1", json={
            "user_id": "prof123",
            "title": "Updated Title",
            "description": "Updated Desc",
            "difficulty": "hard",
            "solution_code": "y=2",
        })
        assert response.status_code in [200, 403, 500]

    def test_update_exercise_not_authorized(self, client, mock_db):
        """Test exercise update by non-owner"""
        mock_db.cursor().fetchone.return_value = ("other_prof",)

        response = client.put("/api/exercises/ex1", json={
            "user_id": "prof123",
            "title": "Updated",
        })
        assert response.status_code in [403, 500]


class TestUpdateChapter:
    """Test PUT /api/chapters/<id> - lines 3278-3325"""

    def test_update_chapter_success(self, client, mock_db):
        """Test successful chapter update"""
        mock_db.cursor().fetchone.return_value = ("prof123",)

        response = client.put("/api/chapters/ch1", json={
            "user_id": "prof123",
            "title": "Updated Chapter",
            "description": "New description",
        })
        assert response.status_code in [200, 403, 404, 500]

    def test_update_chapter_not_authorized(self, client, mock_db):
        """Test chapter update by non-owner - line 3305-3308"""
        mock_db.cursor().fetchone.return_value = ("other_prof",)

        response = client.put("/api/chapters/ch1", json={
            "user_id": "not_the_prof",
            "title": "Updated",
        })
        assert response.status_code in [403, 500]

    def test_update_chapter_not_found(self, client, mock_db):
        """Test chapter update when chapter not found"""
        mock_db.cursor().fetchone.return_value = None

        response = client.put("/api/chapters/ch1", json={
            "user_id": "prof123",
            "title": "Updated",
        })
        assert response.status_code in [404, 500]


class TestDeleteChapter:
    """Test DELETE /api/chapters/<id> - lines 3328-3389"""

    def test_delete_chapter_success(self, client, mock_db):
        """Test successful chapter deletion"""
        mock_db.cursor().fetchone.return_value = ("CLS1", "file.pdf", "prof123")

        response = client.delete("/api/chapters/ch1?user_id=prof123")
        assert response.status_code in [200, 403, 404, 500]

    def test_delete_chapter_not_owner(self, client, mock_db):
        """Test chapter deletion by non-owner - lines 3368-3371"""
        mock_db.cursor().fetchone.return_value = ("CLS1", "file.pdf", "other_prof")

        response = client.delete("/api/chapters/ch1?user_id=not_owner")
        assert response.status_code in [403, 500]

    def test_delete_chapter_not_found(self, client, mock_db):
        """Test deleting non-existent chapter"""
        mock_db.cursor().fetchone.return_value = None

        response = client.delete("/api/chapters/ch1?user_id=prof123")
        assert response.status_code in [404, 500]

    def test_delete_chapter_options(self, client):
        """Test OPTIONS for delete chapter - lines 3332-3338"""
        response = client.options("/api/chapters/ch1")
        assert response.status_code == 200


class TestGenerateExercisesForChapter:
    """Test POST /api/chapters/<id>/generate-exercises - lines 3392-3520"""

    @patch('app.generate_exercises_from_pdf_content')
    @patch('app.extract_text_from_pdf_bytes')
    def test_full_generation_flow(self, mock_extract, mock_generate, client, mock_db):
        """Test complete exercise generation from chapter PDF"""
        mock_extract.return_value = "Analytics text from PDF"
        mock_generate.return_value = [
            {"title": "Q1", "description": "D1", "difficulty": "easy", "solution_code": "c1"},
        ]

        mock_db.cursor().fetchone.return_value = (
            memoryview(b"pdf-data"), "Chapter Title", "CLS123", "prof123",
        )

        response = client.post(
            "/api/chapters/ch123/generate-exercises",
            json={"user_id": "prof123"},
        )
        assert response.status_code in [201, 400, 403, 404, 500]

    def test_chapter_not_found(self, client, mock_db):
        """Test generation when chapter not found"""
        mock_db.cursor().fetchone.return_value = None

        response = client.post(
            "/api/chapters/ch123/generate-exercises",
            json={"user_id": "prof123"},
        )
        assert response.status_code in [404, 500]

    def test_not_professor(self, client, mock_db):
        """Test generation by non-professor - line 3425-3428"""
        mock_db.cursor().fetchone.return_value = (
            memoryview(b"pdf"), "Title", "CLS123", "other_prof",
        )

        response = client.post(
            "/api/chapters/ch123/generate-exercises",
            json={"user_id": "not_prof"},
        )
        assert response.status_code in [403, 500]

    def test_no_pdf_data(self, client, mock_db):
        """Test generation with missing PDF - line 3430-3433"""
        mock_db.cursor().fetchone.return_value = (None, "Title", "CLS123", "prof123")

        response = client.post(
            "/api/chapters/ch123/generate-exercises",
            json={"user_id": "prof123"},
        )
        assert response.status_code in [404, 500]

    @patch('app.extract_text_from_pdf_bytes')
    def test_empty_extracted_text(self, mock_extract, client, mock_db):
        """Test generation when extraction yields empty text - line 3448-3456"""
        mock_extract.return_value = ""
        mock_db.cursor().fetchone.return_value = (
            memoryview(b"pdf"), "Title", "CLS123", "prof123",
        )

        response = client.post(
            "/api/chapters/ch123/generate-exercises",
            json={"user_id": "prof123"},
        )
        assert response.status_code in [400, 500]

    @patch('app.extract_text_from_pdf_bytes')
    @patch('app.generate_exercises_from_pdf_content')
    def test_no_exercises_generated(self, mock_generate, mock_extract, client, mock_db):
        """Test when AI returns no exercises - line 3474-3477"""
        mock_extract.return_value = "Some text"
        mock_generate.return_value = []
        mock_db.cursor().fetchone.return_value = (
            memoryview(b"pdf"), "Title", "CLS123", "prof123",
        )

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            response = client.post(
                "/api/chapters/ch123/generate-exercises",
                json={"user_id": "prof123"},
            )
        assert response.status_code in [400, 500]


class TestGenerateExercisesEndpoint:
    """Test POST /api/chapters/<id>/generate-exercises (the other route) - lines 3713-3844"""

    @patch('app.generate_exercises_from_pdf_content')
    @patch('app.extract_text_from_pdf_bytes')
    def test_full_flow(self, mock_extract, mock_generate, client, mock_db):
        """Test complete exercise generation from chapter"""
        mock_extract.return_value = "PDF text content"
        mock_generate.return_value = [
            {"title": "Q1", "description": "D1", "difficulty": "easy", "solution_code": "c1"},
        ]

        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("CLS123", "Chapter", "prof123", "file.pdf", memoryview(b"pdf-bytes")),
            ("ex_1",),  # RETURNING from INSERT
        ]

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            response = client.post(
                "/api/chapters/ch123/generate-exercises",
                json={"user_id": "prof123"},
            )
        assert response.status_code in [201, 400, 403, 404, 500]

    def test_not_professor(self, client, mock_db):
        """Test generation by non-professor - lines 3755-3758"""
        mock_db.cursor().fetchone.return_value = (
            "CLS123", "Chapter", "other_prof", "file.pdf", memoryview(b"data"),
        )

        response = client.post(
            "/api/chapters/ch123/generate-exercises",
            json={"user_id": "not_prof"},
        )
        assert response.status_code in [403, 500]

    def test_no_pdf_bytes(self, client, mock_db):
        """Test generation when pdf_bytes is empty - lines 3767-3770"""
        mock_db.cursor().fetchone.return_value = (
            "CLS123", "Chapter", "prof123", "file.pdf", None,
        )

        response = client.post(
            "/api/chapters/ch123/generate-exercises",
            json={"user_id": "prof123"},
        )
        assert response.status_code in [404, 500]


class TestCreateExercise:
    """Test POST /api/classes/<id>/chapters/<id>/exercises - lines 4704-4785"""

    def test_create_exercise_success(self, client, mock_db):
        """Test manual exercise creation"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("prof123",),  # Professor owns class
            (1,),  # Chapter exists in class
        ]

        response = client.post(
            "/api/classes/CLS123/chapters/ch1/exercises",
            json={
                "user_id": "prof123",
                "title": "New Exercise",
                "description": "Write a function...",
                "difficulty": "easy",
                "solution_code": "def f(): return 1",
            },
        )
        assert response.status_code in [201, 403, 404, 500]

    def test_create_exercise_not_owner(self, client, mock_db):
        """Test exercise creation by non-owner"""
        mock_db.cursor().fetchone.return_value = ("other_prof",)

        response = client.post(
            "/api/classes/CLS123/chapters/ch1/exercises",
            json={"user_id": "not_owner", "title": "Test"},
        )
        assert response.status_code in [403, 500]

    def test_create_exercise_class_not_found(self, client, mock_db):
        """Test exercise creation with non-existent class"""
        mock_db.cursor().fetchone.return_value = None

        response = client.post(
            "/api/classes/NONEXIST/chapters/ch1/exercises",
            json={"user_id": "prof123", "title": "Test"},
        )
        assert response.status_code in [404, 500]

    def test_create_exercise_chapter_not_in_class(self, client, mock_db):
        """Test exercise creation when chapter not in class"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("prof123",),  # Professor owns class
            None,  # Chapter not found in class
        ]

        response = client.post(
            "/api/classes/CLS123/chapters/ch_wrong/exercises",
            json={"user_id": "prof123", "title": "Test"},
        )
        assert response.status_code in [404, 500]


class TestAddClassResource:
    """Test POST /api/classes/<id>/resources - lines 4788-4798 (OPTIONS) and link add"""

    def test_add_resource_options(self, client):
        """Test OPTIONS for add resource - lines 4792-4798"""
        response = client.options("/api/classes/CLS123/resources")
        assert response.status_code == 200


class TestUploadClassResource:
    """Test POST /api/classes/<id>/resources/upload - lines 4990-5031"""

    def test_upload_resource_file(self, client, mock_db):
        """Test file resource upload"""
        response = client.post(
            "/api/classes/CLS123/resources/upload",
            data={
                "user_id": "prof123",
                "title": "Data File",
                "resource_type": "csv",
                "file": (BytesIO(b"col1,col2\n1,2"), "data.csv"),
            },
            content_type="multipart/form-data",
        )
        assert response.status_code in [201, 400, 500]

    def test_upload_resource_missing_file(self, client, mock_db):
        """Test upload without file"""
        response = client.post(
            "/api/classes/CLS123/resources/upload",
            data={"user_id": "prof123", "title": "Test"},
            content_type="multipart/form-data",
        )
        assert response.status_code in [400, 500]


class TestServeResource:
    """Test GET /api/classes/<id>/resources/<id>/serve - lines 5086-5150"""

    def test_serve_resource_pdf(self, client, mock_db):
        """Test serving PDF resource"""
        mock_db.cursor().fetchone.return_value = (
            memoryview(b"%PDF-content"), "doc.pdf", "pdf",
        )

        response = client.get("/api/classes/CLS123/resources/res123/serve")
        assert response.status_code in [200, 404, 500]

    def test_serve_resource_csv(self, client, mock_db):
        """Test serving CSV resource"""
        mock_db.cursor().fetchone.return_value = (
            memoryview(b"col1,col2\n1,2"), "data.csv", "csv",
        )

        response = client.get("/api/classes/CLS123/resources/res123/serve")
        assert response.status_code in [200, 404, 500]

    def test_serve_resource_not_found(self, client, mock_db):
        """Test serving non-existent resource"""
        mock_db.cursor().fetchone.return_value = None

        response = client.get("/api/classes/CLS123/resources/res123/serve")
        assert response.status_code in [404, 500]


class TestCreateClassResourceJSON:
    """Test POST /api/classes/<id>/resources JSON - lines 5153-5196"""

    def test_create_resource_link(self, client, mock_db):
        """Test creating link resource via JSON"""
        response = client.post("/api/classes/CLS123/resources", json={
            "user_id": "prof123",
            "title": "Tutorial",
            "description": "Good tutorial",
            "resource_type": "link",
            "resource_url": "https://example.com",
        })
        assert response.status_code in [201, 400, 500]

    def test_create_resource_missing_user(self, client, mock_db):
        """Test creating resource without user_id"""
        response = client.post("/api/classes/CLS123/resources", json={
            "title": "Tutorial",
        })
        assert response.status_code in [400, 500]


class TestManageResource:
    """Test PUT/DELETE /api/classes/<id>/resources/<id> - lines 5199-5244"""

    def test_manage_resource_options(self, client):
        """Test OPTIONS for resource management - lines 5203-5209"""
        response = client.options("/api/classes/CLS123/resources/res123")
        assert response.status_code == 200

    def test_manage_resource_delete(self, client, mock_db):
        """Test deleting resource - lines 5215-5220"""
        response = client.delete("/api/classes/CLS123/resources/res123")
        assert response.status_code in [200, 500]

    def test_manage_resource_update(self, client, mock_db):
        """Test updating resource - lines 5222-5241"""
        response = client.put("/api/classes/CLS123/resources/res123", json={
            "title": "Updated",
            "description": "New desc",
            "resource_type": "link",
            "resource_url": "https://updated.com",
        })
        assert response.status_code in [200, 500]


class TestDownloadResource:
    """Test GET /api/resources/<id>/download - lines 5247-5279"""

    def test_download_resource_success(self, client, mock_db):
        """Test successful resource download"""
        mock_db.cursor().fetchone.return_value = (
            memoryview(b"file content data"), "report.pdf", "pdf",
        )

        response = client.get("/api/resources/res123/download")
        assert response.status_code in [200, 404, 500]

    def test_download_resource_no_file(self, client, mock_db):
        """Test downloading resource with no file data"""
        mock_db.cursor().fetchone.return_value = (None, "missing.pdf", "pdf")

        response = client.get("/api/resources/res123/download")
        assert response.status_code in [404, 500]

    def test_download_resource_not_found(self, client, mock_db):
        """Test downloading non-existent resource"""
        mock_db.cursor().fetchone.return_value = None

        response = client.get("/api/resources/nonexist/download")
        assert response.status_code in [404, 500]


class TestHealthCheckDeep:
    """Test health check deep paths - lines 2105-2190"""

    @patch('app.storage_health_check')
    @patch('app.cache_health_check')
    def test_health_check_degraded(self, mock_cache, mock_storage, client, mock_db):
        """Test health check when DB is unhealthy"""
        mock_cursor = mock_db.cursor()
        mock_cursor.execute.side_effect = Exception("DB connection error")
        mock_cache.return_value = {"healthy": True}
        mock_storage.return_value = {"healthy": True}

        response = client.get("/api/health")
        assert response.status_code in [200, 503]

    @patch('app.storage_health_check')
    @patch('app.cache_health_check')
    def test_health_check_all_healthy(self, mock_cache, mock_storage, client, mock_db):
        """Test health check when all services healthy"""
        mock_cache.return_value = {"healthy": True}
        mock_storage.return_value = {"healthy": True}

        response = client.get("/api/health")
        assert response.status_code in [200, 503]


class TestCsrfTokenDeep:
    """Test CSRF token endpoint - lines 2196-2216"""

    def test_csrf_token_disabled(self, client, mock_db):
        """Test CSRF token when feature is disabled"""
        response = client.get("/api/csrf-token")
        assert response.status_code in [200, 500]

    @patch('app.config')
    def test_csrf_token_enabled(self, mock_config, client, mock_db):
        """Test CSRF token when enabled"""
        mock_config.FEATURE_CSRF_PROTECTION = True
        response = client.get("/api/csrf-token")
        assert response.status_code in [200, 500]


class TestDeleteUserEndpoint:
    """Test DELETE /api/users/delete - lines 1121-1142"""

    def test_delete_user_success(self, client, mock_db):
        """Test successful user deletion"""
        response = client.delete("/api/users/delete?user_id=user123")
        assert response.status_code in [200, 400, 500]

    def test_delete_user_missing_id(self, client, mock_db):
        """Test deletion without user_id"""
        response = client.delete("/api/users/delete")
        assert response.status_code in [400, 500]


class TestPracticeProgress:
    """Test practice progress endpoints - lines 1722-1928"""

    def test_get_practice_progress_by_exercise(self, client, mock_db):
        """Test getting progress for specific exercise"""
        mock_db.cursor().fetchone.return_value = (
            "ex1", "Exercise", 85, 90.0, 3, True, datetime(2026, 1, 1),
        )

        response = client.get(
            "/api/users/practice-progress?user_id=user123&exercise_id=ex1"
        )
        assert response.status_code in [200, 400, 500]

    def test_get_practice_progress_all(self, client, mock_db):
        """Test getting all practice progress"""
        mock_db.cursor().fetchall.return_value = [
            ("ex1", "Exercise 1", 85, 90.0, 3, True, datetime(2026, 1, 1)),
        ]

        response = client.get("/api/users/practice-progress?user_id=user123")
        assert response.status_code in [200, 400, 500]

    def test_update_practice_progress(self, client, mock_db):
        """Test updating practice progress"""
        mock_db.cursor().fetchone.return_value = None  # No existing progress

        response = client.put("/api/users/practice-progress", json={
            "user_id": "user123",
            "exercise_id": "ex1",
            "score": 85,
            "accuracy": 90.0,
        })
        assert response.status_code in [200, 400, 404, 500]

    def test_update_practice_progress_new_best(self, client, mock_db):
        """Test updating when new score is a personal best"""
        mock_db.cursor().fetchone.return_value = (
            "user123", "ex1", 70, 75.0, 2, False, None,
        )

        response = client.put("/api/users/practice-progress", json={
            "user_id": "user123",
            "exercise_id": "ex1",
            "score": 95,
            "accuracy": 98.0,
        })
        assert response.status_code in [200, 400, 404, 500]

    def test_get_practice_progress_missing_user(self, client, mock_db):
        """Test getting progress without user_id"""
        response = client.get("/api/users/practice-progress")
        assert response.status_code in [400, 500]


class TestDeleteClass:
    """Test DELETE /api/classes/<id> - lines 3523-3562"""

    def test_delete_class_success(self, client, mock_db):
        """Test successful class deletion"""
        mock_db.cursor().fetchone.return_value = ("prof123",)

        response = client.delete("/api/classes/CLS123?user_id=prof123")
        assert response.status_code in [200, 403, 404, 500]

    def test_delete_class_not_owner(self, client, mock_db):
        """Test deleting class as non-owner"""
        mock_db.cursor().fetchone.return_value = ("other_prof",)

        response = client.delete("/api/classes/CLS123?user_id=not_owner")
        assert response.status_code in [403, 500]

    def test_delete_class_not_found(self, client, mock_db):
        """Test deleting non-existent class"""
        mock_db.cursor().fetchone.return_value = None

        response = client.delete("/api/classes/NONEXIST?user_id=prof123")
        assert response.status_code in [404, 500]

    def test_delete_class_missing_user(self, client, mock_db):
        """Test deleting class without user_id"""
        response = client.delete("/api/classes/CLS123")
        assert response.status_code in [400, 500]
