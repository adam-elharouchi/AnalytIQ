"""
tests/test_users_routes.py — Behavioral tests for user routes.

Covers:
  GET/PUT  /api/users/profile
  GET/PUT  /api/users/settings
  PUT      /api/users/password
  DELETE   /api/users/delete
  GET/POST /api/users/conversations
  GET/PUT/DELETE /api/users/conversations/<id>
  POST     /api/users/conversations/<id>/messages  (append-only)
  GET/PUT  /api/users/ai-digest
  GET/PUT  /api/users/ai-memory
  GET/PUT  /api/users/preferences
  GET/PUT  /api/users/practice-progress
"""
import pytest
import bcrypt
from datetime import datetime
from unittest.mock import MagicMock

AUTH = {"X-Test-User-ID": "student-user-id", "X-Test-User-Role": "student"}


def _bcrypt_hash(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


# ---------------------------------------------------------------------------
# GET /api/users/profile
# ---------------------------------------------------------------------------

class TestGetProfile:
    def test_returns_profile_fields(self, client, mock_db):
        """Authenticated user gets their profile with expected fields."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (
            "student-user-id", "Alice", "alice@example.com", "Alice Smith", "Short bio", None
        )

        resp = client.get("/api/users/profile", headers=AUTH)

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["id"] == "student-user-id"
        assert data["name"] == "Alice"
        assert data["email"] == "alice@example.com"

    def test_user_not_found_returns_404(self, client, mock_db):
        """Missing user returns 404."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None

        resp = client.get("/api/users/profile", headers=AUTH)

        assert resp.status_code == 404
        assert "error" in resp.get_json()

    def test_no_auth_returns_401(self, client, mock_db):
        """Unauthenticated request returns 401."""
        resp = client.get("/api/users/profile")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PUT /api/users/profile
# ---------------------------------------------------------------------------

class TestUpdateProfile:
    def test_update_profile_returns_200(self, client, mock_db):
        """Updating profile returns 200 with success flag."""
        resp = client.put(
            "/api/users/profile",
            headers=AUTH,
            json={"fullName": "Alice Smith", "bio": "Data scientist"},
        )

        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_no_auth_returns_401(self, client, mock_db):
        """Unauthenticated request returns 401."""
        resp = client.put("/api/users/profile", json={"fullName": "X"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/users/settings
# ---------------------------------------------------------------------------

class TestGetSettings:
    def test_returns_settings_with_email_notifications_key(self, client, mock_db):
        """Settings response has emailNotifications key."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (True,)

        resp = client.get("/api/users/settings", headers=AUTH)

        assert resp.status_code == 200
        data = resp.get_json()
        assert "emailNotifications" in data

    def test_missing_settings_returns_default_false(self, client, mock_db):
        """When no settings row, returns default False for emailNotifications."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None

        resp = client.get("/api/users/settings", headers=AUTH)

        assert resp.status_code == 200
        assert resp.get_json()["emailNotifications"] is False

    def test_no_auth_returns_401(self, client, mock_db):
        resp = client.get("/api/users/settings")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PUT /api/users/settings
# ---------------------------------------------------------------------------

class TestUpdateSettings:
    def test_update_settings_returns_200(self, client, mock_db):
        """Updating settings returns 200 with success flag."""
        resp = client.put(
            "/api/users/settings",
            headers=AUTH,
            json={"emailNotifications": True},
        )

        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_no_auth_returns_401(self, client, mock_db):
        resp = client.put("/api/users/settings", json={"emailNotifications": False})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PUT /api/users/password
# ---------------------------------------------------------------------------

class TestUpdatePassword:
    def test_correct_current_password_updates_successfully(self, client, mock_db):
        """Valid current password allows update — 200."""
        password_hash = _bcrypt_hash("oldPassword1")
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (password_hash,)

        resp = client.put(
            "/api/users/password",
            headers=AUTH,
            json={"currentPassword": "oldPassword1", "newPassword": "newPassword1"},
        )

        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_wrong_current_password_returns_401(self, client, mock_db):
        """Wrong current password returns 401."""
        password_hash = _bcrypt_hash("correctPassword1")
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (password_hash,)

        resp = client.put(
            "/api/users/password",
            headers=AUTH,
            json={"currentPassword": "wrongPassword1", "newPassword": "newPassword1"},
        )

        assert resp.status_code == 401
        assert "error" in resp.get_json()

    def test_new_password_too_short_returns_400(self, client, mock_db):
        """New password under 8 chars returns 400."""
        password_hash = _bcrypt_hash("oldPassword1")
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (password_hash,)

        resp = client.put(
            "/api/users/password",
            headers=AUTH,
            json={"currentPassword": "oldPassword1", "newPassword": "abc"},
        )

        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_missing_fields_returns_400(self, client, mock_db):
        """Missing currentPassword or newPassword returns 400."""
        resp = client.put(
            "/api/users/password",
            headers=AUTH,
            json={"currentPassword": "oldPassword1"},
        )

        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_user_not_found_returns_404(self, client, mock_db):
        """User not in DB returns 404."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None

        resp = client.put(
            "/api/users/password",
            headers=AUTH,
            json={"currentPassword": "oldPassword1", "newPassword": "newPassword1"},
        )

        assert resp.status_code == 404

    def test_no_auth_returns_401(self, client, mock_db):
        resp = client.put("/api/users/password", json={})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /api/users/delete
# ---------------------------------------------------------------------------

class TestDeleteUser:
    def test_delete_user_returns_200(self, client, mock_db):
        """Authenticated user can delete their own account."""
        resp = client.delete("/api/users/delete", headers=AUTH)

        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_no_auth_returns_401(self, client, mock_db):
        resp = client.delete("/api/users/delete")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET/POST /api/users/conversations
# ---------------------------------------------------------------------------

class TestConversations:
    def test_get_conversations_returns_200_with_conversations_key(self, client, mock_db):
        """GET returns list of conversations."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (2,)  # total_count
        cursor.fetchall.return_value = [
            ("conv-1", "My conversation", False, datetime.now(), None),
        ]

        resp = client.get("/api/users/conversations", headers=AUTH)

        assert resp.status_code == 200
        data = resp.get_json()
        assert "conversations" in data

    def test_create_conversation_returns_201_with_conversation_id(self, client, mock_db):
        """POST creates conversation and returns 201 with conversation_id."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = ("conv-new",)

        resp = client.post(
            "/api/users/conversations",
            headers=AUTH,
            json={"title": "My first conversation"},
        )

        assert resp.status_code == 201
        data = resp.get_json()
        assert "conversation_id" in data

    def test_get_conversations_no_auth_returns_401(self, client, mock_db):
        resp = client.get("/api/users/conversations")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/users/conversations/<id>
# ---------------------------------------------------------------------------

class TestGetConversation:
    def test_returns_conversation_with_messages(self, client, mock_db):
        """Returns conversation detail with messages list."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = ("conv-1", "My Chat", False, datetime.now(), None)
        cursor.fetchall.return_value = [
            ("user", "Hello there", 1),
            ("model", "Hi! How can I help?", 2),
        ]

        resp = client.get("/api/users/conversations/conv-1", headers=AUTH)

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["id"] == "conv-1"
        assert "messages" in data
        assert len(data["messages"]) == 2

    def test_conversation_not_found_returns_404(self, client, mock_db):
        """Missing conversation returns 404."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None

        resp = client.get("/api/users/conversations/nonexistent", headers=AUTH)

        assert resp.status_code == 404
        assert "error" in resp.get_json()


# ---------------------------------------------------------------------------
# PUT /api/users/conversations/<id>
# ---------------------------------------------------------------------------

class TestUpdateConversation:
    def test_update_conversation_title_returns_200(self, client, mock_db):
        """Updating conversation title returns 200."""
        resp = client.put(
            "/api/users/conversations/conv-1",
            headers=AUTH,
            json={"title": "New Title"},
        )

        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_archive_conversation_returns_200(self, client, mock_db):
        """Archiving a conversation returns 200."""
        resp = client.put(
            "/api/users/conversations/conv-1",
            headers=AUTH,
            json={"archived": True},
        )

        assert resp.status_code == 200
        assert resp.get_json()["success"] is True


# ---------------------------------------------------------------------------
# POST /api/users/conversations/<id>/messages — append message (Task 35)
# ---------------------------------------------------------------------------

class TestAppendConversationMessage:
    def test_append_user_message_returns_201(self, client, mock_db):
        """Appending a user message returns 201 with success flag."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = ("conv-1", "My Chat", False, datetime.now(), None)

        resp = client.post(
            "/api/users/conversations/conv-1/messages",
            headers=AUTH,
            json={"role": "user", "content": "What is Python?"},
        )

        assert resp.status_code == 201
        assert resp.get_json()["success"] is True

    def test_append_model_message_returns_201(self, client, mock_db):
        """Appending a model message returns 201."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = ("conv-1", "My Chat", False, datetime.now(), None)

        resp = client.post(
            "/api/users/conversations/conv-1/messages",
            headers=AUTH,
            json={"role": "model", "content": "Python is a programming language."},
        )

        assert resp.status_code == 201
        assert resp.get_json()["success"] is True

    def test_invalid_role_returns_400(self, client, mock_db):
        """Invalid role value returns 400."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = ("conv-1", "My Chat", False, datetime.now(), None)

        resp = client.post(
            "/api/users/conversations/conv-1/messages",
            headers=AUTH,
            json={"role": "admin", "content": "This should fail"},
        )

        assert resp.status_code == 400
        data = resp.get_json()
        assert "role" in data["error"]

    def test_missing_content_returns_400(self, client, mock_db):
        """Missing content returns 400."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = ("conv-1", "My Chat", False, datetime.now(), None)

        resp = client.post(
            "/api/users/conversations/conv-1/messages",
            headers=AUTH,
            json={"role": "user"},
        )

        assert resp.status_code == 400

    def test_content_too_large_returns_413(self, client, mock_db):
        """Content over 50000 chars returns 413."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = ("conv-1", "My Chat", False, datetime.now(), None)

        resp = client.post(
            "/api/users/conversations/conv-1/messages",
            headers=AUTH,
            json={"role": "user", "content": "x" * 50001},
        )

        assert resp.status_code == 413

    def test_conversation_not_found_returns_404(self, client, mock_db):
        """Missing conversation returns 404."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None

        resp = client.post(
            "/api/users/conversations/nonexistent/messages",
            headers=AUTH,
            json={"role": "user", "content": "Hello"},
        )

        assert resp.status_code == 404

    def test_no_auth_returns_401(self, client, mock_db):
        resp = client.post(
            "/api/users/conversations/conv-1/messages",
            json={"role": "user", "content": "Hello"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /api/users/conversations/<id>
# ---------------------------------------------------------------------------

class TestDeleteConversation:
    def test_delete_conversation_returns_200(self, client, mock_db):
        """Deleting conversation returns 200."""
        resp = client.delete("/api/users/conversations/conv-1", headers=AUTH)

        assert resp.status_code == 200
        assert resp.get_json()["success"] is True


# ---------------------------------------------------------------------------
# GET /api/users/ai-digest
# ---------------------------------------------------------------------------

class TestAiDigest:
    def test_get_ai_digest_returns_expected_keys(self, client, mock_db):
        """GET ai-digest returns goal, constraints, decisions, current_state, open_questions."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = ("Learn Python", "[]", "[]", "[]", "[]")

        resp = client.get("/api/users/ai-digest", headers=AUTH)

        assert resp.status_code == 200
        data = resp.get_json()
        assert "goal" in data
        assert "constraints" in data
        assert "decisions" in data
        assert "current_state" in data
        assert "open_questions" in data

    def test_get_ai_digest_no_row_returns_defaults(self, client, mock_db):
        """When no digest exists, returns empty defaults."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None

        resp = client.get("/api/users/ai-digest", headers=AUTH)

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["goal"] == ""
        assert data["constraints"] == []

    def test_update_ai_digest_returns_200(self, client, mock_db):
        """PUT ai-digest returns 200 with success."""
        resp = client.put(
            "/api/users/ai-digest",
            headers=AUTH,
            json={"digest": {"goal": "Learn Flask", "constraints": [], "decisions": [],
                             "current_state": [], "open_questions": []}},
        )

        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_no_auth_returns_401(self, client, mock_db):
        resp = client.get("/api/users/ai-digest")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET/PUT /api/users/ai-memory
# ---------------------------------------------------------------------------

class TestAiMemory:
    def test_get_ai_memory_returns_memory_key(self, client, mock_db):
        """GET ai-memory returns memory key."""
        cursor = mock_db.cursor()
        cursor.fetchall.return_value = [("memory item 1",), ("memory item 2",)]

        resp = client.get("/api/users/ai-memory", headers=AUTH)

        assert resp.status_code == 200
        assert "memory" in resp.get_json()

    def test_update_ai_memory_returns_200(self, client, mock_db):
        """PUT ai-memory returns 200 with success."""
        resp = client.put(
            "/api/users/ai-memory",
            headers=AUTH,
            json={"memory": ["Remember: use list comprehensions"]},
        )

        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_no_auth_returns_401(self, client, mock_db):
        resp = client.get("/api/users/ai-memory")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET/PUT /api/users/preferences
# ---------------------------------------------------------------------------

class TestPreferences:
    def test_get_preferences_returns_expected_keys(self, client, mock_db):
        """GET preferences returns currentLanguage, geminiModel, aiProvider."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = ("python", "gemini-3.5-flash", "gemini")

        resp = client.get("/api/users/preferences", headers=AUTH)

        assert resp.status_code == 200
        data = resp.get_json()
        assert "currentLanguage" in data
        assert "geminiModel" in data
        assert "aiProvider" in data

    def test_get_preferences_no_row_returns_defaults(self, client, mock_db):
        """When no preferences row exists, returns python/gemini-3.5-flash defaults."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None

        resp = client.get("/api/users/preferences", headers=AUTH)

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["currentLanguage"] == "python"
        assert data["geminiModel"] == "gemini-3.5-flash"

    def test_update_preferences_returns_200(self, client, mock_db):
        """PUT preferences returns 200 with success."""
        resp = client.put(
            "/api/users/preferences",
            headers=AUTH,
            json={"currentLanguage": "javascript", "geminiModel": "gemini-3.5-flash"},
        )

        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_no_auth_returns_401(self, client, mock_db):
        resp = client.get("/api/users/preferences")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET/PUT /api/users/practice-progress
# ---------------------------------------------------------------------------

class TestPracticeProgress:
    def test_get_all_practice_progress_returns_list(self, client, mock_db):
        """GET without exercise_id returns a list of progress entries."""
        cursor = mock_db.cursor()
        cursor.fetchall.return_value = [
            ("ex-1", "Exercise 1", 85, 0.9, 3, True, datetime.now()),
        ]

        resp = client.get("/api/users/practice-progress", headers=AUTH)

        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)

    def test_get_single_practice_progress_by_exercise(self, client, mock_db):
        """GET with exercise_id returns single progress entry."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (
            "ex-1", "Exercise 1", 85, 0.9, 120, 3, 80, True, datetime.now()
        )

        resp = client.get(
            "/api/users/practice-progress?exercise_id=ex-1",
            headers=AUTH,
        )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["exercise_id"] == "ex-1"
        assert "best_score" in data

    def test_update_practice_progress_returns_200(self, client, mock_db):
        """PUT practice-progress returns 200 with is_new_best and best_score."""
        cursor = mock_db.cursor()
        # user_exists -> True; get_current_progress -> existing record
        cursor.fetchone.side_effect = [
            ("student-user-id",),  # user_exists
            (70, 2),               # get_current_progress
        ]

        resp = client.put(
            "/api/users/practice-progress",
            headers=AUTH,
            json={
                "exercise_id": "ex-1",
                "score": 90,
                "accuracy": 0.9,
                "time_spent": 120,
                "progress_data": {"exercise_title": "Write a loop", "accuracy": 0.9},
            },
        )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "is_new_best" in data
        assert "best_score" in data

    def test_update_practice_progress_missing_exercise_id_returns_400(self, client, mock_db):
        """PUT without exercise_id returns 400."""
        resp = client.put(
            "/api/users/practice-progress",
            headers=AUTH,
            json={"score": 90},
        )

        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_no_auth_returns_401(self, client, mock_db):
        resp = client.get("/api/users/practice-progress")
        assert resp.status_code == 401
