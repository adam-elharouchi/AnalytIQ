"""
tests/unit/test_ags_grade_passback.py — Behavioral tests for AGS grade passback.

Covers two layers:
  1. _push_ags_grade() unit tests — call the helper directly with a mock DB conn
     to verify it calls/skips the LMS AGS service correctly.

  2. POST /api/exercises/<id>/grade integration tests — verifies that the grade
     endpoint calls _push_ags_grade when a student has an lti_sub, and that a
     passback failure never blocks the student from receiving their grade.

Fetchone call order inside grade_exercise (test-cases-present, no retroactive gen):
  [0] get_exercise_test_cases         → ("solution", "Python", TEST_CASES)
  [1] get_exercise_location           → ("ch-1", "class-1")
  [2] get_generation_event_by_exercise → None
  [3] get_outcome_count_for_user_exercise → (0,)
  [4] insert_outcome_event RETURNING  → ("some-uuid",)
  [5] SELECT lti_sub FROM users       → ("lti-sub-123",)  ← AGS block
"""

from unittest.mock import MagicMock, patch, call

import pytest

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

AUTH_STUDENT = {"X-Test-User-ID": "student-id", "X-Test-User-Role": "student"}

TEST_CASES = [{"description": "basic", "input": "[1, 2]", "expected_output": "3", "weight": 1}]
TEST_CASES_ROW = ("solution", "Python", TEST_CASES)
EXERCISE_ROW = ("ex-1", "ch-1", "class-1", "Write a loop", "Print 1 to 10", "easy",
                "for i in range(10): print(i)")

# AI grader result that replaces the old run_test_cases result
GRADE_RESULT = {
    "total_score": 80,
    "correctness_score": 56,
    "quality_score": 24,
    "feedback": "Good work! Your solution solves the task correctly.",
    "passed": True,
    "graded_by": "ai",
}

RUN_CODE_RESULT = {"stdout": "Hello\n", "stderr": "", "timed_out": False}

# Fetchone side_effect for a successful grade with lti_sub present
# New order (AI grading flow):
#   [0] get_exercise_detail
#   [1] get_exercise_test_cases  (language lookup)
#   [2] get_exercise_location
#   [3] get_generation_event_by_exercise
#   [4] get_outcome_count_for_user_exercise
#   [5] insert_outcome_event RETURNING id
#   [6] SELECT lti_sub FROM users
def _fetchone_seq(lti_sub=("lti-sub-abc",)):
    return [
        EXERCISE_ROW,          # get_exercise_detail
        TEST_CASES_ROW,        # get_exercise_test_cases (language lookup)
        ("ch-1", "class-1"),   # get_exercise_location
        None,                   # get_generation_event_by_exercise
        (0,),                   # get_outcome_count_for_user_exercise
        ("evt-uuid-1",),        # insert_outcome_event RETURNING id
        lti_sub,                # SELECT lti_sub FROM users
    ]


# ---------------------------------------------------------------------------
# 1.  _push_ags_grade() unit tests
# ---------------------------------------------------------------------------


class TestPushAgsGradeHelper:
    """Direct unit tests for _push_ags_grade without going through HTTP."""

    def _make_conn(self, class_row):
        """Return a mock DB conn whose cursor().fetchone() returns class_row."""
        cur = MagicMock()
        cur.fetchone.return_value = class_row
        conn = MagicMock()
        conn.cursor.return_value = cur
        return conn

    def test_returns_silently_when_class_not_found(self):
        conn = self._make_conn(None)
        from blueprints.lti import _push_ags_grade

        # Should not raise
        _push_ags_grade(conn, "class-missing", "ex-1", "lti-user-1", 80)

    def test_returns_silently_when_ags_disabled(self):
        # ags_enabled=False
        conn = self._make_conn((False, "https://canvas.example/ags", "https://canvas.example"))
        from blueprints.lti import _push_ags_grade

        _push_ags_grade(conn, "class-1", "ex-1", "lti-user-1", 80)

    def test_returns_silently_when_lineitems_url_missing(self):
        # ags_enabled=True but no URL
        conn = self._make_conn((True, None, "https://canvas.example"))
        from blueprints.lti import _push_ags_grade

        _push_ags_grade(conn, "class-1", "ex-1", "lti-user-1", 80)

    def test_raises_when_pylti1p3_not_installed(self):
        conn = self._make_conn((True, "https://canvas.example/ags", "https://canvas.example"))
        from blueprints.lti import _push_ags_grade
        import sys

        # Temporarily hide pylti1p3 to simulate ImportError
        hidden = {}
        for mod_name in list(sys.modules.keys()):
            if "pylti1p3" in mod_name:
                hidden[mod_name] = sys.modules.pop(mod_name)

        try:
            with patch.dict("sys.modules", {"pylti1p3.assignments_grades": None,
                                            "pylti1p3.grade": None,
                                            "pylti1p3.lineitem": None}):
                with pytest.raises((RuntimeError, ImportError)):
                    _push_ags_grade(conn, "class-1", "ex-1", "lti-user-1", 80)
        finally:
            sys.modules.update(hidden)

    def test_raises_when_tool_conf_not_configured(self):
        conn = self._make_conn((True, "https://canvas.example/ags", "https://canvas.example"))

        with patch("blueprints.lti._build_tool_conf", return_value=None):
            from blueprints.lti import _push_ags_grade

            with pytest.raises(RuntimeError, match="LTI tool not configured"):
                _push_ags_grade(conn, "class-1", "ex-1", "lti-user-1", 80)

    def test_calls_ags_put_grade_when_fully_configured(self):
        """AGS service's put_grade is invoked when class is fully configured."""
        conn = self._make_conn(
            (True, "https://canvas.example/lineitems", "https://canvas.example")
        )
        mock_tool_conf = MagicMock()
        mock_ags_instance = MagicMock()

        # pylti1p3 imports are local to the function; patch at the module level
        with patch("blueprints.lti._build_tool_conf", return_value=mock_tool_conf), \
             patch("pylti1p3.assignments_grades.AssignmentsGradesService",
                   return_value=mock_ags_instance), \
             patch("pylti1p3.grade.Grade"), \
             patch("pylti1p3.lineitem.LineItem"):
            from blueprints.lti import _push_ags_grade
            _push_ags_grade(conn, "class-1", "ex-1", "lti-user-abc", 75)

        mock_ags_instance.put_grade.assert_called_once()

    def test_ags_service_constructed_with_correct_issuer(self):
        issuer = "https://my-lms.example.edu"
        conn = self._make_conn(
            (True, "https://my-lms.example.edu/ags/lineitems", issuer)
        )
        mock_tool_conf = MagicMock()
        captured_args = {}

        def capture_ags(tool_conf, service_data, iss, **kw):
            captured_args.update({"issuer": iss, "service_data": service_data})
            return MagicMock()

        with patch("blueprints.lti._build_tool_conf", return_value=mock_tool_conf), \
             patch("pylti1p3.assignments_grades.AssignmentsGradesService",
                   side_effect=capture_ags), \
             patch("pylti1p3.grade.Grade"), \
             patch("pylti1p3.lineitem.LineItem"):
            from blueprints.lti import _push_ags_grade
            _push_ags_grade(conn, "class-1", "ex-1", "user-x", 90)

        assert captured_args["issuer"] == issuer

    def test_grade_object_set_with_correct_score(self):
        conn = self._make_conn(
            (True, "https://canvas.example/ags", "https://canvas.example")
        )
        mock_tool_conf = MagicMock()
        mock_ags = MagicMock()
        grade_calls = []

        class FakeGrade:
            def set_score_given(self, v):
                grade_calls.append(v)
                return self
            def set_score_maximum(self, v): return self
            def set_timestamp(self, v): return self
            def set_activity_progress(self, v): return self
            def set_grading_progress(self, v): return self
            def set_user_id(self, v): return self

        with patch("blueprints.lti._build_tool_conf", return_value=mock_tool_conf), \
             patch("pylti1p3.assignments_grades.AssignmentsGradesService",
                   return_value=mock_ags), \
             patch("pylti1p3.grade.Grade", FakeGrade), \
             patch("pylti1p3.lineitem.LineItem"):
            from blueprints.lti import _push_ags_grade
            _push_ags_grade(conn, "class-1", "ex-1", "lti-user-1", 88)

        assert grade_calls == [88]

    def test_line_item_tag_uses_exercise_id(self):
        conn = self._make_conn(
            (True, "https://canvas.example/ags", "https://canvas.example")
        )
        mock_tool_conf = MagicMock()
        mock_ags = MagicMock()
        tag_calls = []

        class FakeLineItem:
            def set_tag(self, v):
                tag_calls.append(v)
                return self
            def set_score_maximum(self, v): return self

        with patch("blueprints.lti._build_tool_conf", return_value=mock_tool_conf), \
             patch("pylti1p3.assignments_grades.AssignmentsGradesService",
                   return_value=mock_ags), \
             patch("pylti1p3.grade.Grade"), \
             patch("pylti1p3.lineitem.LineItem", FakeLineItem):
            from blueprints.lti import _push_ags_grade
            _push_ags_grade(conn, "class-1", "ex-99", "lti-user-1", 70)

        assert tag_calls == ["exercise-ex-99"]


# ---------------------------------------------------------------------------
# 2.  Grade endpoint + AGS integration tests
# ---------------------------------------------------------------------------


class TestGradeEndpointAgsPassback:
    """
    Tests that POST /api/exercises/<id>/grade triggers (or skips) AGS passback.
    _push_ags_grade is patched at blueprints.lti so we can assert call/no-call
    without needing a real LMS.
    """

    def _post_grade(self, client, exercise_id="ex-1",
                    code="def solution(a, b): return a + b"):
        return client.post(
            f"/api/exercises/{exercise_id}/grade",
            headers=AUTH_STUDENT,
            json={"code": code},
        )

    def _mock_ai(self, monkeypatch, grade=None):
        """Patch run_code and grade_with_ai so tests don't hit real Gemini."""
        monkeypatch.setattr("blueprints.exercises.run_code",
                            lambda *a, **kw: RUN_CODE_RESULT)
        monkeypatch.setattr("blueprints.exercises.grade_with_ai",
                            lambda **kw: (grade or GRADE_RESULT))

    def test_ags_called_when_student_has_lti_sub(self, client, mock_db, monkeypatch):
        """When student.lti_sub is set and class is LTI-linked, passback fires."""
        mock_db.cursor().fetchone.side_effect = _fetchone_seq(lti_sub=("lti-sub-abc",))
        self._mock_ai(monkeypatch)

        with patch("blueprints.lti._push_ags_grade") as mock_passback:
            resp = self._post_grade(client)

        assert resp.status_code == 200
        mock_passback.assert_called_once()

    def test_ags_called_with_correct_score(self, client, mock_db, monkeypatch):
        """Passback receives the total_score from the AI grader."""
        mock_db.cursor().fetchone.side_effect = _fetchone_seq(lti_sub=("lti-sub-abc",))
        self._mock_ai(monkeypatch, grade={**GRADE_RESULT, "total_score": 95})

        captured = {}

        def spy_passback(conn, class_id, exercise_id, lti_user_id, score, **kw):
            captured["score"] = score

        with patch("blueprints.lti._push_ags_grade", side_effect=spy_passback):
            self._post_grade(client)

        assert captured["score"] == 95

    def test_ags_called_with_correct_lti_user_id(self, client, mock_db, monkeypatch):
        """Passback uses the student's lti_sub, not internal user_id."""
        mock_db.cursor().fetchone.side_effect = _fetchone_seq(lti_sub=("canvas-sub-xyz",))
        self._mock_ai(monkeypatch)

        captured = {}

        def spy_passback(conn, class_id, exercise_id, lti_user_id, score, **kw):
            captured["lti_user_id"] = lti_user_id

        with patch("blueprints.lti._push_ags_grade", side_effect=spy_passback):
            self._post_grade(client)

        assert captured["lti_user_id"] == "canvas-sub-xyz"

    def test_ags_not_called_when_student_has_no_lti_sub(self, client, mock_db, monkeypatch):
        """Students without an LTI identity (non-LTI enrolment) skip passback."""
        mock_db.cursor().fetchone.side_effect = _fetchone_seq(lti_sub=(None,))
        self._mock_ai(monkeypatch)

        with patch("blueprints.lti._push_ags_grade") as mock_passback:
            resp = self._post_grade(client)

        assert resp.status_code == 200
        mock_passback.assert_not_called()

    def test_grade_still_returns_200_when_passback_raises(self, client, mock_db, monkeypatch):
        """AGS failures must never block the student from seeing their grade."""
        mock_db.cursor().fetchone.side_effect = _fetchone_seq(lti_sub=("lti-sub-abc",))
        self._mock_ai(monkeypatch)

        def exploding_passback(*args, **kw):
            raise ConnectionError("LMS is down")

        with patch("blueprints.lti._push_ags_grade", side_effect=exploding_passback):
            resp = self._post_grade(client)

        assert resp.status_code == 200
        assert resp.get_json()["total_score"] == GRADE_RESULT["total_score"]

    def test_grade_response_has_ai_feedback(self, client, mock_db, monkeypatch):
        """Response now contains AI feedback instead of has_test_cases flag."""
        mock_db.cursor().fetchone.side_effect = _fetchone_seq(lti_sub=("lti-sub-abc",))
        self._mock_ai(monkeypatch)

        with patch("blueprints.lti._push_ags_grade"):
            resp = self._post_grade(client)

        data = resp.get_json()
        assert "feedback" in data
        assert data.get("graded_by") == "ai"

    def test_ags_not_called_when_no_class_id(self, client, mock_db, monkeypatch):
        """Exercises not linked to a class have no class_id → no passback attempt."""
        mock_db.cursor().fetchone.side_effect = [
            EXERCISE_ROW,      # get_exercise_detail
            TEST_CASES_ROW,    # get_exercise_test_cases (language)
            None,               # get_exercise_location returns None → class_id_for_flywheel = None
            None,               # get_generation_event_by_exercise
            (0,),               # get_outcome_count_for_user_exercise
            ("evt-uuid",),      # insert_outcome_event
        ]
        self._mock_ai(monkeypatch)

        with patch("blueprints.lti._push_ags_grade") as mock_passback:
            resp = self._post_grade(client)

        assert resp.status_code == 200
        mock_passback.assert_not_called()
