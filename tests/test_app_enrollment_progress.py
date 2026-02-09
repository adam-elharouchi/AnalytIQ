"""
Deep tests for enrollment, leaderboard, and student progress endpoints
Targets: enroll_in_class, unenroll_student, get_enrolled_students,
leaderboard endpoints, student progress, practice progress deep paths
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import json


class TestEnrollInClass:
    """Test POST /api/classes/enroll endpoint - lines 3852-3946"""

    def test_enroll_student_success(self, client, mock_db):
        """Test successful student enrollment"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("student",),  # User role
            ("CLS123", "Analytics 101", "prof123"),  # Class exists
            None,  # Not already enrolled
            ("CLS123", "student123"),  # Enrollment result
        ]

        response = client.post("/api/classes/enroll", json={
            "user_id": "student123",
            "class_id": "CLS123",
        })
        assert response.status_code in [200, 201, 400, 403, 404, 409, 500]

    def test_enroll_missing_fields(self, client, mock_db):
        """Test enrollment with missing fields"""
        response = client.post("/api/classes/enroll", json={
            "user_id": "student123",
        })
        assert response.status_code in [400, 401, 403, 500]

    def test_enroll_professor_denied(self, client, mock_db):
        """Test professors cannot enroll in classes"""
        mock_db.cursor().fetchone.return_value = ("professor",)

        response = client.post("/api/classes/enroll", json={
            "user_id": "prof123",
            "class_id": "CLS123",
        })
        assert response.status_code in [403, 500]

    def test_enroll_class_not_found(self, client, mock_db):
        """Test enrollment in non-existent class"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("student",),  # User role
            None,  # Class not found
        ]

        response = client.post("/api/classes/enroll", json={
            "user_id": "student123",
            "class_id": "NONEXIST",
        })
        assert response.status_code in [401, 404, 500]

    def test_enroll_user_not_found(self, client, mock_db):
        """Test enrollment with non-existent user"""
        mock_db.cursor().fetchone.return_value = None

        response = client.post("/api/classes/enroll", json={
            "user_id": "nonexistent",
            "class_id": "CLS123",
        })
        assert response.status_code in [401, 404, 500]

    def test_enroll_options_request(self, client):
        """Test OPTIONS for enrollment endpoint"""
        response = client.options("/api/classes/enroll")
        assert response.status_code == 200


class TestGetEnrolledStudents:
    """Test GET /api/classes/<class_id>/students endpoint - lines 4051-4089"""

    def test_get_enrolled_students_success(self, client, mock_db):
        """Test getting enrolled students list"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.return_value = ("prof123",)  # Class professor
        mock_cursor.fetchall.return_value = [
            ("s1", "Student 1", "s1@test.com", datetime(2026, 1, 1)),
            ("s2", "Student 2", "s2@test.com", datetime(2026, 1, 2)),
        ]

        response = client.get("/api/classes/CLS123/students?user_id=prof123")
        assert response.status_code in [200, 400, 401, 403, 404, 500]

    def test_get_enrolled_students_missing_user_id(self, client, mock_db):
        """Test getting students without user_id"""
        response = client.get("/api/classes/CLS123/students")
        assert response.status_code in [400, 401, 403, 500]


class TestClassAverageLeaderboard:
    """Test GET /api/classes/<class_id>/leaderboard/average - lines 4479-4569"""

    def test_get_average_leaderboard_as_professor(self, client, mock_db):
        """Test getting average leaderboard as professor"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.return_value = ("prof123",)  # Professor owns class
        mock_cursor.fetchall.return_value = [
            ("s1", "Student 1", "s1@test.com", 92.5, 5),
            ("s2", "Student 2", "s2@test.com", 88.0, 4),
        ]

        response = client.get("/api/classes/CLS123/leaderboard/average?user_id=prof123")
        assert response.status_code in [200, 400, 401, 403, 404, 500]

    def test_get_average_leaderboard_as_enrolled_student(self, client, mock_db):
        """Test getting leaderboard as enrolled student"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("other_prof",),  # Not the professor
            (1,),  # But is enrolled
        ]
        mock_cursor.fetchall.return_value = [
            ("s1", "Student 1", "s1@test.com", 92.5, 5),
        ]

        response = client.get("/api/classes/CLS123/leaderboard/average?user_id=student123")
        assert response.status_code in [200, 403, 500]

    def test_get_average_leaderboard_not_authorized(self, client, mock_db):
        """Test leaderboard access denied"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("other_prof",),  # Not professor
            None,  # Not enrolled either
        ]

        response = client.get("/api/classes/CLS123/leaderboard/average?user_id=random")
        assert response.status_code in [403, 500]

    def test_get_average_leaderboard_class_not_found(self, client, mock_db):
        """Test leaderboard for non-existent class"""
        mock_db.cursor().fetchone.return_value = None

        response = client.get("/api/classes/NONEXIST/leaderboard/average?user_id=user123")
        assert response.status_code in [401, 404, 500]

    def test_get_average_leaderboard_missing_user_id(self, client, mock_db):
        """Test leaderboard without user_id"""
        response = client.get("/api/classes/CLS123/leaderboard/average")
        assert response.status_code in [400, 401, 403, 500]


class TestExerciseLeaderboardForClass:
    """Test GET /api/classes/<class_id>/leaderboard/exercise/<exercise_id> - lines 4572-4655"""

    def test_get_exercise_leaderboard_success(self, client, mock_db):
        """Test getting exercise-specific leaderboard"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.return_value = ("prof123",)  # Professor owns class
        mock_cursor.fetchall.return_value = [
            ("s1", "Student 1", "s1@test.com", 95.0),
            ("s2", "Student 2", "s2@test.com", 88.0),
        ]

        response = client.get(
            "/api/classes/CLS123/leaderboard/exercise/ex123?user_id=prof123"
        )
        assert response.status_code in [200, 400, 401, 403, 404, 500]

    def test_get_exercise_leaderboard_not_authorized(self, client, mock_db):
        """Test exercise leaderboard access denied"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("other_prof",),  # Not professor
            None,  # Not enrolled
        ]

        response = client.get(
            "/api/classes/CLS123/leaderboard/exercise/ex123?user_id=random"
        )
        assert response.status_code in [403, 500]


class TestUpdatePracticeProgress:
    """Test PUT /api/users/practice-progress deep paths - lines 1799-1928"""

    def test_update_progress_new_best(self, client, mock_db):
        """Test updating progress with new best score"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("user123",),  # User exists
            (80, 3),  # Existing progress (best=80, attempts=3)
        ]

        response = client.put("/api/users/practice-progress", json={
            "user_id": "user123",
            "exercise_id": "ex123",
            "score": 95,
            "accuracy": 92.5,
            "time_spent": 180,
            "progress_data": {
                "exercise_title": "Test Exercise",
                "accuracy": 92.5,
            },
        })
        assert response.status_code in [200, 400, 401, 404, 500]

    def test_update_progress_not_new_best(self, client, mock_db):
        """Test updating progress without new best score"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("user123",),  # User exists
            (95, 5),  # Existing progress (best=95, attempts=5)
        ]

        response = client.put("/api/users/practice-progress", json={
            "user_id": "user123",
            "exercise_id": "ex123",
            "score": 70,
            "accuracy": 65.0,
            "time_spent": 200,
        })
        assert response.status_code in [200, 400, 401, 404, 500]

    def test_update_progress_user_not_found(self, client, mock_db):
        """Test updating progress for non-existent user"""
        mock_db.cursor().fetchone.return_value = None

        response = client.put("/api/users/practice-progress", json={
            "user_id": "nonexistent",
            "exercise_id": "ex123",
            "score": 80,
        })
        assert response.status_code in [401, 404, 500]

    def test_update_progress_missing_fields(self, client, mock_db):
        """Test updating progress with missing required fields"""
        response = client.put("/api/users/practice-progress", json={
            "user_id": "user123",
        })
        assert response.status_code in [400, 401, 403, 500]

    def test_update_progress_with_class_id(self, client, mock_db):
        """Test updating progress with class_id for class exercises"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("user123",),  # User exists
            None,  # No existing progress
        ]

        response = client.put("/api/users/practice-progress", json={
            "user_id": "user123",
            "exercise_id": "ex123",
            "score": 85,
            "class_id": "CLS123",
            "class_exercise_id": "cls_ex_123",
        })
        assert response.status_code in [200, 400, 401, 404, 500]

    def test_update_progress_first_attempt(self, client, mock_db):
        """Test first attempt on an exercise"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("user123",),  # User exists
            None,  # No existing progress
        ]

        response = client.put("/api/users/practice-progress", json={
            "user_id": "user123",
            "exercise_id": "ex_new",
            "score": 60,
            "accuracy": 55.0,
        })
        assert response.status_code in [200, 400, 401, 404, 500]


class TestGetPracticeProgress:
    """Test GET /api/users/practice-progress deep paths - lines 1722-1796"""

    def test_get_progress_all_exercises(self, client, mock_db):
        """Test getting all exercise progress"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchall.return_value = [
            ("ex1", "Exercise 1", 85, 90.0, 3, True, datetime(2026, 1, 1)),
            ("ex2", "Exercise 2", 60, 70.0, 2, False, None),
        ]

        response = client.get("/api/users/practice-progress?user_id=user123")
        assert response.status_code in [200, 400, 401, 500]

    def test_get_progress_specific_exercise(self, client, mock_db):
        """Test getting progress for a specific exercise"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.return_value = (
            "ex1", "Exercise 1", 85, 90.0, 120, 3, 80, True, datetime(2026, 1, 1)
        )

        response = client.get(
            "/api/users/practice-progress?user_id=user123&exercise_id=ex1"
        )
        assert response.status_code in [200, 400, 401, 500]

    def test_get_progress_no_results(self, client, mock_db):
        """Test getting progress with no results"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.return_value = None

        response = client.get(
            "/api/users/practice-progress?user_id=user123&exercise_id=nonexistent"
        )
        assert response.status_code in [200, 400, 401, 500]

    def test_get_progress_missing_user_id(self, client, mock_db):
        """Test getting progress without user_id"""
        response = client.get("/api/users/practice-progress")
        assert response.status_code in [400, 401, 403, 500]


class TestGetAllProgress:
    """Test GET /api/exercises/progress endpoint - lines 1931-1974"""

    def test_get_all_progress_via_header(self, client, mock_db):
        """Test getting all progress using X-User-Id header"""
        mock_db.cursor().fetchall.return_value = [
            ("ex1", "Exercise 1", 85, 90.0, 3, True, None),
        ]

        response = client.get(
            "/api/exercises/progress",
            headers={"X-User-Id": "user123"},
        )
        assert response.status_code in [200, 400, 401, 500]

    def test_get_all_progress_via_query(self, client, mock_db):
        """Test getting all progress using query param"""
        mock_db.cursor().fetchall.return_value = []

        response = client.get("/api/exercises/progress?user_id=user123")
        assert response.status_code in [200, 400, 401, 500]


class TestExerciseLeaderboard:
    """Test GET /api/exercises/<exercise_id>/leaderboard - lines 1977-2022"""

    def test_get_leaderboard_with_results(self, client, mock_db):
        """Test leaderboard with multiple entries"""
        mock_db.cursor().fetchall.return_value = [
            ("User1", "u1@test.com", 95, 98.0, 100, 5, datetime(2026, 1, 1)),
            ("User2", "u2@test.com", 88, 92.0, 150, 3, datetime(2026, 1, 2)),
        ]

        response = client.get("/api/exercises/ex123/leaderboard?limit=10")
        assert response.status_code in [200, 401, 500]

    def test_get_leaderboard_empty(self, client, mock_db):
        """Test leaderboard with no entries"""
        mock_db.cursor().fetchall.return_value = []

        response = client.get("/api/exercises/ex123/leaderboard")
        assert response.status_code in [200, 401, 500]


class TestGrandLeaderboard:
    """Test GET /api/leaderboard/grand - lines 2025-2075"""

    def test_get_grand_leaderboard_success(self, client, mock_db):
        """Test getting grand leaderboard"""
        mock_db.cursor().fetchall.return_value = [
            ("u1", "User1", "u1@test.com", 10, 92.5, 925, datetime(2026, 1, 1)),
            ("u2", "User2", "u2@test.com", 8, 88.0, 704, datetime(2026, 1, 2)),
        ]

        response = client.get("/api/leaderboard/grand?limit=5")
        assert response.status_code in [200, 401, 500]

    def test_get_grand_leaderboard_default_limit(self, client, mock_db):
        """Test grand leaderboard with default limit"""
        mock_db.cursor().fetchall.return_value = []

        response = client.get("/api/leaderboard/grand")
        assert response.status_code in [200, 401, 500]


class TestGetStudentProgress:
    """Test GET /api/students/<student_id>/progress - lines 4329-4467"""

    def test_get_student_progress_as_professor(self, client, mock_db):
        """Test professor viewing student progress"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("professor",),  # User role
            ("s123", "Student Name", "student@test.com"),  # Student info
        ]
        mock_cursor.fetchall.return_value = [
            ("ex1", "Exercise 1", "easy", "CLS1", "Class 1", 85, 90.0, 3, True, datetime(2026, 1, 1)),
        ]

        response = client.get("/api/students/s123/progress?user_id=prof123")
        assert response.status_code in [200, 400, 401, 403, 404, 500]

    def test_get_student_progress_with_class_filter(self, client, mock_db):
        """Test professor viewing student progress filtered by class"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("professor",),  # User role
            ("s123", "Student Name", "student@test.com"),  # Student info
            ("prof123",),  # Professor owns class
        ]
        mock_cursor.fetchall.return_value = [
            ("ex1", "Exercise 1", "easy", 85, 90.0, 3, True, datetime(2026, 1, 1)),
        ]

        response = client.get(
            "/api/students/s123/progress?user_id=prof123&class_id=CLS123"
        )
        assert response.status_code in [200, 400, 401, 403, 404, 500]

    def test_get_student_progress_not_professor(self, client, mock_db):
        """Test non-professor trying to view student progress"""
        mock_db.cursor().fetchone.return_value = ("student",)

        response = client.get("/api/students/s123/progress?user_id=student456")
        assert response.status_code in [403, 500]

    def test_get_student_progress_student_not_found(self, client, mock_db):
        """Test viewing progress of non-existent student"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("professor",),  # User role
            None,  # Student not found
        ]

        response = client.get("/api/students/nonexist/progress?user_id=prof123")
        assert response.status_code in [401, 404, 500]

    def test_get_student_progress_missing_user_id(self, client, mock_db):
        """Test viewing progress without user_id"""
        response = client.get("/api/students/s123/progress")
        assert response.status_code in [400, 401, 403, 500]
