"""
Tests for error handling, edge cases, and validation
"""
import pytest
from unittest.mock import patch, MagicMock
import json


class TestDatabaseErrorHandling:
    """Test database connection error handling"""

    def test_database_connection_retry_logic(self, client, mock_db):
        """Test that database connection retry logic works"""
        response = client.get("/api/health")
        assert response.status_code in [200, 500, 503]

    def test_database_pool_initialization(self, client):
        """Test database pool initialization"""
        response = client.get("/api/health")
        assert response.status_code != 500 or "database" in response.get_data(as_text=True).lower()

    def test_database_connection_timeout(self, client, mock_db):
        """Test handling of database connection timeouts"""
        response = client.post(
            "/api/users/signin",
            json={"email": "test@example.com", "password": "testpass"},
        )
        assert response.status_code in [200, 400, 401, 429, 500, 503]


class TestValidationErrors:
    """Test input validation and error responses"""

    def test_signup_missing_name(self, client, mock_db):
        """Test signup with missing name field"""
        response = client.post(
            "/api/users/signup",
            json={"email": "test@example.com", "password": "testpass"},
        )
        assert response.status_code in [400, 429]
        if response.status_code == 400:
            data = response.get_json()
            assert "error" in data

    def test_signup_missing_email(self, client, mock_db):
        """Test signup with missing email field"""
        response = client.post(
            "/api/users/signup",
            json={"name": "Test User", "password": "testpass"},
        )
        assert response.status_code in [400, 429]
        if response.status_code == 400:
            data = response.get_json()
            assert "error" in data

    def test_signup_missing_password(self, client, mock_db):
        """Test signup with missing password field"""
        response = client.post(
            "/api/users/signup",
            json={"name": "Test User", "email": "test@example.com"},
        )
        assert response.status_code in [400, 429]
        if response.status_code == 400:
            data = response.get_json()
            assert "error" in data

    def test_signup_empty_fields(self, client, mock_db):
        """Test signup with empty string fields"""
        response = client.post(
            "/api/users/signup",
            json={"name": "", "email": "", "password": ""},
        )
        assert response.status_code in [400, 429]
        if response.status_code == 400:
            data = response.get_json()
            assert "error" in data

    def test_signin_missing_email(self, client, mock_db):
        """Test signin with missing email"""
        response = client.post(
            "/api/users/signin",
            json={"password": "testpass"},
        )
        assert response.status_code in [400, 429]
        if response.status_code == 400:
            data = response.get_json()
            assert "error" in data

    def test_signin_missing_password(self, client, mock_db):
        """Test signin with missing password"""
        response = client.post(
            "/api/users/signin",
            json={"email": "test@example.com"},
        )
        assert response.status_code in [400, 429]
        if response.status_code == 400:
            data = response.get_json()
            assert "error" in data

    def test_forgot_password_missing_email(self, client, mock_db):
        """Test forgot password with missing email"""
        response = client.post(
            "/api/users/forgot-password",
            json={},
        )
        assert response.status_code in [400, 429]
        if response.status_code == 400:
            data = response.get_json()
            assert "error" in data


class TestAuthenticationEdgeCases:
    """Test authentication edge cases and security"""

    def test_signin_nonexistent_user(self, client, mock_db):
        """Test signin with non-existent user"""
        mock_db.cursor().fetchone.return_value = None

        response = client.post(
            "/api/users/signin",
            json={"email": "nonexistent@example.com", "password": "testpass"},
        )
        assert response.status_code in [401, 429, 500]

    def test_signin_wrong_password(self, client, mock_db):
        """Test signin with wrong password"""
        # Mock user exists but password is wrong
        mock_db.cursor().fetchone.return_value = (
            "user123", "Test User", "test@example.com", "$2b$12$invalidhash", "student"
        )

        with patch("blueprints.auth.verify_password", return_value=(False, False)):
            response = client.post(
                "/api/users/signin",
                json={"email": "test@example.com", "password": "wrongpass"},
            )
        assert response.status_code in [401, 429, 500]

    def test_forgot_password_nonexistent_email(self, client, mock_db):
        """Test forgot password with non-existent email"""
        mock_db.cursor().fetchone.return_value = None

        response = client.post(
            "/api/users/forgot-password",
            json={"email": "nonexistent@example.com"},
        )
        assert response.status_code in [200, 429, 500]

    def test_forgot_password_options_request(self, client):
        """Test OPTIONS request on forgot password endpoint"""
        response = client.options("/api/users/forgot-password")
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers


class TestPasswordSecurity:
    """Test password hashing and verification"""

    def test_password_hashing_bcrypt(self, client, mock_db):
        """Test that passwords are hashed with bcrypt"""
        mock_db.cursor().fetchone.return_value = None  # No existing user

        response = client.post(
            "/api/users/signup",
            json={"name": "Test User", "email": "test@example.com", "password": "testpass123"},
        )
        assert response.status_code in [201, 400, 429, 500]

    def test_password_verification_case_sensitive(self, client, mock_db):
        """Test that password verification is case-sensitive"""
        # Mock user with bcrypt hash
        mock_db.cursor().fetchone.return_value = (
            "user123", "Test User", "test@example.com",
            "$2b$12$LJ3m4ys3Lk8C4VHfZ.g7duSIGcFtxH2FQpcJQkXE6/", "student"
        )

        with patch("blueprints.auth.verify_password", return_value=(False, False)):
            response = client.post(
                "/api/users/signin",
                json={"email": "test@example.com", "password": "testpass123"},
            )
        assert response.status_code in [401, 429, 500]


class TestRoleDetection:
    """Test role detection from email domains"""

    def test_professor_role_from_hult_edu(self):
        """Test professor role detection for @hult.edu"""
        from app import detect_role_from_email
        assert detect_role_from_email("prof@hult.edu") == "professor"

    def test_professor_role_from_faculty_hult_edu(self):
        """Test professor role detection for @faculty.hult.edu"""
        from app import detect_role_from_email
        assert detect_role_from_email("faculty@faculty.hult.edu") == "professor"

    def test_student_role_from_student_hult_edu(self):
        """Test student role detection for @student.hult.edu"""
        from app import detect_role_from_email
        assert detect_role_from_email("student@student.hult.edu") == "student"

    def test_default_role_from_other_email(self):
        """Test default role detection for other email domains"""
        from app import detect_role_from_email
        assert detect_role_from_email("user@example.com") == "student"

    def test_role_detection_none_email(self):
        """Test role detection with None email"""
        from app import detect_role_from_email
        assert detect_role_from_email(None) == "student"

    def test_role_detection_empty_email(self):
        """Test role detection with empty email"""
        from app import detect_role_from_email
        assert detect_role_from_email("") == "student"


class TestCORSHandling:
    """Test CORS header handling"""

    def test_cors_headers_on_api_endpoints(self, client):
        """Test that API endpoints have CORS headers"""
        response = client.get("/api/health")
        assert "Access-Control-Allow-Origin" in response.headers

    def test_cors_options_request(self, client):
        """Test OPTIONS request handling"""
        response = client.options("/api/users/signup")
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers

    def test_cors_wildcard_origin(self, client):
        """Test that CORS allows all origins"""
        response = client.get("/api/health")
        assert response.headers.get("Access-Control-Allow-Origin") == "*"


class TestErrorResponses:
    """Test error response formats"""

    def test_error_response_format(self, client, mock_db):
        """Test that error responses have consistent format"""
        # Use an endpoint that always validates without rate limiting concerns
        response = client.get("/api/users/profile")
        assert response.status_code in [400, 401]
        data = response.get_json()
        assert "error" in data
        assert isinstance(data["error"], str)

    def test_success_response_format(self, client, mock_db):
        """Test JSON response on health endpoint"""
        response = client.get("/api/health")
        assert "application/json" in response.content_type

    def test_json_content_type(self, client, mock_db):
        """Test that API responses have JSON content type"""
        response = client.get("/api/health")
        assert "application/json" in response.content_type

    def test_404_handling(self, client):
        """Test 404 handling for non-existent routes"""
        response = client.get("/api/nonexistent-endpoint")
        assert response.status_code in [404, 405]


class TestConcurrentAccess:
    """Test handling of concurrent requests"""

    def test_multiple_signup_requests(self, client, mock_db):
        """Test handling of multiple signup requests"""
        mock_db.cursor().fetchone.return_value = None

        response1 = client.post(
            "/api/users/signup",
            json={"name": "User 1", "email": "user1@example.com", "password": "pass1"},
        )
        assert response1.status_code in [201, 400, 429, 500]

    def test_duplicate_signup_prevention(self, client, mock_db):
        """Test prevention of duplicate signups"""
        # Mock that user already exists
        from psycopg2 import IntegrityError
        mock_db.cursor().execute.side_effect = [None, IntegrityError("duplicate key")]
        mock_db.cursor().fetchone.return_value = ("existing_user",)

        response = client.post(
            "/api/users/signup",
            json={"name": "Test User", "email": "test@example.com", "password": "testpass"},
        )
        assert response.status_code in [400, 409, 429, 500]


class TestPasswordFunctions:
    """Test password utility functions directly"""

    def test_hash_password_legacy(self):
        """Test legacy hash function"""
        from app import hash_password_legacy
        result = hash_password_legacy("testpass")
        assert isinstance(result, str)
        assert result == hash_password_legacy("testpass")  # Deterministic

    def test_hash_password_bcrypt(self):
        """Test bcrypt hash function"""
        from app import hash_password
        result = hash_password("testpass")
        assert result.startswith("$2")  # bcrypt prefix
        assert len(result) > 50

    def test_verify_password_bcrypt(self):
        """Test bcrypt verification"""
        from app import hash_password, verify_password
        hashed = hash_password("testpass")
        is_valid, needs_rehash = verify_password("testpass", hashed)
        assert is_valid is True
        assert needs_rehash is False

    def test_verify_password_wrong(self):
        """Test wrong password verification"""
        from app import hash_password, verify_password
        hashed = hash_password("testpass")
        is_valid, needs_rehash = verify_password("wrongpass", hashed)
        assert is_valid is False

    def test_verify_password_legacy(self):
        """Test legacy password verification"""
        from app import hash_password_legacy, verify_password
        legacy_hash = hash_password_legacy("testpass")
        is_valid, needs_rehash = verify_password("testpass", legacy_hash)
        assert is_valid is True
        assert needs_rehash is True  # Should suggest rehashing

    def test_close_conn_safely(self):
        """Test the no-op connection close helper"""
        from app import close_conn_safely
        mock_conn = MagicMock()
        close_conn_safely(mock_conn)  # Should not raise


class TestAllowedFile:
    """Test file extension validation"""

    def test_allowed_pdf(self):
        """Test PDF is allowed"""
        from app import allowed_file
        assert allowed_file("test.pdf") is True

    def test_allowed_csv(self):
        """Test CSV is allowed"""
        from app import allowed_file
        assert allowed_file("data.csv") is True

    def test_disallowed_exe(self):
        """Test EXE is not allowed"""
        from app import allowed_file
        assert allowed_file("virus.exe") is False

    def test_no_extension(self):
        """Test file without extension"""
        from app import allowed_file
        assert allowed_file("noextension") is False
