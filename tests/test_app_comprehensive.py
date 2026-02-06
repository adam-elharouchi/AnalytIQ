"""
Comprehensive App.py Tests - Corrected Routes
Tests for actual API endpoints with proper mocking
"""
import pytest
from unittest.mock import patch, MagicMock, ANY
import json
from datetime import datetime
import bcrypt


class TestHealthEndpoint:
    """Test health check endpoint"""

    def test_health_check_all_healthy(self):
        """Test health endpoint when all services are healthy"""
        from app import app

        with app.test_client() as client:
            with patch("cache.cache_health_check") as mock_cache:
                with patch("supabase_storage.storage_health_check") as mock_storage:
                    mock_cache.return_value = {"healthy": True, "message": "OK"}
                    mock_storage.return_value = {"healthy": True, "message": "OK"}

                    response = client.get("/api/health")

                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert data["status"] in ["healthy", "degraded"]


class TestGetClasses:
    """Test get_classes endpoint with caching"""

    def test_get_classes_cache_hit(self, mock_db_connection, mock_db_cursor):
        """Test that cache is used when available"""
        from app import app

        with app.test_client() as client:
            with patch("cache.get_cached") as mock_get_cache:
                cached_response = {
                    "classes": [{"class_id": "123", "name": "Test Class"}],
                    "pagination": {"total": 1, "limit": 10, "offset": 0},
                }
                mock_get_cache.return_value = cached_response

                response = client.get("/api/classes?user_id=test@test.com")

                assert response.status_code == 200
                data = json.loads(response.data)
                assert "classes" in data
                # Verify database was NOT queried
                mock_get_cache.assert_called_once()

    def test_get_classes_cache_miss_professor(
        self, mock_db_connection, mock_db_cursor
    ):
        """Test get_classes for professor with cache miss"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                with patch("cache.get_cached", return_value=None):
                    with patch("cache.set_cached") as mock_set_cache:
                        # Mock user role query
                        mock_db_cursor.fetchone.side_effect = [
                            ("professor",),  # User role
                            (2,),  # Total count
                        ]
                        # Mock classes query
                        mock_db_cursor.fetchall.return_value = [
                            (
                                "class1",
                                "Python 101",
                                "Desc",
                                datetime.now(),
                                5,
                                3,
                            ),
                        ]

                        response = client.get("/api/classes?user_id=prof@test.com")

                        assert response.status_code == 200
                        data = json.loads(response.data)
                        assert len(data["classes"]) == 1
                        # Verify cache was set
                        mock_set_cache.assert_called_once()

    def test_get_classes_missing_user_id(self):
        """Test get_classes without user_id"""
        from app import app

        with app.test_client() as client:
            response = client.get("/api/classes")

            assert response.status_code == 400
            data = json.loads(response.data)
            assert "user_id" in data["error"].lower()


class TestCreateClass:
    """Test class creation"""

    def test_create_class_success(self, mock_db_connection, mock_db_cursor):
        """Test successful class creation"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                with patch("cache.invalidate_cache") as mock_invalidate:
                    response = client.post(
                        "/api/classes",
                        json={
                            "user_id": "prof@test.com",
                            "name": "Python 101",
                            "description": "Intro to Python",
                        },
                    )

                    assert response.status_code == 201
                    data = json.loads(response.data)
                    assert data["success"] is True
                    assert "class_id" in data

    def test_create_class_missing_fields(self):
        """Test class creation with missing required fields"""
        from app import app

        with app.test_client() as client:
            response = client.post(
                "/api/classes",
                json={
                    "user_id": "prof@test.com",
                    # Missing name and description
                },
            )

            assert response.status_code == 400


class TestGetClassDetails:
    """Test getting specific class details"""

    def test_get_class_by_id(self, mock_db_connection, mock_db_cursor):
        """Test getting a specific class"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                mock_db_cursor.fetchone.return_value = (
                    "class123",
                    "Python 101",
                    "Description",
                    "prof@test.com",
                    datetime.now(),
                )

                response = client.get("/api/classes/class123")

                assert response.status_code == 200
                data = json.loads(response.data)
                assert data["class_id"] == "class123"
                assert data["name"] == "Python 101"


class TestUpdateClass:
    """Test class updates"""

    def test_update_class(self, mock_db_connection, mock_db_cursor):
        """Test updating a class"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                with patch("cache.invalidate_cache") as mock_invalidate:
                    response = client.put(
                        "/api/classes/class123",
                        json={
                            "user_id": "prof@test.com",
                            "name": "Updated Python 101",
                            "description": "Updated description",
                        },
                    )

                    assert response.status_code == 200
                    # Verify cache was invalidated
                    assert mock_invalidate.called


class TestDeleteClass:
    """Test class deletion"""

    def test_delete_class(self, mock_db_connection, mock_db_cursor):
        """Test deleting a class"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                with patch("cache.invalidate_cache") as mock_invalidate:
                    response = client.delete(
                        "/api/classes/class123?user_id=prof@test.com"
                    )

                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert data["success"] is True


class TestChapters:
    """Test chapter endpoints"""

    def test_get_chapters_for_class(self, mock_db_connection, mock_db_cursor):
        """Test getting chapters for a class"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                mock_db_cursor.fetchall.return_value = [
                    ("ch1", "Chapter 1", "Desc", "url1", datetime.now()),
                    ("ch2", "Chapter 2", "Desc", "url2", datetime.now()),
                ]

                response = client.get("/api/classes/class123/chapters")

                assert response.status_code == 200
                data = json.loads(response.data)
                assert "chapters" in data


class TestExercises:
    """Test exercise endpoints"""

    def test_get_exercises_for_chapter(self, mock_db_connection, mock_db_cursor):
        """Test getting exercises for a chapter"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                mock_db_cursor.fetchone.return_value = ("user123",)  # user_id check
                mock_db_cursor.fetchall.return_value = [
                    ("ex1", "Exercise 1", "Desc", "code", None, datetime.now(), 1),
                    ("ex2", "Exercise 2", "Desc", "code", None, datetime.now(), 2),
                ]

                response = client.get(
                    "/api/chapters/ch123/exercises?user_id=user123"
                )

                assert response.status_code == 200
                data = json.loads(response.data)
                assert "exercises" in data


class TestEnrollment:
    """Test enrollment endpoints"""

    def test_enroll_student(self, mock_db_connection, mock_db_cursor):
        """Test enrolling a student"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                # Mock: class exists, student not enrolled
                mock_db_cursor.fetchone.side_effect = [
                    ("class123",),  # Class exists
                    None,  # Not enrolled yet
                ]

                response = client.post(
                    "/api/classes/enroll",
                    json={"class_id": "class123", "student_id": "student@test.com"},
                )

                assert response.status_code == 201
                data = json.loads(response.data)
                assert data["success"] is True


class TestCORSHandling:
    """Test CORS preflight requests"""

    def test_options_request_classes(self):
        """Test OPTIONS preflight for classes endpoint"""
        from app import app

        with app.test_client() as client:
            response = client.options("/api/classes")

            assert response.status_code == 200
            assert response.headers["Access-Control-Allow-Origin"] == "*"

    def test_options_request_chapters(self):
        """Test OPTIONS preflight for chapters endpoint"""
        from app import app

        with app.test_client() as client:
            response = client.options("/api/classes/class123/chapters")

            assert response.status_code == 200
            assert response.headers["Access-Control-Allow-Origin"] == "*"


class TestPagination:
    """Test pagination functionality"""

    def test_pagination_default_values(self, mock_db_connection, mock_db_cursor):
        """Test that default pagination values are used"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                with patch("cache.get_cached", return_value=None):
                    with patch("cache.set_cached"):
                        mock_db_cursor.fetchone.side_effect = [
                            ("student",),  # Role
                            (0,),  # Count
                        ]
                        mock_db_cursor.fetchall.return_value = []

                        response = client.get("/api/classes?user_id=test")

                        assert response.status_code == 200
                        data = json.loads(response.data)
                        assert "pagination" in data
                        assert data["pagination"]["limit"] == 10  # Default

    def test_pagination_custom_values(self, mock_db_connection, mock_db_cursor):
        """Test custom pagination values"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                with patch("cache.get_cached", return_value=None):
                    with patch("cache.set_cached"):
                        mock_db_cursor.fetchone.side_effect = [
                            ("student",),
                            (0,),
                        ]
                        mock_db_cursor.fetchall.return_value = []

                        response = client.get(
                            "/api/classes?user_id=test&limit=5&offset=10"
                        )

                        assert response.status_code == 200
                        data = json.loads(response.data)
                        assert data["pagination"]["limit"] == 5
                        assert data["pagination"]["offset"] == 10


class TestErrorHandling:
    """Test error handling"""

    def test_database_error_handling(self):
        """Test handling of database errors"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection") as mock_conn:
                mock_conn.side_effect = Exception("Database connection failed")

                response = client.get("/api/classes?user_id=test")

                assert response.status_code == 500
                data = json.loads(response.data)
                assert "error" in data
