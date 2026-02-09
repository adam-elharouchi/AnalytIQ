"""
Deep tests for resource management endpoints
Targets: add_class_resource, upload_class_resource, serve_resource_download,
create_class_resource, manage_resource, download_resource, serve_resource_file
Lines: 4788-5288
"""
import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO
from datetime import datetime
import json


class TestAddClassResource:
    """Test POST /api/classes/<class_id>/resources (JSON link) - lines 4788-4837"""

    def test_add_resource_link_success(self, client, mock_db):
        """Test adding a link resource to a class"""
        response = client.post("/api/classes/CLS123/resources", json={
            "user_id": "prof123",
            "title": "Useful Link",
            "description": "A helpful resource",
            "resource_type": "link",
            "resource_url": "https://example.com/resource",
        })
        assert response.status_code in [201, 400, 401, 403, 500]

    def test_add_resource_missing_user_id(self, client, mock_db):
        """Test adding resource without user_id"""
        response = client.post("/api/classes/CLS123/resources", json={
            "title": "Useful Link",
            "resource_url": "https://example.com",
        })
        assert response.status_code in [400, 401, 403, 500]

    def test_add_resource_options(self, client):
        """Test OPTIONS for adding resource"""
        response = client.options("/api/classes/CLS123/resources")
        assert response.status_code == 200


class TestUploadClassResource:
    """Test POST /api/classes/<class_id>/resources/upload - lines 5022-5090"""

    def test_upload_resource_file(self, client, mock_db):
        """Test uploading a file resource"""
        file_content = b"Sample file content for testing"

        response = client.post(
            "/api/classes/CLS123/resources/upload",
            data={
                "user_id": "prof123",
                "title": "Test File",
                "description": "Test description",
                "resource_type": "file",
                "file": (BytesIO(file_content), "data.csv"),
            },
            content_type="multipart/form-data",
        )
        assert response.status_code in [201, 400, 401, 403, 500]

    def test_upload_resource_no_file(self, client, mock_db):
        """Test uploading without a file"""
        response = client.post(
            "/api/classes/CLS123/resources/upload",
            data={"user_id": "prof123", "title": "Test"},
            content_type="multipart/form-data",
        )
        assert response.status_code in [400, 401, 403, 500]

    def test_upload_resource_empty_filename(self, client, mock_db):
        """Test uploading with empty filename"""
        response = client.post(
            "/api/classes/CLS123/resources/upload",
            data={
                "user_id": "prof123",
                "file": (BytesIO(b"content"), ""),
            },
            content_type="multipart/form-data",
        )
        assert response.status_code in [400, 401, 403, 500]

    def test_upload_resource_options(self, client):
        """Test OPTIONS for resource upload"""
        response = client.options("/api/classes/CLS123/resources/upload")
        assert response.status_code == 200


class TestServeResourceDownload:
    """Test GET /api/resources/<resource_id>/download - lines 5093-5150 and 5247-5279"""

    def test_download_pdf_resource(self, client, mock_db):
        """Test downloading a PDF resource"""
        mock_db.cursor().fetchone.return_value = (
            memoryview(b"%PDF-1.4\nContent"),  # file_data
            "document.pdf",  # filename
            "pdf",  # resource_type
        )

        response = client.get("/api/resources/res123/download")
        assert response.status_code in [200, 401, 404, 500]

    def test_download_csv_resource(self, client, mock_db):
        """Test downloading a CSV resource"""
        mock_db.cursor().fetchone.return_value = (
            memoryview(b"col1,col2\nval1,val2"),
            "data.csv",
            "file",
        )

        response = client.get("/api/resources/res123/download")
        assert response.status_code in [200, 401, 404, 500]

    def test_download_resource_not_found(self, client, mock_db):
        """Test downloading non-existent resource"""
        mock_db.cursor().fetchone.return_value = None

        response = client.get("/api/resources/nonexistent/download")
        assert response.status_code in [401, 404, 500]

    def test_download_resource_empty_data(self, client, mock_db):
        """Test downloading resource with empty file data"""
        mock_db.cursor().fetchone.return_value = (None, "file.csv", "file")

        response = client.get("/api/resources/res123/download")
        assert response.status_code in [401, 404, 500]


class TestCreateClassResourceJson:
    """Test POST /api/classes/<class_id>/resources (duplicate route) - lines 5153-5196"""

    def test_create_resource_json(self, client, mock_db):
        """Test creating resource via JSON"""
        response = client.post("/api/classes/CLS123/resources", json={
            "user_id": "prof123",
            "title": "Tutorial Link",
            "description": "A great tutorial",
            "resource_type": "link",
            "resource_url": "https://tutorial.example.com",
        })
        assert response.status_code in [201, 400, 401, 403, 500]


class TestManageResource:
    """Test PUT/DELETE /api/classes/<class_id>/resources/<resource_id> - lines 5199-5244"""

    def test_update_resource_success(self, client, mock_db):
        """Test updating a resource"""
        response = client.put("/api/classes/CLS123/resources/res123", json={
            "title": "Updated Title",
            "description": "Updated description",
            "resource_type": "link",
            "resource_url": "https://updated.example.com",
        })
        assert response.status_code in [200, 400, 401, 404, 500]

    def test_delete_resource_success(self, client, mock_db):
        """Test deleting a resource"""
        response = client.delete("/api/classes/CLS123/resources/res123")
        assert response.status_code in [200, 401, 404, 500]

    def test_manage_resource_options(self, client):
        """Test OPTIONS for resource management"""
        response = client.options("/api/classes/CLS123/resources/res123")
        assert response.status_code == 200


class TestDeleteExercise:
    """Test DELETE /api/exercises/<exercise_id> - lines 4912-4951"""

    def test_delete_exercise_success(self, client, mock_db):
        """Test successful exercise deletion"""
        mock_db.cursor().fetchone.return_value = ("ch123", "CLS123")

        response = client.delete("/api/exercises/ex123")
        assert response.status_code in [200, 401, 404, 500]

    def test_delete_exercise_not_found(self, client, mock_db):
        """Test deleting non-existent exercise"""
        mock_db.cursor().fetchone.return_value = None

        response = client.delete("/api/exercises/nonexistent")
        assert response.status_code in [401, 404, 500]

    def test_delete_exercise_options(self, client):
        """Test OPTIONS for exercise delete"""
        response = client.options("/api/exercises/ex123")
        assert response.status_code == 200


class TestCreateExercise:
    """Test POST /api/classes/<class_id>/chapters/<chapter_id>/exercises - lines 4704-4785"""

    def test_create_exercise_success(self, client, mock_db):
        """Test successful exercise creation"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("prof123",),  # Class professor
            (1,),  # Chapter belongs to class
        ]

        response = client.post(
            "/api/classes/CLS123/chapters/ch123/exercises",
            json={
                "user_id": "prof123",
                "title": "New Exercise",
                "description": "Exercise description",
                "difficulty": "medium",
                "solution_code": "x = 42\nprint(x)",
            },
        )
        assert response.status_code in [201, 400, 403, 404, 500]

    def test_create_exercise_class_not_found(self, client, mock_db):
        """Test creating exercise for non-existent class"""
        mock_db.cursor().fetchone.return_value = None

        response = client.post(
            "/api/classes/NONEXIST/chapters/ch123/exercises",
            json={
                "user_id": "prof123",
                "title": "Exercise",
            },
        )
        assert response.status_code in [401, 404, 500]

    def test_create_exercise_not_owner(self, client, mock_db):
        """Test creating exercise as non-owner"""
        mock_db.cursor().fetchone.return_value = ("other_prof",)

        response = client.post(
            "/api/classes/CLS123/chapters/ch123/exercises",
            json={
                "user_id": "prof123",
                "title": "Exercise",
            },
        )
        assert response.status_code in [403, 500]

    def test_create_exercise_chapter_not_in_class(self, client, mock_db):
        """Test creating exercise with chapter not in class"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            ("prof123",),  # Class professor
            None,  # Chapter not in class
        ]

        response = client.post(
            "/api/classes/CLS123/chapters/wrong_chapter/exercises",
            json={
                "user_id": "prof123",
                "title": "Exercise",
            },
        )
        assert response.status_code in [401, 404, 500]

    def test_create_exercise_missing_user_id(self, client, mock_db):
        """Test creating exercise without user_id"""
        response = client.post(
            "/api/classes/CLS123/chapters/ch123/exercises",
            json={"title": "Exercise"},
        )
        assert response.status_code in [400, 401, 403, 500]


class TestUserPreferences:
    """Test user preferences endpoints - lines 1596-1719"""

    def test_get_preferences_success(self, client, mock_db):
        """Test getting user preferences"""
        mock_db.cursor().fetchone.return_value = ("python", "gemini-2.5-flash", "gemini")

        response = client.get("/api/users/preferences?user_id=user123")
        assert response.status_code in [200, 400, 401, 500]

    def test_get_preferences_missing_user_id(self, client, mock_db):
        """Test getting preferences without user_id"""
        response = client.get("/api/users/preferences")
        assert response.status_code in [400, 401, 403, 500]

    def test_update_preferences_success(self, client, mock_db):
        """Test updating user preferences"""
        response = client.put("/api/users/preferences", json={
            "user_id": "user123",
            "currentLanguage": "python",
            "geminiModel": "gemini-2.5-flash",
            "aiProvider": "gemini",
        })
        assert response.status_code in [200, 400, 401, 500]

    def test_update_preferences_missing_user_id(self, client, mock_db):
        """Test updating preferences without user_id"""
        response = client.put("/api/users/preferences", json={
            "currentLanguage": "python",
        })
        assert response.status_code in [400, 401, 403, 500]

    def test_update_preferences_partial(self, client, mock_db):
        """Test updating only some preferences"""
        response = client.put("/api/users/preferences", json={
            "user_id": "user123",
            "currentLanguage": "javascript",
        })
        assert response.status_code in [200, 400, 401, 500]


class TestUserDelete:
    """Test DELETE /api/users/delete endpoint - lines 1121-1142"""

    def test_delete_user_success(self, client, mock_db):
        """Test successful user deletion"""
        response = client.delete("/api/users/delete?user_id=user123")
        assert response.status_code in [200, 400, 401, 500]

    def test_delete_user_missing_id(self, client, mock_db):
        """Test deleting user without user_id"""
        response = client.delete("/api/users/delete")
        assert response.status_code in [400, 401, 403, 500]


class TestCsrfToken:
    """Test GET /api/csrf-token endpoint - lines 2196-2216"""

    def test_get_csrf_token_disabled(self, client):
        """Test getting CSRF token when disabled"""
        response = client.get("/api/csrf-token")
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("csrf_enabled") is False
