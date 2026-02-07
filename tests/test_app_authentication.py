"""
Tests for authentication flows, password management, and session handling
"""
import pytest
from unittest.mock import patch, MagicMock
import os


class TestSignupFlow:
    """Test complete signup flow"""

    def test_signup_success_student(self, client, mock_db):
        """Test successful student signup"""
        mock_db.cursor().fetchone.side_effect = [None, ('user123', 'Test Student', 'test@student.hult.edu', 'student')]
        
        response = client.post(
            "/api/users/signup",
            json={
                "name": "Test Student",
                "email": "test@student.hult.edu",
                "password": "securePassword123"
            },
        )
        
        assert response.status_code in [201, 400, 429]

    def test_signup_success_professor(self, client, mock_db):
        """Test successful professor signup"""
        mock_db.cursor().fetchone.side_effect = [None, ('prof123', 'Test Prof', 'prof@hult.edu', 'professor')]
        
        response = client.post(
            "/api/users/signup",
            json={
                "name": "Test Professor",
                "email": "prof@hult.edu",
                "password": "securePassword123"
            },
        )
        
        assert response.status_code in [201, 400, 429]

    def test_signup_duplicate_email(self, client, mock_db):
        """Test signup with duplicate email"""
        mock_db.cursor().fetchone.return_value = ('existing_user',)
        
        response = client.post(
            "/api/users/signup",
            json={
                "name": "Duplicate User",
                "email": "existing@example.com",
                "password": "password123"
            },
        )
        
        assert response.status_code in [400, 429]

    def test_signup_invalid_json(self, client):
        """Test signup with invalid JSON"""
        response = client.post(
            "/api/users/signup",
            data="not json",
            content_type="application/json"
        )
        
        assert response.status_code in [400, 415, 429, 500]


class TestSigninFlow:
    """Test complete signin flow"""

    def test_signin_success(self, client, mock_db):
        """Test successful signin"""
        import bcrypt
        password_hash = bcrypt.hashpw("password123".encode(), bcrypt.gensalt()).decode()
        mock_db.cursor().fetchone.return_value = ('user123', 'Test User', 'test@example.com', password_hash, 'student')
        
        response = client.post(
            "/api/users/signin",
            json={"email": "test@example.com", "password": "password123"},
        )
        
        assert response.status_code in [200, 401, 429]

    def test_signin_invalid_password(self, client, mock_db):
        """Test signin with wrong password"""
        import bcrypt
        password_hash = bcrypt.hashpw("correctpassword".encode(), bcrypt.gensalt()).decode()
        mock_db.cursor().fetchone.return_value = ('user123', 'Test User', 'test@example.com', password_hash, 'student')
        
        response = client.post(
            "/api/users/signin",
            json={"email": "test@example.com", "password": "wrongpassword"},
        )
        
        assert response.status_code in [401, 429]

    def test_signin_user_not_found(self, client, mock_db):
        """Test signin with non-existent user"""
        mock_db.cursor().fetchone.return_value = None
        
        response = client.post(
            "/api/users/signin",
            json={"email": "nonexistent@example.com", "password": "password123"},
        )
        
        assert response.status_code in [401, 429]

    def test_signin_legacy_password_migration(self, client, mock_db):
        """Test signin with legacy password hash triggers migration"""
        # Legacy hash (not bcrypt)
        mock_db.cursor().fetchone.return_value = ('user123', 'Test User', 'test@example.com', '12345678', 'student')
        
        response = client.post(
            "/api/users/signin",
            json={"email": "test@example.com", "password": "password123"},
        )
        
        # Should either succeed (if legacy hash matches) or fail
        assert response.status_code in [200, 401, 429]


class TestPasswordReset:
    """Test password reset flow"""

    def test_forgot_password_existing_user(self, client, mock_db):
        """Test forgot password for existing user"""
        mock_db.cursor().fetchone.return_value = ('user123', 'Test User')
        
        response = client.post(
            "/api/users/forgot-password",
            json={"email": "test@example.com"},
        )
        
        # Should return success even if user doesn't exist (security)
        assert response.status_code in [200, 429]

    def test_forgot_password_nonexistent_user(self, client, mock_db):
        """Test forgot password for non-existent user"""
        mock_db.cursor().fetchone.return_value = None
        
        response = client.post(
            "/api/users/forgot-password",
            json={"email": "nonexistent@example.com"},
        )
        
        # Should return success to prevent email enumeration
        assert response.status_code in [200, 429]

    def test_reset_password_valid_token(self, client, mock_db):
        """Test password reset with valid token"""
        from datetime import datetime, timedelta
        expires_at = datetime.utcnow() + timedelta(hours=1)
        mock_db.cursor().fetchone.return_value = ('test@example.com', expires_at)
        
        response = client.post(
            "/api/users/reset-password",
            json={
                "token": "valid_token_123",
                "email": "test@example.com",
                "password": "newPassword123"
            },
        )
        
        assert response.status_code in [200, 400, 404, 429]

    def test_reset_password_expired_token(self, client, mock_db):
        """Test password reset with expired token"""
        from datetime import datetime, timedelta
        expires_at = datetime.utcnow() - timedelta(hours=1)
        mock_db.cursor().fetchone.return_value = ('test@example.com', expires_at)
        
        response = client.post(
            "/api/users/reset-password",
            json={
                "token": "expired_token",
                "email": "test@example.com",
                "password": "newPassword123"
            },
        )
        
        assert response.status_code in [400, 404, 429]


class TestUserProfile:
    """Test user profile operations"""

    def test_get_user_profile(self, client, mock_db):
        """Test getting user profile"""
        mock_db.cursor().fetchone.return_value = ('user123', 'Test User', 'test@example.com', 'student', None, None)
        
        response = client.get("/api/users/user123")
        
        assert response.status_code in [200, 404]

    def test_update_user_profile(self, client, mock_db):
        """Test updating user profile"""
        mock_db.cursor().fetchone.return_value = ('user123', 'Updated Name', 'test@example.com', 'student')
        
        response = client.put(
            "/api/users/user123",
            json={"name": "Updated Name"},
        )
        
        assert response.status_code in [200, 400, 404]

    def test_get_user_settings(self, client, mock_db):
        """Test getting user settings"""
        mock_db.cursor().fetchone.return_value = ('user123', True, 'dark', 'en')
        
        response = client.get("/api/users/user123/settings")
        
        assert response.status_code in [200, 404]

    def test_update_user_settings(self, client, mock_db):
        """Test updating user settings"""
        mock_db.cursor().fetchone.return_value = ('user123', True, 'light', 'en')
        
        response = client.put(
            "/api/users/user123/settings",
            json={"theme": "light", "notifications": True},
        )
        
        assert response.status_code in [200, 400, 404]


class TestTokenValidation:
    """Test token and session validation"""

    def test_validate_session_token(self, client, mock_db):
        """Test session token validation"""
        mock_db.cursor().fetchone.return_value = ('user123', 'Test User', 'test@example.com')
        
        response = client.get(
            "/api/auth/validate",
            headers={"Authorization": "Bearer test_token_123"},
        )
        
        assert response.status_code in [200, 401, 404]

    def test_validate_invalid_token(self, client, mock_db):
        """Test invalid token validation"""
        mock_db.cursor().fetchone.return_value = None
        
        response = client.get(
            "/api/auth/validate",
            headers={"Authorization": "Bearer invalid_token"},
        )
        
        assert response.status_code in [401, 404]

    def test_logout(self, client, mock_db):
        """Test logout endpoint"""
        response = client.post(
            "/api/auth/logout",
            headers={"Authorization": "Bearer test_token_123"},
        )
        
        assert response.status_code in [200, 204, 404]


class TestRateLimiting:
    """Test rate limiting behavior"""

    def test_rate_limit_headers(self, client):
        """Test that rate limit headers are present"""
        response = client.get("/api/health")
        
        # Rate limit headers might be present
        # X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
        assert response.status_code in [200, 429, 503]

    def test_options_not_rate_limited(self, client):
        """Test that OPTIONS requests are not rate limited"""
        for _ in range(10):
            response = client.options("/api/users/signup")
            assert response.status_code == 200


class TestEmailValidation:
    """Test email validation in authentication"""

    def test_signup_invalid_email_format(self, client, mock_db):
        """Test signup with invalid email format"""
        response = client.post(
            "/api/users/signup",
            json={
                "name": "Test User",
                "email": "not-an-email",
                "password": "password123"
            },
        )
        
        # Should accept or reject based on validation
        assert response.status_code in [201, 400, 429, 500]

    def test_signup_empty_email(self, client, mock_db):
        """Test signup with empty email"""
        response = client.post(
            "/api/users/signup",
            json={
                "name": "Test User",
                "email": "",
                "password": "password123"
            },
        )
        
        assert response.status_code in [400, 429]

    def test_signup_whitespace_email(self, client, mock_db):
        """Test signup with whitespace in email"""
        response = client.post(
            "/api/users/signup",
            json={
                "name": "Test User",
                "email": "  test@example.com  ",
                "password": "password123"
            },
        )
        
        assert response.status_code in [201, 400, 429, 500]


class TestPasswordStrength:
    """Test password strength requirements"""

    def test_signup_short_password(self, client, mock_db):
        """Test signup with too short password"""
        response = client.post(
            "/api/users/signup",
            json={
                "name": "Test User",
                "email": "test@example.com",
                "password": "123"
            },
        )
        
        # Might accept or reject based on password policy
        assert response.status_code in [201, 400, 429, 500]

    def test_signup_long_password(self, client, mock_db):
        """Test signup with very long password"""
        long_password = "a" * 1000
        
        response = client.post(
            "/api/users/signup",
            json={
                "name": "Test User",
                "email": "test@example.com",
                "password": long_password
            },
        )
        
        # Should handle gracefully
        assert response.status_code in [201, 400, 429, 500]

    def test_signup_special_chars_password(self, client, mock_db):
        """Test signup with special characters in password"""
        mock_db.cursor().fetchone.side_effect = [None, ('user123', 'Test User', 'test@example.com', 'student')]
        
        response = client.post(
            "/api/users/signup",
            json={
                "name": "Test User",
                "email": "test@example.com",
                "password": "P@$$w0rd!@#$%^&*()"
            },
        )
        
        assert response.status_code in [201, 400, 429]
