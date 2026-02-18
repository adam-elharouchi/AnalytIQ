"""
tests/test_security.py — Task 49

Asserts that every authenticated endpoint returns 401 when called without a
valid Bearer token.  Tests use the standard conftest `client` fixture (which
sets TESTING=True) but deliberately omit the X-Test-User-ID header so that
auth is enforced rather than bypassed.
"""

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _no_auth_get(client, url):
    return client.get(url)


def _no_auth_post(client, url, json=None):
    return client.post(url, json=json or {})


def _no_auth_put(client, url, json=None):
    return client.put(url, json=json or {})


def _no_auth_delete(client, url):
    return client.delete(url)


# ---------------------------------------------------------------------------
# Users blueprint
# ---------------------------------------------------------------------------

class TestUsersAuthRequired:
    def test_get_profile(self, client):
        assert _no_auth_get(client, "/api/users/profile").status_code == 401

    def test_update_profile(self, client):
        assert _no_auth_put(client, "/api/users/profile").status_code == 401

    def test_get_settings(self, client):
        assert _no_auth_get(client, "/api/users/settings").status_code == 401

    def test_update_settings(self, client):
        assert _no_auth_put(client, "/api/users/settings").status_code == 401

    def test_update_password(self, client):
        assert _no_auth_put(client, "/api/users/password").status_code == 401

    def test_delete_user(self, client):
        assert _no_auth_delete(client, "/api/users/delete").status_code == 401

    def test_get_conversations(self, client):
        assert _no_auth_get(client, "/api/users/conversations").status_code == 401

    def test_create_conversation(self, client):
        assert _no_auth_post(client, "/api/users/conversations").status_code == 401

    def test_get_conversation(self, client):
        assert _no_auth_get(client, "/api/users/conversations/conv1").status_code == 401

    def test_update_conversation(self, client):
        assert _no_auth_put(client, "/api/users/conversations/conv1").status_code == 401

    def test_append_conversation_message(self, client):
        assert _no_auth_post(client, "/api/users/conversations/conv1/messages").status_code == 401

    def test_delete_conversation(self, client):
        assert _no_auth_delete(client, "/api/users/conversations/conv1").status_code == 401

    def test_get_ai_digest(self, client):
        assert _no_auth_get(client, "/api/users/ai-digest").status_code == 401

    def test_update_ai_digest(self, client):
        assert _no_auth_put(client, "/api/users/ai-digest").status_code == 401

    def test_get_ai_memory(self, client):
        assert _no_auth_get(client, "/api/users/ai-memory").status_code == 401

    def test_update_ai_memory(self, client):
        assert _no_auth_put(client, "/api/users/ai-memory").status_code == 401

    def test_get_preferences(self, client):
        assert _no_auth_get(client, "/api/users/preferences").status_code == 401

    def test_update_preferences(self, client):
        assert _no_auth_put(client, "/api/users/preferences").status_code == 401

    def test_get_practice_progress(self, client):
        assert _no_auth_get(client, "/api/users/practice-progress").status_code == 401

    def test_update_practice_progress(self, client):
        assert _no_auth_put(client, "/api/users/practice-progress").status_code == 401


# ---------------------------------------------------------------------------
# Classes blueprint
# ---------------------------------------------------------------------------

class TestClassesAuthRequired:
    def test_create_class(self, client):
        assert _no_auth_post(client, "/api/classes").status_code == 401

    def test_get_classes(self, client):
        assert _no_auth_get(client, "/api/classes").status_code == 401

    def test_get_class(self, client):
        assert _no_auth_get(client, "/api/classes/CLS1").status_code == 401

    def test_get_class_resources(self, client):
        assert _no_auth_get(client, "/api/classes/CLS1/resources").status_code == 401

    def test_update_class(self, client):
        assert _no_auth_put(client, "/api/classes/CLS1").status_code == 401

    def test_delete_class(self, client):
        assert _no_auth_delete(client, "/api/classes/CLS1").status_code == 401

    def test_enroll_in_class(self, client):
        assert _no_auth_post(client, "/api/classes/enroll").status_code == 401

    def test_get_enrolled_classes(self, client):
        assert _no_auth_get(client, "/api/classes/enrolled").status_code == 401

    def test_get_class_students(self, client):
        assert _no_auth_get(client, "/api/classes/CLS1/students").status_code == 401

    def test_get_class_progress(self, client):
        assert _no_auth_get(client, "/api/classes/CLS1/progress").status_code == 401

    def test_get_progress(self, client):
        assert _no_auth_get(client, "/api/progress").status_code == 401

    def test_get_student_progress(self, client):
        assert _no_auth_get(client, "/api/students/s1/progress").status_code == 401

    def test_get_class_average_leaderboard(self, client):
        assert _no_auth_get(client, "/api/classes/CLS1/leaderboard/average").status_code == 401

    def test_get_exercise_leaderboard_for_class(self, client):
        assert _no_auth_get(client, "/api/classes/CLS1/leaderboard/exercise/EX1").status_code == 401

    def test_add_class_resource(self, client):
        assert _no_auth_post(client, "/api/classes/CLS1/resources").status_code == 401

    def test_upload_class_resource(self, client):
        assert _no_auth_post(client, "/api/classes/CLS1/resources/upload").status_code == 401


# ---------------------------------------------------------------------------
# Chapters blueprint
# ---------------------------------------------------------------------------

class TestChaptersAuthRequired:
    def test_get_chapter_upload_url(self, client):
        assert _no_auth_get(client, "/api/chapters/upload-url").status_code == 401

    def test_upload_chapter(self, client):
        assert _no_auth_post(client, "/api/classes/CLS1/chapters").status_code == 401

    def test_get_class_chapters(self, client):
        assert _no_auth_get(client, "/api/classes/CLS1/chapters").status_code == 401

    def test_update_chapter(self, client):
        assert _no_auth_put(client, "/api/chapters/ch1").status_code == 401

    def test_delete_chapter(self, client):
        assert _no_auth_delete(client, "/api/chapters/ch1").status_code == 401

    def test_generate_exercises(self, client):
        assert _no_auth_post(client, "/api/chapters/ch1/generate-exercises").status_code == 401

    def test_get_chapter_exercises(self, client):
        assert _no_auth_get(client, "/api/chapters/ch1/exercises").status_code == 401

    def test_create_exercise(self, client):
        assert _no_auth_post(client, "/api/classes/CLS1/chapters/ch1/exercises").status_code == 401


# ---------------------------------------------------------------------------
# Exercises blueprint
# ---------------------------------------------------------------------------

class TestExercisesAuthRequired:
    def test_get_all_progress(self, client):
        assert _no_auth_get(client, "/api/exercises/progress").status_code == 401

    def test_get_exercise_leaderboard(self, client):
        assert _no_auth_get(client, "/api/exercises/ex1/leaderboard").status_code == 401

    def test_get_grand_leaderboard(self, client):
        assert _no_auth_get(client, "/api/leaderboard/grand").status_code == 401

    def test_get_exercise_details(self, client):
        assert _no_auth_get(client, "/api/exercises/ex1").status_code == 401

    def test_update_exercise(self, client):
        assert _no_auth_put(client, "/api/exercises/ex1").status_code == 401

    def test_delete_exercise(self, client):
        assert _no_auth_delete(client, "/api/exercises/ex1").status_code == 401


# ---------------------------------------------------------------------------
# AI blueprint
# ---------------------------------------------------------------------------

class TestAIAuthRequired:
    def test_proxy_ai_chat(self, client):
        assert _no_auth_post(client, "/api/ai/chat").status_code == 401
