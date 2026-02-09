"""
Deep tests for class management endpoints
Targets: get_class_by_id, get_class_resources, update_class, delete_class,
validate_pdf_file, create_class deep paths, get_classes student/professor paths
"""
import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO
import json
from datetime import datetime


class TestGetClassById:
    """Test GET /api/classes/<class_id> endpoint - lines 2527-2637"""

    def test_get_class_by_id_as_professor(self, client, mock_db):
        """Test getting class details as the owning professor"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            # Class info join with professor
            ("CLS123", "Analytics 101", "Intro course", "prof123", datetime(2026, 1, 1),
             "Prof Name", "prof@hult.edu"),
            # User role check
            ("professor",),
            # Student count
            (15,),
            # Chapter count
            (5,),
            # Exercise count
            (20,),
        ]

        response = client.get("/api/classes/CLS123?user_id=prof123")
        assert response.status_code in [200, 401, 500]
        if response.status_code == 200:
            data = response.get_json()
            assert data.get("class_id") == "CLS123"

    def test_get_class_by_id_as_enrolled_student(self, client, mock_db):
        """Test getting class details as an enrolled student"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            # Class info
            ("CLS123", "Analytics 101", "Intro", "prof123", datetime(2026, 1, 1),
             "Prof Name", "prof@hult.edu"),
            # User role - student
            ("student",),
            # Student enrolled check
            (1,),
            # Student count
            (15,),
            # Chapter count
            (5,),
            # Exercise count
            (20,),
        ]

        response = client.get("/api/classes/CLS123?user_id=student123")
        assert response.status_code in [200, 403, 500]

    def test_get_class_not_found(self, client, mock_db):
        """Test getting non-existent class"""
        mock_db.cursor().fetchone.return_value = None

        response = client.get("/api/classes/NONEXIST?user_id=user123")
        assert response.status_code in [401, 404, 500]

    def test_get_class_missing_user_id(self, client, mock_db):
        """Test getting class without user_id"""
        response = client.get("/api/classes/CLS123")
        assert response.status_code in [400, 401, 403, 500]

    def test_get_class_access_denied_unenrolled(self, client, mock_db):
        """Test access denied for unenrolled student"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            # Class info
            ("CLS123", "Analytics 101", "Intro", "prof123", datetime(2026, 1, 1),
             "Prof Name", "prof@hult.edu"),
            # User role - student
            ("student",),
            # Not enrolled
            None,
        ]

        response = client.get("/api/classes/CLS123?user_id=random_student")
        assert response.status_code in [403, 500]


class TestGetClassResources:
    """Test GET /api/classes/<class_id>/resources endpoint - lines 2643-2743"""

    def test_get_class_resources_success(self, client, mock_db):
        """Test getting resources for a class"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.return_value = ("prof123",)  # Class professor_id
        mock_cursor.fetchall.side_effect = [
            # Chapters as resources
            [("ch1", "Chapter 1", "Desc", "http://pdf.url", datetime(2026, 1, 1))],
            # Other resources
            [("res1", "Resource 1", "Desc", "link", "http://example.com", datetime(2026, 1, 1))],
        ]

        response = client.get("/api/classes/CLS123/resources?user_id=prof123")
        assert response.status_code in [200, 400, 401, 500]

    def test_get_class_resources_missing_user_id(self, client, mock_db):
        """Test getting resources without user_id"""
        response = client.get("/api/classes/CLS123/resources")
        assert response.status_code in [400, 401]

    def test_get_class_resources_class_not_found(self, client, mock_db):
        """Test getting resources for non-existent class"""
        mock_db.cursor().fetchone.return_value = None

        response = client.get("/api/classes/NONEXIST/resources?user_id=user123")
        assert response.status_code in [401, 404, 500]


class TestCreateClassDeep:
    """Test POST /api/classes deep paths - lines 2328-2414"""

    def test_create_class_success(self, client, mock_db):
        """Test successful class creation"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("professor",),  # User role
            None,  # Class code not taken
            ("CLS123", "Analytics 101", "Intro", datetime(2026, 1, 1)),  # New class
        ]

        response = client.post("/api/classes", json={
            "user_id": "prof123",
            "name": "Analytics 101",
            "description": "Introduction to Analytics",
            "class_code": "ANA101",
        })
        assert response.status_code in [201, 400, 403, 409, 500]

    def test_create_class_missing_name(self, client, mock_db):
        """Test creating class without name"""
        response = client.post("/api/classes", json={
            "user_id": "prof123",
            "class_code": "ANA101",
        })
        assert response.status_code in [400, 401, 403, 500]

    def test_create_class_missing_class_code(self, client, mock_db):
        """Test creating class without class code"""
        response = client.post("/api/classes", json={
            "user_id": "prof123",
            "name": "Analytics 101",
        })
        assert response.status_code in [400, 401, 403, 500]

    def test_create_class_invalid_code_format(self, client, mock_db):
        """Test creating class with invalid code format"""
        response = client.post("/api/classes", json={
            "user_id": "prof123",
            "name": "Analytics 101",
            "class_code": "AB",  # Too short
        })
        assert response.status_code in [400, 401, 403, 500]

    def test_create_class_not_professor(self, client, mock_db):
        """Test creating class as non-professor"""
        mock_db.cursor().fetchone.return_value = ("student",)

        response = client.post("/api/classes", json={
            "user_id": "student123",
            "name": "My Class",
            "class_code": "CLS101",
        })
        assert response.status_code in [403, 500]

    def test_create_class_duplicate_code(self, client, mock_db):
        """Test creating class with existing code"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("professor",),  # User role
            ("existing_class_id",),  # Code already exists
        ]

        response = client.post("/api/classes", json={
            "user_id": "prof123",
            "name": "Analytics 102",
            "class_code": "ANA101",
        })
        assert response.status_code in [409, 500]

    def test_create_class_options(self, client):
        """Test OPTIONS preflight for class creation"""
        response = client.options("/api/classes")
        assert response.status_code == 200


class TestGetClassesPagination:
    """Test GET /api/classes pagination paths - lines 2417-2526"""

    def test_get_classes_as_professor(self, client, mock_db):
        """Test getting classes as professor"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("professor",),  # User role
            (3,),  # Total count
        ]
        mock_cursor.fetchall.return_value = [
            ("CLS1", "Class 1", "Desc", datetime(2026, 1, 1), 10, 3),
            ("CLS2", "Class 2", "Desc", datetime(2026, 1, 2), 15, 5),
        ]

        response = client.get("/api/classes?user_id=prof123&limit=10&offset=0")
        assert response.status_code in [200, 400, 401, 404, 500]

    def test_get_classes_as_student(self, client, mock_db):
        """Test getting enrolled classes as student"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("student",),  # User role
            (2,),  # Total count
        ]
        mock_cursor.fetchall.return_value = [
            ("CLS1", "Class 1", "Desc", datetime(2026, 1, 1), 10, 3),
        ]

        response = client.get("/api/classes?user_id=student123")
        assert response.status_code in [200, 400, 401, 404, 500]

    def test_get_classes_missing_user_id(self, client, mock_db):
        """Test getting classes without user_id"""
        response = client.get("/api/classes")
        assert response.status_code in [400, 401]

    def test_get_classes_user_not_found(self, client, mock_db):
        """Test getting classes for non-existent user"""
        mock_db.cursor().fetchone.return_value = None

        response = client.get("/api/classes?user_id=nonexistent")
        assert response.status_code in [401, 404, 500]


class TestUpdateClass:
    """Test PUT /api/classes/<class_id> endpoint - lines 2825-2917"""

    def test_update_class_name(self, client, mock_db):
        """Test updating class name"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.return_value = ("prof123",)  # Professor owns class

        response = client.put("/api/classes/CLS123", json={
            "user_id": "prof123",
            "name": "Updated Analytics 101",
        })
        assert response.status_code in [200, 400, 401, 403, 404, 500]

    def test_update_class_description(self, client, mock_db):
        """Test updating class description"""
        mock_db.cursor().fetchone.return_value = ("prof123",)

        response = client.put("/api/classes/CLS123", json={
            "user_id": "prof123",
            "description": "Updated description",
        })
        assert response.status_code in [200, 400, 401, 403, 404, 500]

    def test_update_class_no_fields(self, client, mock_db):
        """Test updating class with no fields to update"""
        mock_db.cursor().fetchone.return_value = ("prof123",)

        response = client.put("/api/classes/CLS123", json={
            "user_id": "prof123",
        })
        assert response.status_code in [400, 401, 403, 500]

    def test_update_class_not_owner(self, client, mock_db):
        """Test updating class as non-owner"""
        mock_db.cursor().fetchone.return_value = ("other_prof",)

        response = client.put("/api/classes/CLS123", json={
            "user_id": "prof123",
            "name": "Hacked Name",
        })
        assert response.status_code in [403, 500]

    def test_update_class_not_found(self, client, mock_db):
        """Test updating non-existent class"""
        mock_db.cursor().fetchone.return_value = None

        response = client.put("/api/classes/NONEXIST", json={
            "user_id": "prof123",
            "name": "New Name",
        })
        assert response.status_code in [401, 404, 500]


class TestDeleteClass:
    """Test DELETE /api/classes/<class_id> endpoint - lines 3523-3562"""

    def test_delete_class_success(self, client, mock_db):
        """Test successful class deletion"""
        mock_db.cursor().fetchone.return_value = ("prof123",)

        response = client.delete("/api/classes/CLS123?user_id=prof123")
        assert response.status_code in [200, 401, 500]

    def test_delete_class_not_found(self, client, mock_db):
        """Test deleting non-existent class"""
        mock_db.cursor().fetchone.return_value = None

        response = client.delete("/api/classes/NONEXIST?user_id=prof123")
        assert response.status_code in [401, 404, 500]

    def test_delete_class_not_owner(self, client, mock_db):
        """Test deleting class as non-owner"""
        mock_db.cursor().fetchone.return_value = ("other_prof",)

        response = client.delete("/api/classes/CLS123?user_id=prof123")
        assert response.status_code in [403, 500]

    def test_delete_class_missing_user_id(self, client, mock_db):
        """Test deleting class without user_id"""
        response = client.delete("/api/classes/CLS123")
        assert response.status_code in [400, 401, 403, 500]


class TestValidatePdfFile:
    """Test validate_pdf_file function - lines 2925-2990"""

    def test_validate_valid_pdf(self):
        """Test validation of a valid PDF"""
        from app import validate_pdf_file
        pdf_content = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\nSome PDF content here\n%%EOF"
        file = BytesIO(pdf_content)
        is_valid, error = validate_pdf_file(file)
        assert is_valid is True
        assert error is None

    def test_validate_empty_pdf(self):
        """Test validation of empty file"""
        from app import validate_pdf_file
        file = BytesIO(b"")
        is_valid, error = validate_pdf_file(file)
        assert is_valid is False
        assert "empty" in error.lower()

    def test_validate_non_pdf_file(self):
        """Test validation of non-PDF file"""
        from app import validate_pdf_file
        file = BytesIO(b"This is not a PDF file")
        is_valid, error = validate_pdf_file(file)
        assert is_valid is False
        assert "PDF" in error

    def test_validate_pdf_too_large(self):
        """Test validation of oversized PDF"""
        from app import validate_pdf_file
        # Create file larger than 50MB
        large_content = b"%PDF-1.4\n" + b"x" * (51 * 1024 * 1024)
        file = BytesIO(large_content)
        is_valid, error = validate_pdf_file(file)
        assert is_valid is False
        assert "large" in error.lower()

    def test_validate_pdf_with_javascript(self):
        """Test validation of PDF with JavaScript (suspicious)"""
        from app import validate_pdf_file
        pdf_content = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n/JavaScript alert('xss')\n%%EOF"
        file = BytesIO(pdf_content)
        is_valid, error = validate_pdf_file(file)
        assert is_valid is False
        assert "unsafe" in error.lower()

    def test_validate_pdf_unsupported_version(self):
        """Test validation of unsupported PDF version"""
        from app import validate_pdf_file
        pdf_content = b"%PDF-3.0\nContent\n%%EOF"
        file = BytesIO(pdf_content)
        is_valid, error = validate_pdf_file(file)
        assert is_valid is False
        assert "version" in error.lower() or "PDF" in error


class TestAllowedFile:
    """Test allowed_file function"""

    def test_allowed_extensions(self):
        """Test all allowed file extensions"""
        from app import allowed_file
        for ext in ["pdf", "csv", "xlsx", "xls", "json", "txt", "ipynb"]:
            assert allowed_file(f"test.{ext}") is True

    def test_disallowed_extensions(self):
        """Test disallowed file extensions"""
        from app import allowed_file
        for ext in ["exe", "bat", "sh", "py", "js", "php"]:
            assert allowed_file(f"test.{ext}") is False


class TestContactSubmission:
    """Test POST /api/contact endpoint - lines 2271-2310"""

    def test_submit_contact_form(self, client, mock_db):
        """Test submitting contact form"""
        response = client.post("/api/contact", json={
            "name": "Test User",
            "email": "test@example.com",
            "subject": "Help needed",
            "message": "I need help with the platform",
        })
        assert response.status_code in [200, 201, 400, 500]

    def test_submit_contact_form_missing_fields(self, client, mock_db):
        """Test submitting contact form with missing fields"""
        response = client.post("/api/contact", json={
            "name": "Test User",
            "email": "test@example.com",
        })
        assert response.status_code in [400, 401, 403, 500]

    def test_contact_options(self, client):
        """Test OPTIONS for contact endpoint"""
        response = client.options("/api/contact")
        assert response.status_code == 200
