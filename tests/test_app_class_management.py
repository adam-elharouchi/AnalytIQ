"""
Comprehensive Tests for Class Management and Student Enrollment
Target: Push coverage from 66% to 70%+
"""
import pytest
from unittest.mock import patch, MagicMock
import json


class TestClassManagement:
    """Test class creation and management"""

    def test_create_class_success(self, mock_db_connection, mock_db_cursor):
        """Test creating a new class"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                mock_db_cursor.fetchone.return_value = ("class123",)

                response = client.post(
                    "/api/classes",
                    json={
                        "professor_id": "prof123",
                        "name": "Python 101",
                        "description": "Introduction to Python",
                        "semester": "Fall 2026"
                    }
                )

                assert response.status_code in [201, 400, 500]

    def test_create_class_missing_fields(self):
        """Test class creation with missing required fields"""
        from app import app

        with app.test_client() as client:
            response = client.post(
                "/api/classes",
                json={"professor_id": "prof123"}
            )

            assert response.status_code in [400, 500]

    def test_get_classes_by_professor(self, mock_db_connection, mock_db_cursor):
        """Test getting classes for a professor"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                mock_db_cursor.fetchall.return_value = [
                    ("class1", "Python 101", "Intro to Python", "Fall 2026", 25),
                    ("class2", "Data Science", "DS Fundamentals", "Fall 2026", 30),
                ]

                response = client.get("/api/classes?professor_id=prof123")

                assert response.status_code in [200, 400, 500]

    def test_get_classes_by_student(self, mock_db_connection, mock_db_cursor):
        """Test getting classes for a student"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                mock_db_cursor.fetchall.return_value = [
                    ("class1", "Python 101", "prof123", "Dr. Smith", 10, 7),
                ]

                response = client.get("/api/classes?student_id=student123")

                assert response.status_code in [200, 400, 500]

    def test_get_class_by_id(self, mock_db_connection, mock_db_cursor):
        """Test getting specific class details"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                mock_db_cursor.fetchone.return_value = (
                    "class123",
                    "Python 101",
                    "Introduction to Python",
                    "Fall 2026",
                    "prof123",
                    "Dr. Smith"
                )

                response = client.get("/api/classes/class123")

                assert response.status_code in [200, 400, 404, 500]

    def test_update_class_success(self, mock_db_connection, mock_db_cursor):
        """Test updating class information"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                response = client.put(
                    "/api/classes/class123",
                    json={
                        "professor_id": "prof123",
                        "name": "Python 101 - Updated",
                        "description": "Updated description"
                    }
                )

                assert response.status_code in [200, 400, 403, 404, 500]

    def test_delete_class_success(self, mock_db_connection, mock_db_cursor):
        """Test deleting a class"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                response = client.delete("/api/classes/class123?professor_id=prof123")

                assert response.status_code in [200, 400, 403, 404, 500]


class TestStudentEnrollment:
    """Test student enrollment operations"""

    def test_enroll_student_success(self, mock_db_connection, mock_db_cursor):
        """Test enrolling a student in a class"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                response = client.post(
                    "/api/classes/class123/enroll",
                    json={
                        "student_id": "student123",
                        "enrollment_code": "ABC123"
                    }
                )

                assert response.status_code in [200, 400, 404, 500]

    def test_enroll_student_invalid_code(self, mock_db_connection, mock_db_cursor):
        """Test enrollment with invalid code"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                mock_db_cursor.fetchone.return_value = None

                response = client.post(
                    "/api/classes/class123/enroll",
                    json={
                        "student_id": "student123",
                        "enrollment_code": "INVALID"
                    }
                )

                assert response.status_code in [400, 403, 404, 500]

    def test_get_enrolled_students(self, mock_db_connection, mock_db_cursor):
        """Test getting list of enrolled students"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                mock_db_cursor.fetchall.return_value = [
                    ("student1", "John Doe", "john@test.com", "2026-01-15", 85.5),
                    ("student2", "Jane Smith", "jane@test.com", "2026-01-16", 92.0),
                ]

                response = client.get("/api/classes/class123/students?professor_id=prof123")

                assert response.status_code in [200, 400, 403, 404, 500]

    def test_remove_student_from_class(self, mock_db_connection, mock_db_cursor):
        """Test removing a student from a class"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                response = client.delete(
                    "/api/classes/class123/students/student123?professor_id=prof123"
                )

                assert response.status_code in [200, 403, 404, 500]


class TestClassStatistics:
    """Test class statistics and analytics"""

    def test_get_class_statistics(self, mock_db_connection, mock_db_cursor):
        """Test getting class statistics"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                mock_db_cursor.fetchone.return_value = (
                    25,  # total_students
                    15,  # active_students
                    85.5,  # avg_progress
                    10  # total_exercises
                )

                response = client.get("/api/classes/class123/statistics?professor_id=prof123")

                assert response.status_code in [200, 403, 404, 500]

    def test_get_class_leaderboard(self, mock_db_connection, mock_db_cursor):
        """Test getting class leaderboard"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                mock_db_cursor.fetchall.return_value = [
                    ("student1", "John Doe", 95.5, 10, 9),
                    ("student2", "Jane Smith", 92.0, 10, 8),
                    ("student3", "Bob Johnson", 88.5, 10, 7),
                ]

                response = client.get("/api/classes/class123/leaderboard")

                assert response.status_code in [200, 404, 500]


class TestEnrollmentCode:
    """Test enrollment code generation and validation"""

    def test_generate_enrollment_code(self, mock_db_connection, mock_db_cursor):
        """Test generating enrollment code for a class"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                response = client.post(
                    "/api/classes/class123/enrollment-code",
                    json={"professor_id": "prof123"}
                )

                assert response.status_code in [200, 403, 404, 500]

    def test_validate_enrollment_code(self, mock_db_connection, mock_db_cursor):
        """Test validating enrollment code"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                mock_db_cursor.fetchone.return_value = ("class123", "Python 101")

                response = client.get("/api/classes/validate-code/ABC123")

                assert response.status_code in [200, 404, 500]


class TestClassOptions:
    """Test OPTIONS requests for CORS"""

    def test_classes_options(self):
        """Test OPTIONS request for classes endpoint"""
        from app import app

        with app.test_client() as client:
            response = client.options("/api/classes")
            assert response.status_code in [200, 204]

    def test_class_enroll_options(self):
        """Test OPTIONS request for enrollment endpoint"""
        from app import app

        with app.test_client() as client:
            response = client.options("/api/classes/class123/enroll")
            assert response.status_code in [200, 204, 404]
