"""
Exercise Repository — SQL operations for exercises, leaderboards, and progress lookups.

Every function receives a DB *connection* and returns plain Python data.
The caller (blueprint) is responsible for commit / rollback / connection lifecycle.
"""

import json
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exercise CRUD
# ---------------------------------------------------------------------------


def get_exercise_detail(conn, exercise_id):
    """Return single exercise row or None."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT exercise_id, chapter_id, class_id, title, description, difficulty, solution_code
        FROM class_exercises
        WHERE exercise_id = %s
        """,
        (exercise_id,),
    )
    row = cur.fetchone()
    cur.close()
    return row


def get_exercise_test_cases(conn, exercise_id):
    """
    Return (function_name, language, test_cases) for the given exercise,
    or (None, None, None) when the exercise does not exist.

    test_cases is a list of dicts:
      [{description, input, expected_output, weight}, ...]
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT function_name, language, test_cases FROM class_exercises WHERE exercise_id = %s",
        (exercise_id,),
    )
    row = cur.fetchone()
    cur.close()
    if not row:
        return None, None, None
    function_name, language, test_cases_raw = row
    # psycopg2 returns JSONB as a Python object already; guard against string
    if isinstance(test_cases_raw, str):
        try:
            test_cases_raw = json.loads(test_cases_raw)
        except (json.JSONDecodeError, TypeError):
            test_cases_raw = None
    return function_name or "solution", language or "Python", test_cases_raw or []


def save_exercise_test_cases(conn, exercise_id, function_name, test_cases):
    """Persist function_name and test_cases for an existing exercise."""
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE class_exercises
        SET function_name = %s,
            test_cases    = %s
        WHERE exercise_id = %s
        """,
        (function_name, json.dumps(test_cases), exercise_id),
    )
    cur.close()


def get_exercise_owner(conn, exercise_id):
    """Return professor_id for the class that owns this exercise, or None."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT c.professor_id
        FROM class_exercises ce
        JOIN classes c ON ce.class_id = c.class_id
        WHERE ce.exercise_id = %s
        """,
        (exercise_id,),
    )
    row = cur.fetchone()
    cur.close()
    return row[0] if row else None


def update_exercise(conn, exercise_id, title, description, difficulty, solution_code):
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE class_exercises
        SET title = %s, description = %s, difficulty = %s, solution_code = %s
        WHERE exercise_id = %s
        """,
        (title, description, difficulty, solution_code, exercise_id),
    )
    cur.close()


def get_exercise_location(conn, exercise_id):
    """Return (chapter_id, class_id) or None."""
    cur = conn.cursor()
    cur.execute(
        "SELECT chapter_id, class_id FROM class_exercises WHERE exercise_id = %s",
        (exercise_id,),
    )
    row = cur.fetchone()
    cur.close()
    return row


def delete_exercise(conn, exercise_id):
    cur = conn.cursor()
    cur.execute("DELETE FROM class_exercises WHERE exercise_id = %s", (exercise_id,))
    cur.close()


# ---------------------------------------------------------------------------
# Progress
# ---------------------------------------------------------------------------


def get_all_user_progress(conn, user_id):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT exercise_id, exercise_title, best_score, best_accuracy,
               total_attempts, completed, last_completed_at
        FROM practice_progress
        WHERE user_id = %s
        ORDER BY exercise_id
        """,
        (user_id,),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


# ---------------------------------------------------------------------------
# Leaderboards
# ---------------------------------------------------------------------------


def get_exercise_leaderboard(conn, exercise_id, limit):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT u.name, pp.best_score, pp.best_accuracy,
               pp.best_time, pp.total_attempts, pp.last_completed_at
        FROM practice_progress pp
        JOIN users u ON pp.user_id = u.user_id
        WHERE pp.exercise_id = %s AND pp.best_score > 0
        ORDER BY pp.best_score DESC, pp.best_time ASC
        LIMIT %s
        """,
        (exercise_id, limit),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def get_grand_leaderboard(conn, limit):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT u.user_id, u.name,
               COUNT(DISTINCT pp.exercise_id) AS exercises_completed,
               AVG(pp.best_score)             AS average_score,
               SUM(pp.best_score)             AS total_score,
               MAX(pp.last_completed_at)      AS last_activity
        FROM users u
        JOIN practice_progress pp ON u.user_id = pp.user_id
        WHERE pp.completed = true AND pp.best_score >= 50
        GROUP BY u.user_id, u.name
        HAVING COUNT(DISTINCT pp.exercise_id) > 0
        ORDER BY average_score DESC, exercises_completed DESC
        LIMIT %s
        """,
        (limit,),
    )
    rows = cur.fetchall()
    cur.close()
    return rows
