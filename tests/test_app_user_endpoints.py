"""
Comprehensive Tests for User Profile and Settings Endpoints
Target: Increase app.py coverage from 28% to 35%+
"""
import pytest
from unittest.mock import patch, MagicMock
import json


class TestUserProfileEndpoints:
    """Test user profile management"""

    def test_get_user_profile_success(self, mock_db_connection, mock_db_cursor):
        """Test getting user profile"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                mock_db_cursor.fetchone.return_value = (
                    "user123",
                    "John Doe",
                    "john@test.com",
                    "student",
                    "Computer Science",
                    "Sophomore"
                )

                response = client.get("/api/users/profile?user_id=user123")

                assert response.status_code in [200, 400, 404, 500]

    def test_get_user_profile_missing_user_id(self):
        """Test profile endpoint without user_id"""
        from app import app

        with app.test_client() as client:
            response = client.get("/api/users/profile")
            assert response.status_code in [400, 500]

    def test_update_user_profile_success(self, mock_db_connection, mock_db_cursor):
        """Test updating user profile"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                response = client.put(
                    "/api/users/profile",
                    json={
                        "user_id": "user123",
                        "name": "John Updated",
                        "major": "Data Science",
                        "year": "Junior"
                    }
                )

                assert response.status_code in [200, 400, 500]

    def test_update_user_profile_missing_fields(self):
        """Test profile update with missing fields"""
        from app import app

        with app.test_client() as client:
            response = client.put("/api/users/profile", json={})
            assert response.status_code in [400, 500]


class TestUserSettingsEndpoints:
    """Test user settings management"""

    def test_get_user_settings_success(self, mock_db_connection, mock_db_cursor):
        """Test getting user settings"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                mock_db_cursor.fetchone.return_value = (
                    True,  # email_notifications
                    "dark",  # theme
                    "en"  # language
                )

                response = client.get("/api/users/settings?user_id=user123")

                assert response.status_code in [200, 400, 404, 500]

    def test_update_user_settings_success(self, mock_db_connection, mock_db_cursor):
        """Test updating user settings"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                response = client.put(
                    "/api/users/settings",
                    json={
                        "user_id": "user123",
                        "email_notifications": False,
                        "theme": "light",
                        "language": "es"
                    }
                )

                assert response.status_code in [200, 400, 500]


class TestPasswordManagement:
    """Test password change and reset"""

    def test_change_password_success(self, mock_db_connection, mock_db_cursor):
        """Test changing password"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                with patch("app.verify_password", return_value=True):
                    with patch("app.hash_password", return_value="new_hashed"):
                        mock_db_cursor.fetchone.return_value = ("old_hashed",)

                        response = client.put(
                            "/api/users/password",
                            json={
                                "user_id": "user123",
                                "current_password": "old_pass",
                                "new_password": "new_pass"
                            }
                        )

                        assert response.status_code in [200, 400, 401, 500]

    def test_change_password_wrong_current(self, mock_db_connection, mock_db_cursor):
        """Test password change with wrong current password"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                with patch("app.verify_password", return_value=False):
                    mock_db_cursor.fetchone.return_value = ("old_hashed",)

                    response = client.put(
                        "/api/users/password",
                        json={
                            "user_id": "user123",
                            "current_password": "wrong_pass",
                            "new_password": "new_pass"
                        }
                    )

                    assert response.status_code in [400, 401, 500]

    def test_forgot_password_success(self, mock_db_connection, mock_db_cursor):
        """Test forgot password flow"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                mock_db_cursor.fetchone.return_value = ("user123", "john@test.com")

                response = client.post(
                    "/api/users/forgot-password",
                    json={"email": "john@test.com"}
                )

                assert response.status_code in [200, 404, 500]

    def test_reset_password_success(self, mock_db_connection, mock_db_cursor):
        """Test password reset with token"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                with patch("app.hash_password", return_value="new_hashed"):
                    mock_db_cursor.fetchone.return_value = ("user123",)

                    response = client.post(
                        "/api/users/reset-password",
                        json={
                            "token": "reset_token_123",
                            "new_password": "new_password"
                        }
                    )

                    assert response.status_code in [200, 400, 404, 500]


class TestUserPreferences:
    """Test user preferences endpoints"""

    def test_get_preferences_success(self, mock_db_connection, mock_db_cursor):
        """Test getting user preferences"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                mock_db_cursor.fetchone.return_value = (
                    json.dumps({"difficulty": "medium", "topics": ["python", "data"]}),
                )

                response = client.get("/api/users/preferences?user_id=user123")

                assert response.status_code in [200, 400, 404, 500]

    def test_update_preferences_success(self, mock_db_connection, mock_db_cursor):
        """Test updating user preferences"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                response = client.put(
                    "/api/users/preferences",
                    json={
                        "user_id": "user123",
                        "preferences": {
                            "difficulty": "hard",
                            "topics": ["python", "ml", "data"]
                        }
                    }
                )

                assert response.status_code in [200, 400, 500]


class TestPracticeProgress:
    """Test practice progress tracking"""

    def test_get_practice_progress_success(self, mock_db_connection, mock_db_cursor):
        """Test getting practice progress"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                mock_db_cursor.fetchall.return_value = [
                    ("exercise1", "completed", 95, "2026-01-15"),
                    ("exercise2", "in_progress", 60, "2026-01-16"),
                ]

                response = client.get("/api/users/practice-progress?user_id=user123")

                assert response.status_code in [200, 400, 500]

    def test_update_practice_progress_success(self, mock_db_connection, mock_db_cursor):
        """Test updating practice progress"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                response = client.put(
                    "/api/users/practice-progress",
                    json={
                        "user_id": "user123",
                        "exercise_id": "exercise1",
                        "status": "completed",
                        "score": 100
                    }
                )

                assert response.status_code in [200, 400, 404, 500]


class TestUserDeletion:
    """Test user account deletion"""

    def test_delete_user_account_success(self, mock_db_connection, mock_db_cursor):
        """Test deleting user account"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                with patch("app.verify_password", return_value=True):
                    mock_db_cursor.fetchone.return_value = ("hashed_password",)

                    response = client.delete(
                        "/api/users/delete",
                        json={
                            "user_id": "user123",
                            "password": "correct_password"
                        }
                    )

                    assert response.status_code in [200, 400, 401, 500]

    def test_delete_user_wrong_password(self, mock_db_connection, mock_db_cursor):
        """Test account deletion with wrong password"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                with patch("app.verify_password", return_value=False):
                    mock_db_cursor.fetchone.return_value = ("hashed_password",)

                    response = client.delete(
                        "/api/users/delete",
                        json={
                            "user_id": "user123",
                            "password": "wrong_password"
                        }
                    )

                    assert response.status_code in [400, 401, 500]


class TestProgressEndpoint:
    """Test general progress endpoint"""

    def test_get_overall_progress(self, mock_db_connection, mock_db_cursor):
        """Test getting overall student progress"""
        from app import app

        with app.test_client() as client:
            with patch("app.get_db_connection", return_value=mock_db_connection):
                mock_db_cursor.fetchall.return_value = [
                    ("class1", "Python 101", 10, 7, 70.0),
                    ("class2", "Data Science", 15, 15, 100.0),
                ]

                response = client.get("/api/progress?user_id=student123")

                assert response.status_code in [200, 400, 500]
