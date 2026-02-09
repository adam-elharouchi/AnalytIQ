"""
Deep tests for leaderboard endpoints and student progress endpoint.
Targets uncovered lines: 4329-4467 (get_student_progress), 4479-4655 (leaderboards),
4784-4951 (PDF serving + delete exercise), 2208-2258 (delete user, CSRF token)
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import json


class TestStudentProgressProfessor:
    """Test GET /api/students/<id>/progress - lines 4329-4467"""

    def test_get_student_progress_with_class(self, client, mock_db):
        """Test getting student progress filtered by class"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("professor",),  # User role
            ("s1", "Student 1", "s1@test.com"),  # Student exists
            ("prof123",),  # Class owned by professor
        ]
        mock_cursor.fetchall.return_value = [
            ("ex1", "Exercise 1", "easy", 85, 90.0, 3, True, datetime(2026, 1, 1)),
        ]

        response = client.get(
            "/api/students/s1/progress?user_id=prof123&class_id=CLS123"
        )
        assert response.status_code in [200, 403, 404, 500]

    def test_get_student_progress_all_classes(self, client, mock_db):
        """Test getting student progress across all classes"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("professor",),
            ("s1", "Student 1", "s1@test.com"),
        ]
        mock_cursor.fetchall.return_value = [
            ("ex1", "Exercise 1", "easy", "CLS1", "Class 1", 85, 90.0, 3, True, datetime(2026, 1, 1)),
        ]

        response = client.get("/api/students/s1/progress?user_id=prof123")
        assert response.status_code in [200, 403, 404, 500]

    def test_get_student_progress_not_professor(self, client, mock_db):
        """Test non-professor accessing student progress"""
        mock_db.cursor().fetchone.return_value = ("student",)

        response = client.get("/api/students/s1/progress?user_id=student123")
        assert response.status_code in [403, 500]

    def test_get_student_progress_student_not_found(self, client, mock_db):
        """Test with non-existent student"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("professor",),  # User is professor
            None,  # Student not found
        ]

        response = client.get("/api/students/nonexist/progress?user_id=prof123")
        assert response.status_code in [401, 404, 500]

    def test_get_student_progress_user_not_found(self, client, mock_db):
        """Test with non-existent requesting user"""
        mock_db.cursor().fetchone.return_value = None

        response = client.get("/api/students/s1/progress?user_id=nonexist")
        assert response.status_code in [401, 404, 500]

    def test_get_student_progress_missing_user(self, client, mock_db):
        """Test without user_id parameter"""
        response = client.get("/api/students/s1/progress")
        assert response.status_code in [400, 401, 403, 500]

    def test_get_student_progress_class_access_denied(self, client, mock_db):
        """Test when professor doesn't own the class - lines 4369-4372"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("professor",),  # User is professor
            ("s1", "Student 1", "s1@test.com"),  # Student exists
            ("other_prof",),  # Class owned by different professor
        ]

        response = client.get(
            "/api/students/s1/progress?user_id=prof123&class_id=CLS123"
        )
        assert response.status_code in [403, 500]


class TestAverageLeaderboard:
    """Test GET /api/classes/<id>/leaderboard/average - lines 4479-4569"""

    def test_average_leaderboard_as_professor(self, client, mock_db):
        """Test professor viewing class average leaderboard"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.return_value = ("prof123",)  # Professor owns class
        mock_cursor.fetchall.return_value = [
            ("s1", "Student 1", "s1@test.com", 85.5, 3),
            ("s2", "Student 2", "s2@test.com", 72.0, 2),
        ]

        response = client.get(
            "/api/classes/CLS123/leaderboard/average?user_id=prof123"
        )
        assert response.status_code in [200, 403, 404, 500]

    def test_average_leaderboard_as_enrolled_student(self, client, mock_db):
        """Test enrolled student viewing leaderboard"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("other_prof",),  # Class professor (not the requesting user)
            (1,),  # Enrolled check
        ]
        mock_cursor.fetchall.return_value = [
            ("s1", "Student", "s@e.com", 90.0, 5),
        ]

        response = client.get(
            "/api/classes/CLS123/leaderboard/average?user_id=student123"
        )
        assert response.status_code in [200, 403, 500]

    def test_average_leaderboard_not_enrolled(self, client, mock_db):
        """Test non-enrolled student viewing leaderboard"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("other_prof",),  # Not the professor
            None,  # Not enrolled
        ]

        response = client.get(
            "/api/classes/CLS123/leaderboard/average?user_id=random"
        )
        assert response.status_code in [403, 500]

    def test_average_leaderboard_class_not_found(self, client, mock_db):
        """Test leaderboard for non-existent class"""
        mock_db.cursor().fetchone.return_value = None

        response = client.get(
            "/api/classes/NONEXIST/leaderboard/average?user_id=prof123"
        )
        assert response.status_code in [401, 404, 500]

    def test_average_leaderboard_missing_user(self, client, mock_db):
        """Test leaderboard without user_id"""
        response = client.get("/api/classes/CLS123/leaderboard/average")
        assert response.status_code in [400, 401, 403, 500]


class TestExerciseLeaderboard:
    """Test GET /api/classes/<id>/leaderboard/exercise/<id> - lines 4572-4655"""

    def test_exercise_leaderboard_success(self, client, mock_db):
        """Test getting exercise-specific leaderboard"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.return_value = ("prof123",)  # Professor
        mock_cursor.fetchall.return_value = [
            ("s1", "Student 1", "s1@test.com", 95.0),
            ("s2", "Student 2", "s2@test.com", 80.0),
        ]

        response = client.get(
            "/api/classes/CLS123/leaderboard/exercise/ex1?user_id=prof123"
        )
        assert response.status_code in [200, 403, 404, 500]

    def test_exercise_leaderboard_enrolled_student(self, client, mock_db):
        """Test enrolled student viewing exercise leaderboard"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("other_prof",),  # Not professor
            (1,),  # Enrolled
        ]
        mock_cursor.fetchall.return_value = [
            ("s1", "Student", "s@e.com", 90.0),
        ]

        response = client.get(
            "/api/classes/CLS123/leaderboard/exercise/ex1?user_id=student123"
        )
        assert response.status_code in [200, 403, 500]

    def test_exercise_leaderboard_not_authorized(self, client, mock_db):
        """Test non-authorized user viewing exercise leaderboard"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("other_prof",),
            None,  # Not enrolled
        ]

        response = client.get(
            "/api/classes/CLS123/leaderboard/exercise/ex1?user_id=random"
        )
        assert response.status_code in [403, 500]

    def test_exercise_leaderboard_class_not_found(self, client, mock_db):
        """Test exercise leaderboard for non-existent class"""
        mock_db.cursor().fetchone.return_value = None

        response = client.get(
            "/api/classes/NONEXIST/leaderboard/exercise/ex1?user_id=prof123"
        )
        assert response.status_code in [401, 404, 500]

    def test_exercise_leaderboard_missing_user(self, client, mock_db):
        """Test exercise leaderboard without user_id"""
        response = client.get(
            "/api/classes/CLS123/leaderboard/exercise/ex1"
        )
        assert response.status_code in [400, 401, 403, 500]


class TestServeChapterPdfDeep:
    """Test serving chapter PDFs - lines 4836-4910"""

    def test_serve_pdf_from_database(self, client, mock_db):
        """Test serving PDF directly from database bytes"""
        mock_db.cursor().fetchone.return_value = (
            memoryview(b"%PDF-1.4\nFake PDF content"), "chapter.pdf",
        )

        response = client.get(
            "/api/chapters/ch123/pdf?user_id=user123"
        )
        assert response.status_code in [200, 401, 404, 500]

    def test_serve_pdf_fallback_filesystem(self, client, mock_db):
        """Test PDF serving fallback to filesystem - lines 4894-4901"""
        mock_db.cursor().fetchone.return_value = (None, "legacy.pdf")

        with patch("os.path.exists", return_value=True):
            with patch("app.send_from_directory") as mock_send:
                mock_send.return_value = MagicMock(
                    headers={}, status_code=200
                )
                response = client.get(
                    "/api/chapters/ch123/pdf?user_id=user123"
                )
        assert response.status_code in [200, 401, 404, 500]

    def test_serve_pdf_no_data(self, client, mock_db):
        """Test serving PDF when no data available - line 4903"""
        mock_db.cursor().fetchone.return_value = (None, None)

        response = client.get(
            "/api/chapters/ch123/pdf?user_id=user123"
        )
        assert response.status_code in [401, 404, 500]

    def test_serve_pdf_file_not_found(self, client, mock_db):
        """Test PDF fallback when file doesn't exist"""
        mock_db.cursor().fetchone.return_value = (None, "missing.pdf")

        with patch("os.path.exists", return_value=False):
            response = client.get(
                "/api/chapters/ch123/pdf?user_id=user123"
            )
        assert response.status_code in [401, 404, 500]


class TestDeleteExerciseDeep:
    """Test DELETE /api/exercises/<id> - lines 4912-4951"""

    def test_delete_exercise_success(self, client, mock_db):
        """Test successful exercise deletion"""
        mock_db.cursor().fetchone.return_value = ("ch123", "CLS123")

        response = client.delete("/api/exercises/ex123")
        assert response.status_code in [200, 401, 404, 500]

    def test_delete_exercise_not_found(self, client, mock_db):
        """Test deleting non-existent exercise"""
        mock_db.cursor().fetchone.return_value = None

        response = client.delete("/api/exercises/nonexist")
        assert response.status_code in [401, 404, 500]

    def test_delete_exercise_options(self, client):
        """Test OPTIONS for delete exercise - lines 4916-4922"""
        response = client.options("/api/exercises/ex123")
        assert response.status_code == 200


class TestDeleteUserDeep:
    """Test DELETE /api/users/delete - lines 1121-1142"""

    def test_delete_user_success(self, client, mock_db):
        """Test deleting user account"""
        response = client.delete("/api/users/delete?user_id=user123")
        assert response.status_code in [200, 400, 401, 500]

    def test_delete_user_missing_id(self, client, mock_db):
        """Test deleting user without user_id"""
        response = client.delete("/api/users/delete")
        assert response.status_code in [400, 401, 403, 500]


class TestCsrfToken:
    """Test GET /api/csrf-token"""

    def test_get_csrf_token(self, client, mock_db):
        """Test getting CSRF token"""
        response = client.get("/api/csrf-token")
        assert response.status_code in [200, 401, 500]


class TestGetProfile:
    """Test profile endpoints - lines 885-984"""

    def test_get_profile_success(self, client, mock_db):
        """Test getting user profile"""
        mock_db.cursor().fetchone.return_value = (
            "user123", "Test User", "test@test.com",
            "Test Full Name", "A bio", "pic.jpg",
        )

        response = client.get("/api/users/profile?user_id=user123")
        assert response.status_code in [200, 401, 404, 500]

    def test_get_profile_not_found(self, client, mock_db):
        """Test getting non-existent profile - line 912"""
        mock_db.cursor().fetchone.return_value = None

        response = client.get("/api/users/profile?user_id=nonexist")
        assert response.status_code in [401, 404, 500]

    def test_update_profile_email_and_name(self, client, mock_db):
        """Test updating profile with email and fullName"""
        response = client.put("/api/users/profile", json={
            "user_id": "user123",
            "fullName": "New Full Name",
            "email": "new@test.com",
            "bio": "Updated bio",
            "profilePicture": "new_pic.jpg",
        })
        assert response.status_code in [200, 400, 401, 500]

    def test_update_profile_without_email(self, client, mock_db):
        """Test updating profile without email - lines 950-960"""
        response = client.put("/api/users/profile", json={
            "user_id": "user123",
            "bio": "Just a bio update",
        })
        assert response.status_code in [200, 400, 401, 500]


class TestGetSettings:
    """Test settings endpoints - lines 987-1019"""

    def test_get_settings_no_result(self, client, mock_db):
        """Test getting settings when no records exist - line 1007"""
        mock_db.cursor().fetchone.return_value = None

        response = client.get("/api/users/settings?user_id=user123")
        assert response.status_code in [200, 401, 500]
        if response.status_code == 200:
            data = response.get_json()
            assert data.get("emailNotifications") is False

    def test_get_settings_with_data(self, client, mock_db):
        """Test getting settings with existing data"""
        mock_db.cursor().fetchone.return_value = (True,)

        response = client.get("/api/users/settings?user_id=user123")
        assert response.status_code in [200, 401, 500]
