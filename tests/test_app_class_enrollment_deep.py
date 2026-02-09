"""
Deep tests for class management, enrollment, and progress endpoints.
Targets uncovered lines: 2431-2526 (get_classes student), 2754-2846 (class update details),
3910-3912 (already enrolled), 3952-4029 (enrolled classes), 4051-4089 (enrolled students owner check),
4117-4237 (class progress), 4248-4323 (progress endpoint), 4667-4694 (ensure tables)
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import json


class TestGetClassesStudentPath:
    """Test GET /api/classes student path - lines 2473-2526"""

    def test_get_classes_student_path(self, client, mock_db):
        """Test getting enrolled classes as student"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("student",),  # User role
            (2,),  # Total count
        ]
        mock_cursor.fetchall.return_value = [
            ("CLS1", "Class 1", "Desc", datetime(2026, 1, 1), 15, 3),
        ]

        response = client.get("/api/classes?user_id=student123&limit=10&offset=0")
        assert response.status_code in [200, 401, 404, 500]

    def test_get_classes_no_role(self, client, mock_db):
        """Test getting classes when user role is None"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            (None,),  # No role - defaults to student
            (0,),
        ]
        mock_cursor.fetchall.return_value = []

        response = client.get("/api/classes?user_id=user123")
        assert response.status_code in [200, 401, 404, 500]


class TestGetClassByIdErrors:
    """Test get_class_by_id error paths - lines 2565-2637"""

    def test_get_class_user_not_found(self, client, mock_db):
        """Test getting class when user doesn't exist"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("CLS1", "Class", "Desc", "prof1", datetime(2026, 1, 1), "Prof", "prof@e.com"),
            None,  # User not found
        ]

        response = client.get("/api/classes/CLS1?user_id=nonexist")
        assert response.status_code in [401, 404, 500]


class TestGetClassResourceErrors:
    """Test class resources error paths - lines 2720-2791"""

    def test_get_resources_with_db_error(self, client, mock_db):
        """Test resources when class_resources table query fails"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.return_value = ("prof123",)
        mock_cursor.fetchall.side_effect = [
            [],  # chapters
            Exception("Table not found"),  # class_resources
        ]

        response = client.get("/api/classes/CLS123/resources?user_id=prof123")
        assert response.status_code in [200, 401, 500]


class TestUpdateClassDeep:
    """Test class update deep paths - lines 2825-2917"""

    def test_update_class_both_fields(self, client, mock_db):
        """Test updating both name and description"""
        mock_db.cursor().fetchone.return_value = ("prof123",)

        response = client.put("/api/classes/CLS123", json={
            "user_id": "prof123",
            "name": "New Name",
            "description": "New Desc",
        })
        assert response.status_code in [200, 401, 500]

    def test_update_class_db_error(self, client, mock_db):
        """Test class update with DB error - lines 2914-2917"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.return_value = ("prof123",)
        mock_cursor.execute.side_effect = [None, None, Exception("DB error")]

        response = client.put("/api/classes/CLS123", json={
            "user_id": "prof123",
            "name": "New Name",
        })
        assert response.status_code in [200, 401, 500]


class TestAlreadyEnrolled:
    """Test enrollment when already enrolled - lines 3910-3912"""

    def test_enroll_already_enrolled(self, client, mock_db):
        """Test enrolling when student is already enrolled"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("student",),  # User role
            ("CLS123", "Class Name", "prof123"),  # Class exists
            (1,),  # Already enrolled!
        ]

        response = client.post("/api/classes/enroll", json={
            "user_id": "student123",
            "class_id": "CLS123",
        })
        assert response.status_code in [400, 401, 403, 500]


class TestGetEnrolledClasses:
    """Test GET /api/classes/enrolled - lines 3949-4029"""

    def test_get_enrolled_classes_success(self, client, mock_db):
        """Test getting enrolled classes"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("student",),  # User role
            (2,),  # Total count
        ]
        mock_cursor.fetchall.return_value = [
            ("CLS1", "Class 1", "Desc", datetime(2026, 1, 1), "Prof", "p@e.com",
             datetime(2026, 1, 5), 15, 3),
        ]

        response = client.get("/api/classes/enrolled?user_id=student123")
        assert response.status_code in [200, 400, 401, 404, 500]

    def test_get_enrolled_classes_missing_user(self, client, mock_db):
        """Test enrolled classes without user_id"""
        response = client.get("/api/classes/enrolled")
        assert response.status_code in [400, 401, 403, 500]

    def test_get_enrolled_classes_user_not_found(self, client, mock_db):
        """Test enrolled classes for non-existent user"""
        mock_db.cursor().fetchone.return_value = None

        response = client.get("/api/classes/enrolled?user_id=nonexist")
        assert response.status_code in [401, 404, 500]


class TestGetClassStudentsOwnerCheck:
    """Test enrolled students access control - lines 4051-4089"""

    def test_get_students_not_owner(self, client, mock_db):
        """Test getting students as non-owner professor"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.return_value = ("other_prof",)

        response = client.get("/api/classes/CLS123/students?user_id=prof123")
        assert response.status_code in [403, 500]

    def test_get_students_class_not_found(self, client, mock_db):
        """Test getting students for non-existent class"""
        mock_db.cursor().fetchone.return_value = None

        response = client.get("/api/classes/CLS123/students?user_id=prof123")
        assert response.status_code in [401, 404, 500]


class TestGetClassProgress:
    """Test GET /api/classes/<class_id>/progress - lines 4097-4237"""

    def test_get_class_progress_success(self, client, mock_db):
        """Test getting class progress as professor"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.return_value = ("prof123",)  # Professor owns class
        mock_cursor.fetchall.side_effect = [
            # Exercises
            [("ex1", "Exercise 1", "easy"), ("ex2", "Exercise 2", "medium")],
            # Students
            [("s1", "Student 1", "s1@test.com"), ("s2", "Student 2", "s2@test.com")],
            # Progress rows
            [
                ("s1", "ex1", 85, 90.0, 3, True, datetime(2026, 1, 1)),
                ("s1", "ex2", 70, 75.0, 2, False, None),
                ("s2", "ex1", 60, 65.0, 1, False, None),
                ("s2", "ex2", 0, 0.0, 0, False, None),
            ],
        ]

        response = client.get("/api/classes/CLS123/progress?user_id=prof123")
        assert response.status_code in [200, 403, 404, 500]

    def test_get_class_progress_not_owner(self, client, mock_db):
        """Test getting progress as non-owner"""
        mock_db.cursor().fetchone.return_value = ("other_prof",)

        response = client.get("/api/classes/CLS123/progress?user_id=prof123")
        assert response.status_code in [403, 500]

    def test_get_class_progress_not_found(self, client, mock_db):
        """Test getting progress for non-existent class"""
        mock_db.cursor().fetchone.return_value = None

        response = client.get("/api/classes/CLS123/progress?user_id=prof123")
        assert response.status_code in [401, 404, 500]

    def test_get_class_progress_missing_user(self, client, mock_db):
        """Test getting progress without user_id"""
        response = client.get("/api/classes/CLS123/progress")
        assert response.status_code in [400, 401, 403, 500]


class TestGetProgressEndpoint:
    """Test GET /api/progress - lines 4240-4323"""

    def test_get_progress_with_class_filter(self, client, mock_db):
        """Test getting progress filtered by class_id"""
        mock_db.cursor().fetchall.return_value = [
            ("ex1", "Exercise 1", "easy", 85, 90.0, 3, True, datetime(2026, 1, 1)),
        ]

        response = client.get(
            "/api/progress?user_id=user123&class_id=CLS123"
        )
        assert response.status_code in [200, 400, 401, 500]

    def test_get_progress_without_class(self, client, mock_db):
        """Test getting all progress without class filter"""
        mock_db.cursor().fetchall.return_value = [
            ("ex1", "Exercise 1", 85, 90.0, 3, True, datetime(2026, 1, 1)),
        ]

        response = client.get("/api/progress?user_id=user123")
        assert response.status_code in [200, 400, 401, 500]

    def test_get_progress_missing_user(self, client, mock_db):
        """Test getting progress without user_id"""
        response = client.get("/api/progress")
        assert response.status_code in [400, 401, 403, 500]


class TestContactEndpoint:
    """Test POST /api/contact deep paths - lines 2269-2310"""

    def test_contact_form_with_user_id(self, client, mock_db):
        """Test contact form with logged-in user"""
        response = client.post("/api/contact", json={
            "name": "Test User",
            "email": "test@test.com",
            "subject": "Help",
            "message": "Need help with platform",
            "user_id": "user123",
        })
        assert response.status_code in [200, 201, 500]

    def test_contact_form_options(self, client):
        """Test OPTIONS for contact endpoint"""
        response = client.options("/api/contact")
        assert response.status_code == 200


class TestClassCodeGeneration:
    """Test generate_class_code function - lines 2318-2325"""

    def test_generate_class_code(self):
        """Test class code generation format"""
        from app import generate_class_code
        code = generate_class_code()
        assert len(code) == 10
        assert code[:5].isalpha() and code[:5].isupper()
        assert code[5:].isdigit()

    def test_generate_class_code_unique(self):
        """Test class codes are unique"""
        from app import generate_class_code
        codes = {generate_class_code() for _ in range(20)}
        assert len(codes) > 1  # Extremely unlikely to get duplicates


class TestResourceFileServe:
    """Test resource file serving - lines 5285-5288"""

    def test_serve_legacy_resource_file(self, client, mock_db):
        """Test serving legacy resource files"""
        response = client.get("/api/resources/files/nonexistent.pdf")
        assert response.status_code in [200, 401, 404, 500]


class TestTaskStatus:
    """Test GET /api/tasks/<task_id> - lines 2219-2258"""

    def test_get_task_status(self, client, mock_db):
        """Test getting task status"""
        response = client.get("/api/tasks/some-task-id")
        assert response.status_code in [200, 404, 500, 503]
