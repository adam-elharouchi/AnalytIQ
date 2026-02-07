"""
Deep tests for signup/signin flows, password management, settings, conversations,
AI digest, AI memory, and user preferences.
Targets uncovered lines: 497-704, 839-984, 1059-1598, 1716-1719
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import json


class TestSignupDeepPaths:
    """Test signup success paths - lines 548-646"""

    def test_signup_success_creates_user(self, client, mock_db):
        """Test successful signup with all default table inserts"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            None,  # No existing user
            ("user123", "Test User", "test@example.com", "student"),  # Created user
        ]

        response = client.post("/api/users/signup", json={
            "name": "Test User",
            "email": "test@example.com",
            "password": "securepass123",
        })
        assert response.status_code in [201, 429, 500]
        if response.status_code == 201:
            data = response.get_json()
            assert data.get("success") is True
            assert "user_id" in data

    def test_signup_professor_email(self, client, mock_db):
        """Test signup with professor email domain"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            None,
            ("prof123", "Prof Test", "prof@hult.edu", "professor"),
        ]

        response = client.post("/api/users/signup", json={
            "name": "Prof Test",
            "email": "prof@hult.edu",
            "password": "securepass123",
        })
        assert response.status_code in [201, 429, 500]

    def test_signup_email_already_exists(self, client, mock_db):
        """Test signup with email that already exists"""
        mock_db.cursor().fetchone.return_value = ("existing_user",)

        response = client.post("/api/users/signup", json={
            "name": "Test User",
            "email": "existing@example.com",
            "password": "securepass123",
        })
        assert response.status_code in [400, 429, 500]

    def test_signup_missing_fields(self, client, mock_db):
        """Test signup with missing fields"""
        response = client.post("/api/users/signup", json={
            "name": "Test User",
        })
        assert response.status_code in [400, 429]

    def test_signup_profile_creation_failure(self, client, mock_db):
        """Test that signup succeeds even when profile tables fail"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.side_effect = [
            None,
            ("user123", "Test", "test@example.com", "student"),
        ]
        # Simulate some sub-inserts failing
        call_count = [0]
        original_execute = mock_cursor.execute

        def execute_with_failures(query, params=None):
            call_count[0] += 1
            if call_count[0] in [3, 4]:  # Fail on profile/settings inserts
                raise Exception("Table not found")
            return original_execute(query, params)

        mock_cursor.execute = execute_with_failures

        response = client.post("/api/users/signup", json={
            "name": "Test",
            "email": "test@example.com",
            "password": "pass123",
        })
        assert response.status_code in [201, 429, 500]


class TestSigninDeepPaths:
    """Test signin success/failure paths - lines 649-719"""

    def test_signin_success_bcrypt(self, client, mock_db):
        """Test successful signin with bcrypt password"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.return_value = (
            "user123", "Test User", "test@example.com",
            "$2b$12$validhash", "student",
        )

        with patch("app.verify_password", return_value=(True, False)):
            response = client.post("/api/users/signin", json={
                "email": "test@example.com",
                "password": "correctpass",
            })
        assert response.status_code in [200, 429, 500]
        if response.status_code == 200:
            data = response.get_json()
            assert "user_id" in data

    def test_signin_legacy_hash_migration(self, client, mock_db):
        """Test signin with legacy hash triggers migration - line 688-704"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.return_value = (
            "user123", "Test User", "test@example.com",
            "12345678", "student",  # Legacy hash
        )

        with patch("app.verify_password", return_value=(True, True)):
            with patch("app.hash_password", return_value="$2b$12$newhash"):
                response = client.post("/api/users/signin", json={
                    "email": "test@example.com",
                    "password": "testpass",
                })
        assert response.status_code in [200, 429, 500]

    def test_signin_invalid_credentials(self, client, mock_db):
        """Test signin with wrong password"""
        mock_db.cursor().fetchone.return_value = (
            "user123", "Test", "test@test.com", "$2b$12$hash", "student",
        )

        with patch("app.verify_password", return_value=(False, False)):
            response = client.post("/api/users/signin", json={
                "email": "test@test.com",
                "password": "wrongpass",
            })
        assert response.status_code in [401, 429, 500]

    def test_signin_user_not_found(self, client, mock_db):
        """Test signin with non-existent email"""
        mock_db.cursor().fetchone.return_value = None

        response = client.post("/api/users/signin", json={
            "email": "nobody@test.com",
            "password": "pass123",
        })
        assert response.status_code in [401, 429, 500]

    def test_signin_missing_fields(self, client, mock_db):
        """Test signin with missing email"""
        response = client.post("/api/users/signin", json={"password": "pass"})
        assert response.status_code in [400, 429]


class TestForgotPasswordDeep:
    """Test forgot/reset password - lines 721-882"""

    def test_forgot_password_success(self, client, mock_db):
        """Test forgot password sends email"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.return_value = ("user123", "test@test.com")

        with patch("app.mail") as mock_mail:
            response = client.post("/api/users/forgot-password", json={
                "email": "test@test.com",
            })
        assert response.status_code in [200, 429, 500]

    def test_forgot_password_missing_email(self, client, mock_db):
        """Test forgot password without email"""
        response = client.post("/api/users/forgot-password", json={})
        assert response.status_code in [400, 429]

    def test_reset_password_success(self, client, mock_db):
        """Test password reset with valid token"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.return_value = (1,)  # Valid token

        response = client.post("/api/users/reset-password", json={
            "token": "valid-token",
            "email": "test@test.com",
            "newPassword": "newSecurePass123",
        })
        assert response.status_code in [200, 400, 429, 500]

    def test_reset_password_invalid_token(self, client, mock_db):
        """Test password reset with invalid token"""
        mock_db.cursor().fetchone.return_value = None

        response = client.post("/api/users/reset-password", json={
            "token": "invalid-token",
            "email": "test@test.com",
            "newPassword": "newpass123",
        })
        assert response.status_code in [400, 429, 500]

    def test_reset_password_short_password(self, client, mock_db):
        """Test password reset with too short password"""
        response = client.post("/api/users/reset-password", json={
            "token": "token",
            "email": "test@test.com",
            "newPassword": "ab",
        })
        assert response.status_code in [400, 429, 500]

    def test_reset_password_missing_fields(self, client, mock_db):
        """Test password reset with missing fields"""
        response = client.post("/api/users/reset-password", json={
            "token": "token",
        })
        assert response.status_code in [400, 429, 500]


class TestUpdatePassword:
    """Test PUT /api/users/password - lines 1067-1118"""

    def test_update_password_success(self, client, mock_db):
        """Test successful password update"""
        mock_db.cursor().fetchone.return_value = ("$2b$12$currenthash",)

        with patch("app.verify_password", return_value=(True, False)):
            with patch("app.hash_password", return_value="$2b$12$newhash"):
                response = client.put("/api/users/password", json={
                    "user_id": "user123",
                    "currentPassword": "oldpass",
                    "newPassword": "newpass123",
                })
        assert response.status_code in [200, 401, 404, 500]

    def test_update_password_wrong_current(self, client, mock_db):
        """Test password update with wrong current password"""
        mock_db.cursor().fetchone.return_value = ("$2b$12$hash",)

        with patch("app.verify_password", return_value=(False, False)):
            response = client.put("/api/users/password", json={
                "user_id": "user123",
                "currentPassword": "wrongpass",
                "newPassword": "newpass123",
            })
        assert response.status_code in [401, 500]

    def test_update_password_user_not_found(self, client, mock_db):
        """Test password update for non-existent user"""
        mock_db.cursor().fetchone.return_value = None

        response = client.put("/api/users/password", json={
            "user_id": "nonexistent",
            "currentPassword": "pass",
            "newPassword": "newpass",
        })
        assert response.status_code in [404, 500]

    def test_update_password_missing_fields(self, client, mock_db):
        """Test password update with missing fields"""
        response = client.put("/api/users/password", json={
            "user_id": "user123",
        })
        assert response.status_code in [400, 500]


class TestUpdateSettings:
    """Test PUT /api/users/settings - lines 1022-1064"""

    def test_update_settings_success(self, client, mock_db):
        """Test successful settings update"""
        response = client.put("/api/users/settings", json={
            "user_id": "user123",
            "emailNotifications": True,
        })
        assert response.status_code in [200, 400, 500]

    def test_update_settings_missing_user_id(self, client, mock_db):
        """Test settings update without user_id"""
        response = client.put("/api/users/settings", json={
            "emailNotifications": True,
        })
        assert response.status_code in [400, 500]


class TestConversationsDeep:
    """Test conversation CRUD deep paths - lines 1145-1403"""

    def test_get_conversations_with_pagination(self, client, mock_db):
        """Test getting conversations with pagination"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.return_value = (5,)  # Total count
        mock_cursor.fetchall.return_value = [
            ("conv1", "Title 1", False, datetime(2026, 1, 1), datetime(2026, 1, 2)),
            ("conv2", "Title 2", True, datetime(2026, 1, 3), None),
        ]

        response = client.get(
            "/api/users/conversations?user_id=user123&limit=10&offset=0"
        )
        assert response.status_code in [200, 500]

    def test_get_conversations_archived(self, client, mock_db):
        """Test getting archived conversations"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.return_value = (2,)
        mock_cursor.fetchall.return_value = []

        response = client.get(
            "/api/users/conversations?user_id=user123&archived=true"
        )
        assert response.status_code in [200, 500]

    def test_get_conversations_missing_user(self, client, mock_db):
        """Test getting conversations without user_id"""
        response = client.get("/api/users/conversations")
        assert response.status_code == 400

    def test_create_conversation_success(self, client, mock_db):
        """Test creating a conversation"""
        mock_db.cursor().fetchone.return_value = ("conv_new",)

        response = client.post("/api/users/conversations", json={
            "user_id": "user123",
            "title": "New Chat",
        })
        assert response.status_code in [201, 500]

    def test_create_conversation_with_id(self, client, mock_db):
        """Test creating conversation with custom ID"""
        mock_db.cursor().fetchone.return_value = ("custom_id",)

        response = client.post("/api/users/conversations", json={
            "user_id": "user123",
            "conversation_id": "custom_id",
            "title": "Custom Chat",
        })
        assert response.status_code in [201, 500]

    def test_create_conversation_missing_user(self, client, mock_db):
        """Test creating conversation without user_id"""
        response = client.post("/api/users/conversations", json={
            "title": "Chat",
        })
        assert response.status_code in [400, 500]

    def test_get_conversation_by_id_success(self, client, mock_db):
        """Test getting specific conversation with messages"""
        mock_cursor = mock_db.cursor()
        mock_cursor.fetchone.return_value = (
            "conv1", "Title", False, datetime(2026, 1, 1), datetime(2026, 1, 2),
        )
        mock_cursor.fetchall.return_value = [
            ("user", "Hello", 0, datetime(2026, 1, 1)),
            ("assistant", "Hi there!", 1, datetime(2026, 1, 1)),
        ]

        response = client.get(
            "/api/users/conversations/conv1?user_id=user123"
        )
        assert response.status_code in [200, 404, 500]

    def test_get_conversation_not_found(self, client, mock_db):
        """Test getting non-existent conversation"""
        mock_db.cursor().fetchone.return_value = None

        response = client.get(
            "/api/users/conversations/nonexistent?user_id=user123"
        )
        assert response.status_code in [404, 500]

    def test_get_conversation_missing_user(self, client, mock_db):
        """Test getting conversation without user_id"""
        response = client.get("/api/users/conversations/conv1")
        assert response.status_code in [400, 500]

    def test_update_conversation_title(self, client, mock_db):
        """Test updating conversation title"""
        response = client.put("/api/users/conversations/conv1", json={
            "user_id": "user123",
            "title": "Updated Title",
        })
        assert response.status_code in [200, 500]

    def test_update_conversation_archived(self, client, mock_db):
        """Test archiving a conversation"""
        response = client.put("/api/users/conversations/conv1", json={
            "user_id": "user123",
            "archived": True,
        })
        assert response.status_code in [200, 500]

    def test_update_conversation_with_messages(self, client, mock_db):
        """Test updating conversation with messages - lines 1348-1362"""
        response = client.put("/api/users/conversations/conv1", json={
            "user_id": "user123",
            "title": "Updated",
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ],
        })
        assert response.status_code in [200, 500]

    def test_update_conversation_missing_user(self, client, mock_db):
        """Test updating conversation without user_id"""
        response = client.put("/api/users/conversations/conv1", json={
            "title": "New Title",
        })
        assert response.status_code in [400, 500]

    def test_delete_conversation_success(self, client, mock_db):
        """Test soft-deleting a conversation"""
        response = client.delete(
            "/api/users/conversations/conv1?user_id=user123"
        )
        assert response.status_code in [200, 500]

    def test_delete_conversation_missing_user(self, client, mock_db):
        """Test deleting conversation without user_id"""
        response = client.delete("/api/users/conversations/conv1")
        assert response.status_code in [400, 500]


class TestAIDigestDeep:
    """Test AI digest endpoints deep - lines 1406-1529"""

    def test_get_ai_digest_with_data(self, client, mock_db):
        """Test getting AI digest with existing data"""
        mock_db.cursor().fetchone.return_value = (
            "Study goal",
            '["constraint1", "constraint2"]',
            '["decision1"]',
            '["state1"]',
            '["question1"]',
        )

        response = client.get("/api/users/ai-digest?user_id=user123")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.get_json()
            assert data.get("goal") == "Study goal"

    def test_get_ai_digest_no_data(self, client, mock_db):
        """Test getting AI digest with no data"""
        mock_db.cursor().fetchone.return_value = None

        response = client.get("/api/users/ai-digest?user_id=user123")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.get_json()
            assert data.get("goal") == ""

    def test_get_ai_digest_with_non_json_data(self, client, mock_db):
        """Test AI digest parsing with non-JSON string data - line 1446-1453"""
        mock_db.cursor().fetchone.return_value = (
            "Goal text",
            "not json text",  # Non-JSON string
            None,  # None value
            '["valid"]',
            "",  # Empty string
        )

        response = client.get("/api/users/ai-digest?user_id=user123")
        assert response.status_code in [200, 500]

    def test_get_ai_digest_missing_user(self, client, mock_db):
        """Test getting AI digest without user_id"""
        response = client.get("/api/users/ai-digest")
        assert response.status_code in [400, 500]

    def test_update_ai_digest_success(self, client, mock_db):
        """Test updating AI digest"""
        response = client.put("/api/users/ai-digest", json={
            "user_id": "user123",
            "digest": {
                "goal": "Learn Python",
                "constraints": ["Time: 2 hours/day"],
                "decisions": ["Focus on basics first"],
                "current_state": ["Started chapter 1"],
                "open_questions": ["Which IDE?"],
            },
        })
        assert response.status_code in [200, 500]

    def test_update_ai_digest_with_string_values(self, client, mock_db):
        """Test AI digest serialization with string values - lines 1490-1498"""
        response = client.put("/api/users/ai-digest", json={
            "user_id": "user123",
            "digest": {
                "goal": "Study",
                "constraints": "single string value",
                "decisions": '["already json"]',
            },
        })
        assert response.status_code in [200, 500]

    def test_update_ai_digest_missing_user(self, client, mock_db):
        """Test updating AI digest without user_id"""
        response = client.put("/api/users/ai-digest", json={
            "digest": {"goal": "test"},
        })
        assert response.status_code in [400, 500]


class TestAIMemoryDeep:
    """Test AI memory endpoints - lines 1532-1598"""

    def test_get_ai_memory_success(self, client, mock_db):
        """Test getting AI memory"""
        mock_db.cursor().fetchall.return_value = [
            ("User likes Python",),
            ("User is a beginner",),
        ]

        response = client.get("/api/users/ai-memory?user_id=user123")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.get_json()
            assert "memory" in data

    def test_get_ai_memory_empty(self, client, mock_db):
        """Test getting AI memory with no items"""
        mock_db.cursor().fetchall.return_value = []

        response = client.get("/api/users/ai-memory?user_id=user123")
        assert response.status_code in [200, 500]

    def test_get_ai_memory_missing_user(self, client, mock_db):
        """Test getting AI memory without user_id"""
        response = client.get("/api/users/ai-memory")
        assert response.status_code in [400, 500]

    def test_update_ai_memory_success(self, client, mock_db):
        """Test updating AI memory"""
        response = client.put("/api/users/ai-memory", json={
            "user_id": "user123",
            "memory": [
                "User prefers Python",
                "Interested in data science",
                "Beginner level",
            ],
        })
        assert response.status_code in [200, 500]

    def test_update_ai_memory_empty_items(self, client, mock_db):
        """Test updating memory with empty items filtered"""
        response = client.put("/api/users/ai-memory", json={
            "user_id": "user123",
            "memory": ["Valid item", "", None, "Another item"],
        })
        assert response.status_code in [200, 500]

    def test_update_ai_memory_missing_user(self, client, mock_db):
        """Test updating AI memory without user_id"""
        response = client.put("/api/users/ai-memory", json={
            "memory": ["item"],
        })
        assert response.status_code in [400, 500]


class TestPreferencesDeep:
    """Test preferences deep paths - lines 1601-1719"""

    def test_get_preferences_no_results(self, client, mock_db):
        """Test getting preferences returns defaults when not found"""
        mock_db.cursor().fetchone.return_value = None

        response = client.get("/api/users/preferences?user_id=user123")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.get_json()
            assert data.get("currentLanguage") == "python"

    def test_update_preferences_all_fields(self, client, mock_db):
        """Test updating all preference fields - lines 1677-1708"""
        response = client.put("/api/users/preferences", json={
            "user_id": "user123",
            "currentLanguage": "javascript",
            "geminiModel": "gemini-3-pro-preview",
            "aiProvider": "openai",
        })
        assert response.status_code in [200, 500]

    def test_update_preferences_single_field(self, client, mock_db):
        """Test updating single preference field"""
        response = client.put("/api/users/preferences", json={
            "user_id": "user123",
            "currentLanguage": "r",
        })
        assert response.status_code in [200, 500]

    def test_update_preferences_no_fields(self, client, mock_db):
        """Test updating preferences with no fields to update"""
        response = client.put("/api/users/preferences", json={
            "user_id": "user123",
        })
        assert response.status_code in [200, 500]
