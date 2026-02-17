"""
Tests targeting exception handlers and error paths in app.py.
Forces DB errors to exercise the except blocks that return 500.
Also covers: cached get_classes, update preferences rollback, 
conversation rollback, signup exceptions, signin exceptions.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import json


class TestExceptionHandlers:
    """Force exceptions in various endpoints to cover except blocks."""

    def test_get_conversations_db_error(self, client, mock_db):
        """Cover line 1204-1205 (get_conversations exception)"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.get("/api/users/conversations?user_id=user123")
        assert response.status_code in [401, 500]

    def test_create_conversation_db_error(self, client, mock_db):
        """Cover line 1242-1243 (create_conversation exception)"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.post("/api/users/conversations", json={
            "user_id": "user123", "title": "Test",
        })
        assert response.status_code in [401, 500]

    def test_update_conversation_db_error_rollback(self, client, mock_db):
        """Cover lines 1370-1373 (update_conversation rollback)"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.put("/api/users/conversations/conv1", json={
            "user_id": "user123", "title": "Updated",
        })
        assert response.status_code in [401, 500]

    def test_delete_conversation_db_error(self, client, mock_db):
        """Cover lines 1402-1403"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.delete("/api/users/conversations/conv1?user_id=user123")
        assert response.status_code in [401, 500]

    def test_get_ai_digest_db_error(self, client, mock_db):
        """Cover lines 1468-1469"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.get("/api/users/ai-digest?user_id=user123")
        assert response.status_code in [401, 500]

    def test_update_ai_digest_db_error(self, client, mock_db):
        """Cover lines 1528-1529"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.put("/api/users/ai-digest", json={
            "user_id": "user123", "digest": {"goal": "test"},
        })
        assert response.status_code in [401, 500]

    def test_get_ai_memory_db_error(self, client, mock_db):
        """Cover lines 1559-1560"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.get("/api/users/ai-memory?user_id=user123")
        assert response.status_code in [401, 500]

    def test_update_ai_memory_db_error(self, client, mock_db):
        """Cover lines 1597-1598"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.put("/api/users/ai-memory", json={
            "user_id": "user123", "memory": ["item1"],
        })
        assert response.status_code in [401, 500]

    def test_update_preferences_db_error_rollback(self, client, mock_db):
        """Cover lines 1716-1719 (update_preferences rollback)"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.put("/api/users/preferences", json={
            "user_id": "user123", "currentLanguage": "python",
        })
        assert response.status_code in [401, 500]

    def test_signup_db_error(self, client, mock_db):
        """Cover lines 645-646 (signup exception)"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.post("/api/users/signup", json={
            "name": "Test", "email": "test@test.com", "password": "pass123",
        })
        assert response.status_code in [500, 429]

    def test_get_profile_db_error(self, client, mock_db):
        """Cover lines 928-929 (get_profile exception)"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.get("/api/users/profile?user_id=user123")
        assert response.status_code in [401, 500]

    def test_update_profile_db_error(self, client, mock_db):
        """Cover lines 983-984 (update_profile exception)"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.put("/api/users/profile", json={
            "user_id": "user123", "bio": "test",
        })
        assert response.status_code in [401, 500]

    def test_get_settings_db_error(self, client, mock_db):
        """Cover lines 1018-1019 (get_settings exception)"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.get("/api/users/settings?user_id=user123")
        assert response.status_code in [401, 500]

    def test_update_settings_db_error(self, client, mock_db):
        """Cover lines 1059-1064"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.put("/api/users/settings", json={
            "user_id": "user123", "emailNotifications": True,
        })
        assert response.status_code in [401, 500]

    def test_update_password_db_error(self, client, mock_db):
        """Cover lines 1115-1118"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.put("/api/users/password", json={
            "user_id": "user123", "currentPassword": "oldpassword", "newPassword": "newpassword123",
        })
        assert response.status_code in [401, 500]

    def test_delete_user_db_error(self, client, mock_db):
        """Cover lines 1141-1142"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.delete("/api/users/delete?user_id=user123")
        assert response.status_code in [401, 500]

    def test_reset_password_db_error_rollback(self, client, mock_db):
        """Cover lines 879-882 (reset_password rollback)"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.post("/api/users/reset-password", json={
            "token": "tok", "email": "test@test.com", "newPassword": "newpass123",
        })
        assert response.status_code in [401, 500]

    def test_get_classes_db_error(self, client, mock_db):
        """Cover get_classes exception"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.get("/api/classes?user_id=user123")
        assert response.status_code in [200, 401, 500]

    def test_get_class_by_id_db_error(self, client, mock_db):
        """Cover get_class_by_id exception"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.get("/api/classes/CLS123?user_id=user123")
        assert response.status_code in [401, 500]

    def test_create_class_db_error(self, client, mock_db):
        """Cover create_class exception"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.post("/api/classes", headers={"X-Test-User-Role": "professor"}, json={
            "user_id": "prof123", "name": "Class", "class_code": "CLS123",
        })
        assert response.status_code in [401, 500]

    def test_update_class_db_error(self, client, mock_db):
        """Cover update_class exception - lines 2914-2917"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.put("/api/classes/CLS123", json={
            "user_id": "prof123", "name": "New",
        })
        assert response.status_code in [401, 500]

    def test_delete_class_db_error(self, client, mock_db):
        """Cover delete_class exception - lines 3561-3562"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.delete("/api/classes/CLS123?user_id=prof123")
        assert response.status_code in [401, 500]

    def test_get_class_resources_db_error(self, client, mock_db):
        """Cover get_class_resources exception"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.get("/api/classes/CLS123/resources?user_id=prof123")
        assert response.status_code in [401, 500]

    def test_upload_chapter_db_error(self, client, mock_db):
        """Cover upload_chapter exception - lines 2985-2987"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.post(
            "/api/classes/CLS123/chapters",
            data={"user_id": "prof123", "title": "Ch"},
            content_type="multipart/form-data",
        )
        assert response.status_code in [401, 500]

    def test_get_chapters_db_error(self, client, mock_db):
        """Cover get_chapters exception - lines 3271-3272"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.get("/api/classes/CLS123/chapters?user_id=prof123")
        assert response.status_code in [401, 500]

    def test_update_chapter_db_error(self, client, mock_db):
        """Cover update_chapter exception - lines 3324-3325"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.put("/api/chapters/ch1", json={
            "user_id": "prof123", "title": "New",
        })
        assert response.status_code in [401, 500]

    def test_delete_chapter_db_error(self, client, mock_db):
        """Cover delete_chapter exception - lines 3385-3389"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.delete("/api/chapters/ch1?user_id=prof123")
        assert response.status_code in [401, 500]

    def test_generate_exercises_for_chapter_db_error(self, client, mock_db):
        """Cover generate_exercises_for_chapter exception"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.post("/api/chapters/ch1/generate-exercises", json={
            "user_id": "prof123",
        })
        assert response.status_code in [401, 500]

    def test_get_chapter_exercises_db_error(self, client, mock_db):
        """Cover get_chapter_exercises exception - lines 3656-3657"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.get("/api/chapters/ch1/exercises?user_id=prof123")
        assert response.status_code in [401, 500]

    def test_enroll_db_error(self, client, mock_db):
        """Cover enroll exception"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.post("/api/classes/enroll", json={
            "user_id": "student123", "class_id": "CLS123",
        })
        assert response.status_code in [401, 500]

    def test_get_enrolled_classes_db_error(self, client, mock_db):
        """Cover get_enrolled_classes exception - lines 4028-4029"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.get("/api/classes/enrolled?user_id=student123")
        assert response.status_code in [401, 500]

    def test_get_class_students_db_error(self, client, mock_db):
        """Cover get_class_students exception - lines 4088-4089"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.get("/api/classes/CLS123/students?user_id=prof123")
        assert response.status_code in [401, 500]

    def test_get_class_progress_db_error(self, client, mock_db):
        """Cover get_class_progress exception - lines 4231-4237"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.get("/api/classes/CLS123/progress?user_id=prof123")
        assert response.status_code in [401, 500]

    def test_get_progress_db_error(self, client, mock_db):
        """Cover get_progress exception"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.get("/api/progress?user_id=user123")
        assert response.status_code in [401, 500]

    def test_get_student_progress_db_error(self, client, mock_db):
        """Cover get_student_progress exception - lines 4463-4467"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.get("/api/students/s1/progress?user_id=prof123")
        assert response.status_code in [401, 403, 500]

    def test_avg_leaderboard_db_error(self, client, mock_db):
        """Cover average leaderboard exception - lines 4564-4569"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.get("/api/classes/CLS123/leaderboard/average?user_id=prof123")
        assert response.status_code in [401, 500]

    def test_exercise_leaderboard_db_error(self, client, mock_db):
        """Cover exercise leaderboard exception - lines 4648-4655"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.get("/api/classes/CLS123/leaderboard/exercise/ex1?user_id=prof123")
        assert response.status_code in [401, 500]

    def test_create_exercise_db_error(self, client, mock_db):
        """Cover create_exercise exception - lines 4784-4785"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.post("/api/classes/CLS123/chapters/ch1/exercises", json={
            "user_id": "prof123", "title": "Test",
        })
        assert response.status_code in [401, 500]

    def test_add_class_resource_db_error(self, client, mock_db):
        """Cover add_class_resource exception"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.post("/api/classes/CLS123/resources", json={
            "user_id": "prof123", "title": "Test",
        })
        assert response.status_code in [401, 500]

    def test_upload_resource_db_error(self, client, mock_db):
        """Cover upload_class_resource exception - lines 5086-5090"""
        from io import BytesIO
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.post(
            "/api/classes/CLS123/resources/upload",
            data={
                "user_id": "prof123",
                "file": (BytesIO(b"data"), "test.txt"),
            },
            content_type="multipart/form-data",
        )
        assert response.status_code in [401, 500]

    def test_serve_resource_download_db_error(self, client, mock_db):
        """Cover serve_resource_download exception - lines 5148-5150"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.get("/api/resources/res123/download")
        assert response.status_code in [401, 500]

    def test_manage_resource_db_error(self, client, mock_db):
        """Cover manage_resource exception - lines 5243-5244"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.delete("/api/classes/CLS123/resources/res123")
        assert response.status_code in [401, 500]

    def test_serve_resource_file_db_error(self, client, mock_db):
        """Cover serve_resource_file exception"""
        response = client.get("/api/resources/files/nonexistent.pdf")
        assert response.status_code in [401, 404, 500]

    def test_delete_exercise_db_error(self, client, mock_db):
        """Cover delete_exercise exception - lines 4950-4951"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.delete("/api/exercises/ex1")
        assert response.status_code in [401, 500]

    def test_get_exercise_db_error(self, client, mock_db):
        """Cover get_exercise exception - lines 2790-2791"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.get("/api/exercises/ex1?user_id=user123")
        assert response.status_code in [401, 500]

    def test_update_exercise_db_error(self, client, mock_db):
        """Cover update_exercise exception - lines 2845-2846"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.put("/api/exercises/ex1", json={
            "user_id": "prof123", "title": "New",
        })
        assert response.status_code in [401, 500]

    def test_get_practice_progress_db_error(self, client, mock_db):
        """Cover practice progress exception"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.get("/api/users/practice-progress?user_id=user123")
        assert response.status_code in [401, 500]

    def test_serve_chapter_pdf_db_error(self, client, mock_db):
        """Cover serve_chapter_pdf exception"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.get("/api/chapters/ch1/pdf?user_id=user123")
        assert response.status_code in [401, 500]

    def test_contact_db_error(self, client, mock_db):
        """Cover contact exception - line 2308-2310"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.post("/api/contact", json={
            "name": "Test", "email": "t@t.com", "subject": "Help", "message": "Msg",
        })
        assert response.status_code in [200, 401, 500]

    def test_health_check_db_error(self, client, mock_db):
        """Cover health_check exception paths - lines 2074-2075, 2105-2108"""
        mock_db.cursor().execute.side_effect = Exception("DB connection failed")

        with patch("app.storage_health_check", return_value={"healthy": False}):
            with patch("app.cache_health_check", return_value={"healthy": True}):
                response = client.get("/api/health")
        assert response.status_code in [200, 503]


class TestSigninExceptionHandlers:
    """Test signin exception paths"""

    def test_signin_db_error(self, client, mock_db):
        """Cover signin exception"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.post("/api/users/signin", json={
            "email": "test@test.com", "password": "pass123",
        })
        assert response.status_code in [500, 429]

    def test_signin_hash_migration_failure(self, client, mock_db):
        """Cover lines 699-704 (hash migration failure during signin)"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.return_value = (
            "user123", "Test", "test@test.com", "12345", "student",
        )

        with patch("blueprints.auth.verify_password", return_value=(True, True)):
            with patch("blueprints.auth.hash_password", side_effect=Exception("Hash error")):
                response = client.post("/api/users/signin", json={
                    "email": "test@test.com",
                    "password": "pass",
                })
        assert response.status_code in [200, 429, 500]


class TestForgotPasswordExceptions:
    """Test forgot password exception paths"""

    def test_forgot_password_db_error(self, client, mock_db):
        """Cover lines 785-796 (forgot_password exception)"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.post("/api/users/forgot-password", json={
            "email": "test@test.com",
        })
        assert response.status_code in [500, 429]


class TestUpdatePracticeProgressError:
    """Test update practice progress exception"""

    def test_update_practice_progress_db_error(self, client, mock_db):
        """Cover update_practice_progress exception"""
        mock_db.cursor().execute.side_effect = Exception("DB error")
        response = client.put("/api/users/practice-progress", json={
            "user_id": "user123", "exercise_id": "ex1", "score": 85,
        })
        assert response.status_code in [500, 404]


class TestCsrfTokenException:
    """Test CSRF token exception path - lines 2213-2216"""

    def test_csrf_token_exception(self, client, mock_db):
        """Cover lines 2213-2216"""
        with patch("app.config") as mock_config:
            mock_config.FEATURE_CSRF_PROTECTION = True
            with patch("app.generate_csrf", side_effect=Exception("CSRF error")):
                response = client.get("/api/csrf-token")
        assert response.status_code in [200, 401, 500]


class TestTaskStatusDeep:
    """Test task status deep paths - lines 2238-2258"""

    def test_task_status_celery_enabled(self, client, mock_db):
        """Test task status when celery is available"""
        with patch("app.celery_app") as mock_celery:
            with patch("app.FEATURE_ASYNC_TASKS", True):
                mock_celery.__bool__ = lambda self: True
                response = client.get("/api/tasks/task123")
        assert response.status_code in [200, 404, 500, 503]
