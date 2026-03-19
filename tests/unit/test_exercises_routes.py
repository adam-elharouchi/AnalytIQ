"""
tests/test_exercises_routes.py — Behavioral tests for exercise routes.

Covers:
  GET    /api/exercises/progress
  GET    /api/exercises/<exercise_id>/leaderboard
  GET    /api/leaderboard/grand
  GET    /api/exercises/<exercise_id>
  PUT    /api/exercises/<exercise_id>
  DELETE /api/exercises/<exercise_id>
  POST   /api/exercises/<exercise_id>/grade
"""
from datetime import datetime
from unittest.mock import MagicMock

import pytest

AUTH_STUDENT = {"X-Test-User-ID": "student-id", "X-Test-User-Role": "student"}
AUTH_PROF = {"X-Test-User-ID": "prof-id", "X-Test-User-Role": "professor"}

# Canonical DB row shapes (mirrors SELECT column order in exercise_repository.py)
# get_exercise_detail: exercise_id, chapter_id, class_id, title, description, difficulty, solution_code
EXERCISE_ROW = (
    "ex-1", "ch-1", "class-1",
    "Write a loop", "Print 1 to 10", "easy",
    "for i in range(10): print(i)",
)

# get_all_user_progress: exercise_id, exercise_title, best_score, best_accuracy,
#                        total_attempts, completed, last_completed_at
PROGRESS_ROW = ("ex-1", "Write a loop", 85, 0.90, 3, True, datetime(2026, 1, 1))

# get_exercise_leaderboard: name, best_score, best_accuracy, best_time, total_attempts
LEADERBOARD_ROW = ("Alice", 95, 0.95, 120, 3, None)

# get_grand_leaderboard: user_id, name, exercises_completed, average_score, total_score
GRAND_ROW = ("user-1", "Alice", 10, 88.5, 885, None)

# get_exercise_test_cases: function_name, language, test_cases (JSONB list)
TEST_CASES = [{"description": "basic", "input": "[1, 2]", "expected_output": "3", "weight": 1}]
TEST_CASES_ROW = ("solution", "Python", TEST_CASES)

# AI grader result shape (replaces run_test_cases result)
AI_GRADE_RESULT = {
    "total_score": 80,
    "correctness_score": 56,
    "quality_score": 24,
    "feedback": "Your solution correctly solves the task. Consider adding a comment to explain your logic.",
    "passed": True,
    "graded_by": "ai",
}

RUN_CODE_RESULT = {"stdout": "Hello World\n", "stderr": "", "timed_out": False}


# ---------------------------------------------------------------------------
# GET /api/exercises/progress
# ---------------------------------------------------------------------------


class TestGetExerciseProgress:
    def test_returns_200_with_progress_key(self, client, mock_db):
        mock_db.cursor().fetchall.return_value = [PROGRESS_ROW]
        resp = client.get("/api/exercises/progress", headers=AUTH_STUDENT)
        assert resp.status_code == 200
        assert "progress" in resp.get_json()

    def test_progress_entry_has_all_required_fields(self, client, mock_db):
        mock_db.cursor().fetchall.return_value = [PROGRESS_ROW]
        resp = client.get("/api/exercises/progress", headers=AUTH_STUDENT)
        entry = resp.get_json()["progress"][0]
        for field in ("exercise_id", "exercise_title", "best_score",
                      "best_accuracy", "total_attempts", "completed",
                      "last_completed_at"):
            assert field in entry, f"Missing field: {field}"

    def test_progress_values_match_db_row(self, client, mock_db):
        mock_db.cursor().fetchall.return_value = [PROGRESS_ROW]
        resp = client.get("/api/exercises/progress", headers=AUTH_STUDENT)
        entry = resp.get_json()["progress"][0]
        assert entry["exercise_id"] == "ex-1"
        assert entry["best_score"] == 85
        assert entry["completed"] is True

    def test_null_score_defaults_to_zero(self, client, mock_db):
        row = ("ex-2", "Exercise 2", None, None, None, None, None)
        mock_db.cursor().fetchall.return_value = [row]
        resp = client.get("/api/exercises/progress", headers=AUTH_STUDENT)
        entry = resp.get_json()["progress"][0]
        assert entry["best_score"] == 0
        assert entry["best_accuracy"] == 0
        assert entry["total_attempts"] == 0
        assert entry["completed"] is False
        assert entry["last_completed_at"] is None

    def test_empty_progress_returns_empty_list(self, client, mock_db):
        mock_db.cursor().fetchall.return_value = []
        resp = client.get("/api/exercises/progress", headers=AUTH_STUDENT)
        assert resp.status_code == 200
        assert resp.get_json()["progress"] == []

    def test_multiple_exercises_all_returned(self, client, mock_db):
        rows = [
            ("ex-1", "Ex 1", 80, 0.80, 2, True, datetime(2026, 1, 1)),
            ("ex-2", "Ex 2", 60, 0.60, 1, True, datetime(2026, 1, 2)),
            ("ex-3", "Ex 3", 0, 0, 0, False, None),
        ]
        mock_db.cursor().fetchall.return_value = rows
        resp = client.get("/api/exercises/progress", headers=AUTH_STUDENT)
        assert len(resp.get_json()["progress"]) == 3

    def test_no_auth_returns_401(self, client, mock_db):
        resp = client.get("/api/exercises/progress")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/exercises/<exercise_id>/leaderboard
# ---------------------------------------------------------------------------


class TestGetExerciseLeaderboard:
    def test_returns_200_with_leaderboard_key(self, client, mock_db):
        mock_db.cursor().fetchall.return_value = [LEADERBOARD_ROW]
        resp = client.get("/api/exercises/ex-1/leaderboard", headers=AUTH_STUDENT)
        assert resp.status_code == 200
        assert "leaderboard" in resp.get_json()

    def test_entry_has_rank_name_score_accuracy_time_attempts(self, client, mock_db):
        mock_db.cursor().fetchall.return_value = [LEADERBOARD_ROW]
        resp = client.get("/api/exercises/ex-1/leaderboard", headers=AUTH_STUDENT)
        entry = resp.get_json()["leaderboard"][0]
        for field in ("rank", "name", "best_score", "best_accuracy",
                      "best_time", "total_attempts"):
            assert field in entry, f"Missing field: {field}"

    def test_email_not_exposed_in_response(self, client, mock_db):
        mock_db.cursor().fetchall.return_value = [LEADERBOARD_ROW]
        resp = client.get("/api/exercises/ex-1/leaderboard", headers=AUTH_STUDENT)
        entry = resp.get_json()["leaderboard"][0]
        assert "email" not in entry

    def test_rank_starts_at_1(self, client, mock_db):
        mock_db.cursor().fetchall.return_value = [LEADERBOARD_ROW]
        resp = client.get("/api/exercises/ex-1/leaderboard", headers=AUTH_STUDENT)
        assert resp.get_json()["leaderboard"][0]["rank"] == 1

    def test_rank_increments_sequentially(self, client, mock_db):
        rows = [
            ("Alice", 95, 0.95, 120, 3, None),
            ("Bob", 88, 0.88, 150, 2, None),
            ("Charlie", 75, 0.75, 200, 1, None),
        ]
        mock_db.cursor().fetchall.return_value = rows
        resp = client.get("/api/exercises/ex-1/leaderboard", headers=AUTH_STUDENT)
        ranks = [e["rank"] for e in resp.get_json()["leaderboard"]]
        assert ranks == [1, 2, 3]

    def test_null_accuracy_defaults_to_zero(self, client, mock_db):
        mock_db.cursor().fetchall.return_value = [("Alice", 80, None, 100, 2, None)]
        resp = client.get("/api/exercises/ex-1/leaderboard", headers=AUTH_STUDENT)
        assert resp.get_json()["leaderboard"][0]["best_accuracy"] == 0

    def test_null_attempts_defaults_to_zero(self, client, mock_db):
        mock_db.cursor().fetchall.return_value = [("Alice", 80, 0.8, 100, None, None)]
        resp = client.get("/api/exercises/ex-1/leaderboard", headers=AUTH_STUDENT)
        assert resp.get_json()["leaderboard"][0]["total_attempts"] == 0

    def test_empty_leaderboard_returns_empty_list(self, client, mock_db):
        mock_db.cursor().fetchall.return_value = []
        resp = client.get("/api/exercises/ex-1/leaderboard", headers=AUTH_STUDENT)
        assert resp.status_code == 200
        assert resp.get_json()["leaderboard"] == []

    def test_limit_param_accepted(self, client, mock_db):
        mock_db.cursor().fetchall.return_value = []
        resp = client.get("/api/exercises/ex-1/leaderboard?limit=3", headers=AUTH_STUDENT)
        assert resp.status_code == 200

    def test_no_auth_returns_401(self, client, mock_db):
        resp = client.get("/api/exercises/ex-1/leaderboard")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/leaderboard/grand
# ---------------------------------------------------------------------------


class TestGetGrandLeaderboard:
    def test_returns_200_with_leaderboard_key(self, client, mock_db):
        mock_db.cursor().fetchall.return_value = [GRAND_ROW]
        resp = client.get("/api/leaderboard/grand", headers=AUTH_STUDENT)
        assert resp.status_code == 200
        assert "leaderboard" in resp.get_json()

    def test_entry_has_all_required_fields(self, client, mock_db):
        mock_db.cursor().fetchall.return_value = [GRAND_ROW]
        resp = client.get("/api/leaderboard/grand", headers=AUTH_STUDENT)
        entry = resp.get_json()["leaderboard"][0]
        for field in ("rank", "user_id", "name", "exercises_completed",
                      "average_score", "total_score"):
            assert field in entry, f"Missing field: {field}"

    def test_email_not_exposed_in_response(self, client, mock_db):
        mock_db.cursor().fetchall.return_value = [GRAND_ROW]
        resp = client.get("/api/leaderboard/grand", headers=AUTH_STUDENT)
        assert "email" not in resp.get_json()["leaderboard"][0]

    def test_rank_starts_at_1(self, client, mock_db):
        mock_db.cursor().fetchall.return_value = [GRAND_ROW]
        resp = client.get("/api/leaderboard/grand", headers=AUTH_STUDENT)
        assert resp.get_json()["leaderboard"][0]["rank"] == 1

    def test_null_scores_default_to_zero(self, client, mock_db):
        mock_db.cursor().fetchall.return_value = [("user-1", "Alice", 5, None, None, None)]
        resp = client.get("/api/leaderboard/grand", headers=AUTH_STUDENT)
        entry = resp.get_json()["leaderboard"][0]
        assert entry["average_score"] == 0
        assert entry["total_score"] == 0

    def test_empty_grand_leaderboard_returns_empty_list(self, client, mock_db):
        mock_db.cursor().fetchall.return_value = []
        resp = client.get("/api/leaderboard/grand", headers=AUTH_STUDENT)
        assert resp.status_code == 200
        assert resp.get_json()["leaderboard"] == []

    def test_limit_param_accepted(self, client, mock_db):
        mock_db.cursor().fetchall.return_value = []
        resp = client.get("/api/leaderboard/grand?limit=5", headers=AUTH_STUDENT)
        assert resp.status_code == 200

    def test_multiple_entries_all_returned(self, client, mock_db):
        rows = [
            ("u1", "Alice", 10, 92.0, 920, None),
            ("u2", "Bob", 8, 85.0, 680, None),
        ]
        mock_db.cursor().fetchall.return_value = rows
        resp = client.get("/api/leaderboard/grand", headers=AUTH_STUDENT)
        assert len(resp.get_json()["leaderboard"]) == 2

    def test_no_auth_returns_401(self, client, mock_db):
        resp = client.get("/api/leaderboard/grand")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/exercises/<exercise_id>
# ---------------------------------------------------------------------------


class TestGetExerciseDetails:
    def test_returns_200_with_exercise_key(self, client, mock_db):
        mock_db.cursor().fetchone.return_value = EXERCISE_ROW
        resp = client.get("/api/exercises/ex-1", headers=AUTH_STUDENT)
        assert resp.status_code == 200
        assert "exercise" in resp.get_json()

    def test_exercise_has_all_seven_fields(self, client, mock_db):
        mock_db.cursor().fetchone.return_value = EXERCISE_ROW
        resp = client.get("/api/exercises/ex-1", headers=AUTH_STUDENT)
        ex = resp.get_json()["exercise"]
        for field in ("exercise_id", "chapter_id", "class_id", "title",
                      "description", "difficulty", "solution_code"):
            assert field in ex, f"Missing field: {field}"

    def test_exercise_values_match_db_row(self, client, mock_db):
        mock_db.cursor().fetchone.return_value = EXERCISE_ROW
        resp = client.get("/api/exercises/ex-1", headers=AUTH_STUDENT)
        ex = resp.get_json()["exercise"]
        assert ex["exercise_id"] == "ex-1"
        assert ex["title"] == "Write a loop"
        assert ex["difficulty"] == "easy"
        assert ex["description"] == "Print 1 to 10"
        assert "range(10)" in ex["solution_code"]

    def test_not_found_returns_404_with_error(self, client, mock_db):
        mock_db.cursor().fetchone.return_value = None
        resp = client.get("/api/exercises/nonexistent", headers=AUTH_STUDENT)
        assert resp.status_code == 404
        assert "error" in resp.get_json()

    def test_no_auth_returns_401(self, client, mock_db):
        resp = client.get("/api/exercises/ex-1")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PUT /api/exercises/<exercise_id>
# ---------------------------------------------------------------------------


class TestUpdateExercise:
    def test_owner_can_update_title(self, client, mock_db):
        mock_db.cursor().fetchone.return_value = ("prof-id",)  # get_exercise_owner
        resp = client.put("/api/exercises/ex-1", headers=AUTH_PROF,
                          json={"title": "New Title"})
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_owner_can_update_difficulty(self, client, mock_db):
        mock_db.cursor().fetchone.return_value = ("prof-id",)
        resp = client.put("/api/exercises/ex-1", headers=AUTH_PROF,
                          json={"difficulty": "hard"})
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_owner_can_update_solution_code(self, client, mock_db):
        mock_db.cursor().fetchone.return_value = ("prof-id",)
        resp = client.put("/api/exercises/ex-1", headers=AUTH_PROF,
                          json={"solution_code": "def solution(): return 42"})
        assert resp.status_code == 200

    def test_non_owner_gets_403(self, client, mock_db):
        mock_db.cursor().fetchone.return_value = ("other-prof-id",)
        resp = client.put("/api/exercises/ex-1", headers=AUTH_PROF,
                          json={"title": "Hijacked"})
        assert resp.status_code == 403

    def test_exercise_not_found_returns_403(self, client, mock_db):
        # owner is None → treated as not authorized
        mock_db.cursor().fetchone.return_value = None
        resp = client.put("/api/exercises/ex-1", headers=AUTH_PROF,
                          json={"title": "Ghost"})
        assert resp.status_code == 403

    def test_title_too_long_returns_400(self, client, mock_db):
        long_title = "x" * 10_000
        resp = client.put("/api/exercises/ex-1", headers=AUTH_PROF,
                          json={"title": long_title})
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_empty_body_accepted_by_owner(self, client, mock_db):
        mock_db.cursor().fetchone.return_value = ("prof-id",)
        resp = client.put("/api/exercises/ex-1", headers=AUTH_PROF, json={})
        assert resp.status_code == 200

    def test_no_auth_returns_401(self, client, mock_db):
        resp = client.put("/api/exercises/ex-1", json={"title": "X"})
        assert resp.status_code == 401

    def test_commit_called_on_success(self, client, mock_db):
        mock_db.cursor().fetchone.return_value = ("prof-id",)
        client.put("/api/exercises/ex-1", headers=AUTH_PROF,
                   json={"title": "Updated"})
        mock_db.commit.assert_called()


# ---------------------------------------------------------------------------
# DELETE /api/exercises/<exercise_id>
# ---------------------------------------------------------------------------


class TestDeleteExercise:
    def test_delete_returns_200_with_success_flag(self, client, mock_db):
        mock_db.cursor().fetchone.return_value = ("ch-1", "class-1")  # get_exercise_location
        resp = client.delete("/api/exercises/ex-1", headers=AUTH_PROF)
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_not_found_returns_404_with_error(self, client, mock_db):
        mock_db.cursor().fetchone.return_value = None
        resp = client.delete("/api/exercises/nonexistent", headers=AUTH_PROF)
        assert resp.status_code == 404
        assert "error" in resp.get_json()

    def test_no_auth_returns_401(self, client, mock_db):
        resp = client.delete("/api/exercises/ex-1")
        assert resp.status_code == 401

    def test_commit_called_after_delete(self, client, mock_db):
        mock_db.cursor().fetchone.return_value = ("ch-1", "class-1")
        client.delete("/api/exercises/ex-1", headers=AUTH_PROF)
        mock_db.commit.assert_called()

    def test_delete_query_executed(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = ("ch-1", "class-1")
        client.delete("/api/exercises/ex-1", headers=AUTH_PROF)
        assert cursor.execute.called


# ---------------------------------------------------------------------------
# POST /api/exercises/<exercise_id>/grade
# ---------------------------------------------------------------------------


class TestGradeExercise:
    """
    Grading uses AI (grade_with_ai) instead of test cases.
    Fetchone sequence per request:
      [0] get_exercise_detail   → EXERCISE_ROW
      [1] get_exercise_test_cases → TEST_CASES_ROW  (language lookup)
      [2+] flywheel calls (wrapped in try/except — failures are silent)
    """

    def _setup_db(self, mock_db, detail_row=EXERCISE_ROW, lang_row=TEST_CASES_ROW):
        mock_db.cursor().fetchone.side_effect = [detail_row, lang_row]

    def test_empty_code_returns_400(self, client, mock_db):
        resp = client.post("/api/exercises/ex-1/grade",
                           headers=AUTH_STUDENT, json={"code": ""})
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_whitespace_only_code_returns_400(self, client, mock_db):
        resp = client.post("/api/exercises/ex-1/grade",
                           headers=AUTH_STUDENT, json={"code": "   \n\t  "})
        assert resp.status_code == 400

    def test_missing_code_field_returns_400(self, client, mock_db):
        resp = client.post("/api/exercises/ex-1/grade",
                           headers=AUTH_STUDENT, json={})
        assert resp.status_code == 400

    def test_exercise_not_found_returns_404(self, client, mock_db):
        mock_db.cursor().fetchone.return_value = None
        resp = client.post("/api/exercises/ex-1/grade",
                           headers=AUTH_STUDENT, json={"code": "print(1)"})
        assert resp.status_code == 404
        assert "error" in resp.get_json()

    def test_valid_submission_returns_200(self, client, mock_db, monkeypatch):
        self._setup_db(mock_db)
        monkeypatch.setattr("blueprints.exercises.run_code", lambda *a, **kw: RUN_CODE_RESULT)
        monkeypatch.setattr("blueprints.exercises.grade_with_ai", lambda **kw: AI_GRADE_RESULT)
        resp = client.post("/api/exercises/ex-1/grade",
                           headers=AUTH_STUDENT,
                           json={"code": "print('Hello World')"})
        assert resp.status_code == 200

    def test_response_includes_required_fields(self, client, mock_db, monkeypatch):
        self._setup_db(mock_db)
        monkeypatch.setattr("blueprints.exercises.run_code", lambda *a, **kw: RUN_CODE_RESULT)
        monkeypatch.setattr("blueprints.exercises.grade_with_ai", lambda **kw: AI_GRADE_RESULT)
        data = client.post("/api/exercises/ex-1/grade",
                           headers=AUTH_STUDENT,
                           json={"code": "print('Hello World')"}).get_json()
        for field in ("total_score", "correctness_score", "quality_score",
                      "feedback", "passed", "graded_by", "output"):
            assert field in data, f"Missing field: {field}"

    def test_graded_by_is_ai(self, client, mock_db, monkeypatch):
        self._setup_db(mock_db)
        monkeypatch.setattr("blueprints.exercises.run_code", lambda *a, **kw: RUN_CODE_RESULT)
        monkeypatch.setattr("blueprints.exercises.grade_with_ai", lambda **kw: AI_GRADE_RESULT)
        data = client.post("/api/exercises/ex-1/grade",
                           headers=AUTH_STUDENT,
                           json={"code": "print('Hello World')"}).get_json()
        assert data["graded_by"] == "ai"

    def test_total_score_within_0_to_100(self, client, mock_db, monkeypatch):
        self._setup_db(mock_db)
        monkeypatch.setattr("blueprints.exercises.run_code", lambda *a, **kw: RUN_CODE_RESULT)
        monkeypatch.setattr("blueprints.exercises.grade_with_ai", lambda **kw: AI_GRADE_RESULT)
        score = client.post("/api/exercises/ex-1/grade",
                            headers=AUTH_STUDENT,
                            json={"code": "print('Hello World')"}).get_json()["total_score"]
        assert 0 <= score <= 100

    def test_ai_grader_receives_db_language_not_client(self, client, mock_db, monkeypatch):
        """Language must come from DB — client cannot override it."""
        captured = {}

        def capture_grader(**kw):
            captured.update(kw)
            return AI_GRADE_RESULT

        self._setup_db(mock_db)  # DB says Python
        monkeypatch.setattr("blueprints.exercises.run_code", lambda *a, **kw: RUN_CODE_RESULT)
        monkeypatch.setattr("blueprints.exercises.grade_with_ai", capture_grader)

        client.post("/api/exercises/ex-1/grade",
                    headers=AUTH_STUDENT,
                    json={"code": "print(1)", "language": "SQL"})  # SQL should be ignored

        assert captured.get("language") == "Python"

    def test_ai_feedback_in_response(self, client, mock_db, monkeypatch):
        self._setup_db(mock_db)
        monkeypatch.setattr("blueprints.exercises.run_code", lambda *a, **kw: RUN_CODE_RESULT)
        monkeypatch.setattr("blueprints.exercises.grade_with_ai", lambda **kw: AI_GRADE_RESULT)
        data = client.post("/api/exercises/ex-1/grade",
                           headers=AUTH_STUDENT,
                           json={"code": "print('Hello World')"}).get_json()
        assert data["feedback"] == AI_GRADE_RESULT["feedback"]

    def test_stdout_in_output_field(self, client, mock_db, monkeypatch):
        self._setup_db(mock_db)
        monkeypatch.setattr("blueprints.exercises.run_code",
                            lambda *a, **kw: {"stdout": "42\n", "stderr": "", "timed_out": False})
        monkeypatch.setattr("blueprints.exercises.grade_with_ai", lambda **kw: AI_GRADE_RESULT)
        data = client.post("/api/exercises/ex-1/grade",
                           headers=AUTH_STUDENT,
                           json={"code": "print(42)"}).get_json()
        assert data["output"] == "42\n"

    def test_perfect_score_from_ai(self, client, mock_db, monkeypatch):
        perfect = {**AI_GRADE_RESULT, "total_score": 100, "correctness_score": 70,
                   "quality_score": 30, "passed": True}
        self._setup_db(mock_db)
        monkeypatch.setattr("blueprints.exercises.run_code", lambda *a, **kw: RUN_CODE_RESULT)
        monkeypatch.setattr("blueprints.exercises.grade_with_ai", lambda **kw: perfect)
        assert client.post("/api/exercises/ex-1/grade",
                           headers=AUTH_STUDENT,
                           json={"code": "print('perfect')"}).get_json()["total_score"] == 100

    def test_zero_score_from_ai(self, client, mock_db, monkeypatch):
        zero = {**AI_GRADE_RESULT, "total_score": 0, "correctness_score": 0,
                "quality_score": 0, "passed": False}
        self._setup_db(mock_db)
        monkeypatch.setattr("blueprints.exercises.run_code", lambda *a, **kw: RUN_CODE_RESULT)
        monkeypatch.setattr("blueprints.exercises.grade_with_ai", lambda **kw: zero)
        assert client.post("/api/exercises/ex-1/grade",
                           headers=AUTH_STUDENT,
                           json={"code": "print('wrong')"}).get_json()["total_score"] == 0

    def test_no_auth_returns_401(self, client, mock_db):
        resp = client.post("/api/exercises/ex-1/grade", json={"code": "print(1)"})
        assert resp.status_code == 401

    def test_commit_called_after_successful_grade(self, client, mock_db, monkeypatch):
        self._setup_db(mock_db)
        monkeypatch.setattr("blueprints.exercises.run_code", lambda *a, **kw: RUN_CODE_RESULT)
        monkeypatch.setattr("blueprints.exercises.grade_with_ai", lambda **kw: AI_GRADE_RESULT)
        client.post("/api/exercises/ex-1/grade",
                    headers=AUTH_STUDENT, json={"code": "print('Hello World')"})
        assert mock_db.cursor().execute.called
