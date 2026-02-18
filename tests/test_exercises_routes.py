"""
tests/test_exercises_routes.py — Behavioral tests for exercise routes.

Covers:
  GET  /api/exercises/progress
  GET  /api/exercises/<exercise_id>/leaderboard
  GET  /api/leaderboard/grand
  GET  /api/exercises/<exercise_id>
  PUT  /api/exercises/<exercise_id>
  DELETE /api/exercises/<exercise_id>
"""
import pytest
from datetime import datetime
from unittest.mock import MagicMock

AUTH_STUDENT = {"X-Test-User-ID": "student-user-id", "X-Test-User-Role": "student"}
AUTH_PROF = {"X-Test-User-ID": "prof-user-id", "X-Test-User-Role": "professor"}


# ---------------------------------------------------------------------------
# GET /api/exercises/progress — progress for authenticated user
# ---------------------------------------------------------------------------

class TestGetExerciseProgress:
    def test_returns_200_with_progress_key(self, client, mock_db):
        """Authenticated user gets progress list."""
        cursor = mock_db.cursor()
        cursor.fetchall.return_value = [
            ("ex-1", "Exercise 1", 85, 0.9, 3, True, datetime.now()),
        ]

        resp = client.get("/api/exercises/progress", headers=AUTH_STUDENT)

        assert resp.status_code == 200
        data = resp.get_json()
        assert "progress" in data

    def test_progress_entry_has_expected_fields(self, client, mock_db):
        """Each progress entry has exercise_id, best_score, completed."""
        cursor = mock_db.cursor()
        cursor.fetchall.return_value = [
            ("ex-1", "Exercise 1", 90, 0.95, 5, True, datetime.now()),
        ]

        resp = client.get("/api/exercises/progress", headers=AUTH_STUDENT)

        assert resp.status_code == 200
        data = resp.get_json()
        entry = data["progress"][0]
        assert "exercise_id" in entry
        assert "best_score" in entry
        assert "completed" in entry

    def test_no_auth_returns_401(self, client, mock_db):
        """Unauthenticated request returns 401."""
        resp = client.get("/api/exercises/progress")
        assert resp.status_code == 401

    def test_empty_progress_returns_empty_list(self, client, mock_db):
        """User with no attempts gets empty progress list."""
        cursor = mock_db.cursor()
        cursor.fetchall.return_value = []

        resp = client.get("/api/exercises/progress", headers=AUTH_STUDENT)

        assert resp.status_code == 200
        assert resp.get_json()["progress"] == []


# ---------------------------------------------------------------------------
# GET /api/exercises/<exercise_id>/leaderboard — exercise leaderboard
# ---------------------------------------------------------------------------

class TestGetExerciseLeaderboard:
    def test_returns_200_with_leaderboard_key(self, client, mock_db):
        """Authenticated user gets exercise leaderboard."""
        cursor = mock_db.cursor()
        cursor.fetchall.return_value = [
            ("Alice", "alice@example.com", 95, 0.95, 120, 3),
            ("Bob", "bob@example.com", 88, 0.88, 150, 2),
        ]

        resp = client.get("/api/exercises/ex-1/leaderboard", headers=AUTH_STUDENT)

        assert resp.status_code == 200
        data = resp.get_json()
        assert "leaderboard" in data

    def test_leaderboard_entries_have_rank_and_name(self, client, mock_db):
        """Each entry has rank, name, best_score (no email exposed)."""
        cursor = mock_db.cursor()
        cursor.fetchall.return_value = [
            ("Alice", "alice@example.com", 95, 0.95, 120, 3),
        ]

        resp = client.get("/api/exercises/ex-1/leaderboard", headers=AUTH_STUDENT)

        assert resp.status_code == 200
        entry = resp.get_json()["leaderboard"][0]
        assert "rank" in entry
        assert "name" in entry
        assert "best_score" in entry
        # Email must NOT be in the leaderboard response (Task 14A)
        assert "email" not in entry

    def test_no_auth_returns_401(self, client, mock_db):
        """Unauthenticated request returns 401."""
        resp = client.get("/api/exercises/ex-1/leaderboard")
        assert resp.status_code == 401

    def test_empty_leaderboard_returns_empty_list(self, client, mock_db):
        """Exercise with no completions returns empty leaderboard."""
        cursor = mock_db.cursor()
        cursor.fetchall.return_value = []

        resp = client.get("/api/exercises/ex-1/leaderboard", headers=AUTH_STUDENT)

        assert resp.status_code == 200
        assert resp.get_json()["leaderboard"] == []


# ---------------------------------------------------------------------------
# GET /api/leaderboard/grand — grand leaderboard
# ---------------------------------------------------------------------------

class TestGetGrandLeaderboard:
    def test_returns_200_with_leaderboard_key(self, client, mock_db):
        """Authenticated user gets grand leaderboard."""
        cursor = mock_db.cursor()
        cursor.fetchall.return_value = [
            ("user-1", "Alice", "alice@example.com", 10, 88.5, 885),
        ]

        resp = client.get("/api/leaderboard/grand", headers=AUTH_STUDENT)

        assert resp.status_code == 200
        data = resp.get_json()
        assert "leaderboard" in data

    def test_grand_leaderboard_no_auth_returns_401(self, client, mock_db):
        """Unauthenticated request is denied."""
        resp = client.get("/api/leaderboard/grand")
        assert resp.status_code == 401

    def test_grand_leaderboard_entries_have_rank_and_no_email(self, client, mock_db):
        """Grand leaderboard entries have rank, name, exercises_completed, no email."""
        cursor = mock_db.cursor()
        cursor.fetchall.return_value = [
            ("user-1", "Alice", "alice@example.com", 10, 88.5, 885),
        ]

        resp = client.get("/api/leaderboard/grand", headers=AUTH_STUDENT)

        assert resp.status_code == 200
        entry = resp.get_json()["leaderboard"][0]
        assert "rank" in entry
        assert "name" in entry
        assert "exercises_completed" in entry
        # Email must NOT be in the grand leaderboard response
        assert "email" not in entry

    def test_grand_leaderboard_respects_limit_param(self, client, mock_db):
        """Custom limit parameter is accepted."""
        cursor = mock_db.cursor()
        cursor.fetchall.return_value = []

        resp = client.get("/api/leaderboard/grand?limit=5", headers=AUTH_STUDENT)

        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/exercises/<exercise_id> — exercise detail
# ---------------------------------------------------------------------------

class TestGetExerciseDetails:
    def test_returns_exercise_details(self, client, mock_db):
        """Returns full exercise object with key fields."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (
            "ex-1", "ch-1", "class-abc", "Write a loop",
            "Print 1 to 10", "easy", "for i in range(10): print(i)"
        )

        resp = client.get("/api/exercises/ex-1", headers=AUTH_STUDENT)

        assert resp.status_code == 200
        data = resp.get_json()
        assert "exercise" in data
        exercise = data["exercise"]
        assert exercise["exercise_id"] == "ex-1"
        assert exercise["title"] == "Write a loop"
        assert exercise["difficulty"] == "easy"

    def test_exercise_not_found_returns_404(self, client, mock_db):
        """Non-existent exercise returns 404."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None

        resp = client.get("/api/exercises/nonexistent", headers=AUTH_STUDENT)

        assert resp.status_code == 404
        assert "error" in resp.get_json()

    def test_no_auth_returns_401(self, client, mock_db):
        """Unauthenticated request returns 401."""
        resp = client.get("/api/exercises/ex-1")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PUT /api/exercises/<exercise_id> — update exercise
# ---------------------------------------------------------------------------

class TestUpdateExercise:
    def test_owner_updates_exercise_returns_200(self, client, mock_db):
        """Exercise owner can update the exercise."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = ("prof-user-id",)  # get_exercise_owner

        resp = client.put(
            "/api/exercises/ex-1",
            headers=AUTH_PROF,
            json={"title": "Updated Title", "difficulty": "hard"},
        )

        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_non_owner_gets_403(self, client, mock_db):
        """Non-owner cannot update exercise."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = ("different-prof-id",)

        resp = client.put(
            "/api/exercises/ex-1",
            headers=AUTH_PROF,
            json={"title": "Hacked"},
        )

        assert resp.status_code == 403

    def test_no_auth_returns_401(self, client, mock_db):
        """Unauthenticated request returns 401."""
        resp = client.put("/api/exercises/ex-1", json={"title": "X"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /api/exercises/<exercise_id> — delete exercise
# ---------------------------------------------------------------------------

class TestDeleteExercise:
    def test_deletes_exercise_returns_200(self, client, mock_db):
        """Successful delete returns 200 with success flag."""
        cursor = mock_db.cursor()
        # get_exercise_location -> (chapter_id,)
        cursor.fetchone.return_value = ("ch-1",)

        resp = client.delete("/api/exercises/ex-1", headers=AUTH_PROF)

        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_exercise_not_found_returns_404(self, client, mock_db):
        """Non-existent exercise returns 404."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None

        resp = client.delete("/api/exercises/nonexistent", headers=AUTH_PROF)

        assert resp.status_code == 404
        assert "error" in resp.get_json()

    def test_no_auth_returns_401(self, client, mock_db):
        """Unauthenticated request returns 401."""
        resp = client.delete("/api/exercises/ex-1")
        assert resp.status_code == 401
