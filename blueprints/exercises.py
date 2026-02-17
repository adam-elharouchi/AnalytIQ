"""
Exercises Blueprint — /api/exercises/* and /api/leaderboard/grand
"""
import logging
from datetime import datetime
from flask import Blueprint, g, jsonify, request
import config
from auth_helpers import require_auth, validate_fields
from db import close_conn_safely, get_db_connection
from extensions import csrf_exempt

logger = logging.getLogger(__name__)
bp = Blueprint("exercises", __name__)


def ensure_exercises_table():
    """Ensure class_exercises table has all required columns (Lazy Migration)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check for solution_code column
        try:
            cursor.execute("SELECT solution_code FROM class_exercises LIMIT 1")
        except Exception:
            conn.rollback()
            print("Adding missing solution_code column to class_exercises")
            cursor.execute("ALTER TABLE class_exercises ADD COLUMN solution_code TEXT")

        # Check for exercise_number column
        try:
            cursor.execute("SELECT exercise_number FROM class_exercises LIMIT 1")
        except Exception:
            conn.rollback()
            print("Adding missing exercise_number column to class_exercises")
            cursor.execute(
                "ALTER TABLE class_exercises ADD COLUMN exercise_number INTEGER DEFAULT 1"
            )

        # Check for created_by column (Fix for 500 error on Create Exercise)
        try:
            cursor.execute("SELECT created_by FROM class_exercises LIMIT 1")
        except Exception:
            conn.rollback()
            print("Adding missing created_by column to class_exercises")
            cursor.execute("ALTER TABLE class_exercises ADD COLUMN created_by VARCHAR(255)")

        conn.commit()
        cursor.close()
        close_conn_safely(conn)
    except Exception as e:
        print(f"Error checking exercises table: {e}")


@bp.route("/api/exercises/progress", methods=["GET"])
@require_auth
def get_all_progress():
    """Get progress for all exercises for current user"""
    try:
        user_id = g.user_id

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT exercise_id, exercise_title, best_score, best_accuracy,
                   total_attempts, completed, last_completed_at
            FROM practice_progress
            WHERE user_id = %s
            ORDER BY exercise_id
        """,
            (user_id,),
        )

        results = cursor.fetchall()
        progress = []
        for row in results:
            progress.append(
                {
                    "exercise_id": row[0],
                    "exercise_title": row[1],
                    "best_score": row[2] or 0,
                    "best_accuracy": float(row[3]) if row[3] else 0,
                    "total_attempts": row[4] or 0,
                    "completed": row[5] or False,
                    "last_completed_at": row[6].isoformat() if row[6] else None,
                }
            )

        cursor.close()
        close_conn_safely(conn)

        return jsonify({"progress": progress}), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/exercises/<exercise_id>/leaderboard", methods=["GET"])
def get_exercise_leaderboard(exercise_id):
    """Get leaderboard for a specific exercise"""
    try:
        limit = int(request.args.get("limit", 10))

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT u.name, u.email, pp.best_score, pp.best_accuracy,
                   pp.best_time, pp.total_attempts, pp.last_completed_at
            FROM practice_progress pp
            JOIN users u ON pp.user_id = u.user_id
            WHERE pp.exercise_id = %s AND pp.best_score > 0
            ORDER BY pp.best_score DESC, pp.best_time ASC
            LIMIT %s
        """,
            (exercise_id, limit),
        )

        results = cursor.fetchall()
        leaderboard = []
        rank = 1
        for row in results:
            leaderboard.append(
                {
                    "rank": rank,
                    "name": row[0],
                    "email": row[1],
                    "best_score": row[2],
                    "best_accuracy": float(row[3]) if row[3] else 0,
                    "best_time": row[4],
                    "total_attempts": row[5] or 0,
                }
            )
            rank += 1

        cursor.close()
        close_conn_safely(conn)

        return jsonify({"leaderboard": leaderboard}), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/leaderboard/grand", methods=["GET"])
def get_grand_leaderboard():
    """Get grand leaderboard - ranked by average score across all exercises"""
    try:
        limit = int(request.args.get("limit", 10))

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT u.user_id, u.name, u.email,
                   COUNT(DISTINCT pp.exercise_id) as exercises_completed,
                   AVG(pp.best_score) as average_score,
                   SUM(pp.best_score) as total_score,
                   MAX(pp.last_completed_at) as last_activity
            FROM users u
            JOIN practice_progress pp ON u.user_id = pp.user_id
            WHERE pp.completed = true AND pp.best_score >= 50
            GROUP BY u.user_id, u.name, u.email
            HAVING COUNT(DISTINCT pp.exercise_id) > 0
            ORDER BY average_score DESC, exercises_completed DESC
            LIMIT %s
        """,
            (limit,),
        )

        results = cursor.fetchall()
        leaderboard = []
        rank = 1
        for row in results:
            leaderboard.append(
                {
                    "rank": rank,
                    "user_id": row[0],
                    "name": row[1],
                    "email": row[2],
                    "exercises_completed": row[3],
                    "average_score": float(row[4]) if row[4] else 0,
                    "total_score": int(row[5]) if row[5] else 0,
                }
            )
            rank += 1

        cursor.close()
        close_conn_safely(conn)

        return jsonify({"leaderboard": leaderboard}), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/exercises/<exercise_id>", methods=["GET"])
@require_auth
def get_exercise_details(exercise_id):
    """Get details of a single exercise"""
    try:
        user_id = g.user_id
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT exercise_id, chapter_id, class_id, title, description, difficulty, solution_code
            FROM class_exercises
            WHERE exercise_id = %s
        """,
            (exercise_id,),
        )

        row = cursor.fetchone()
        cursor.close()
        close_conn_safely(conn)

        if not row:
            return jsonify({"error": "Exercise not found"}), 404

        return (
            jsonify(
                {
                    "exercise": {
                        "exercise_id": row[0],
                        "chapter_id": row[1],
                        "class_id": row[2],
                        "title": row[3],
                        "description": row[4],
                        "difficulty": row[5],
                        "solution_code": row[6],
                    }
                }
            ),
            200,
        )

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/exercises/<exercise_id>", methods=["PUT"])
@csrf_exempt
@require_auth
def update_exercise(exercise_id):
    """Update an existing exercise"""
    try:
        ensure_exercises_table()
        data = request.json or {}
        user_id = g.user_id

        errors = validate_fields(data, [
            ("title", False, config.MAX_EXERCISE_TITLE_LENGTH),
            ("description", False, config.MAX_EXERCISE_DESCRIPTION_LENGTH),
            ("solution_code", False, config.MAX_SOLUTION_CODE_LENGTH),
        ])
        if errors:
            return jsonify({"error": errors[0]}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Verify ownership (simplified check)
        cursor.execute(
            """
            SELECT c.professor_id
            FROM class_exercises ce
            JOIN classes c ON ce.class_id = c.class_id
            WHERE ce.exercise_id = %s
        """,
            (exercise_id,),
        )

        result = cursor.fetchone()
        if not result or result[0] != user_id:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Not authorized"}), 403

        cursor.execute(
            """
            UPDATE class_exercises
            SET title = %s, description = %s, difficulty = %s, solution_code = %s
            WHERE exercise_id = %s
        """,
            (
                data.get("title"),
                data.get("description"),
                data.get("difficulty"),
                data.get("solution_code"),
                exercise_id,
            ),
        )

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/exercises/<exercise_id>", methods=["DELETE"])
@csrf_exempt
@require_auth
def delete_exercise(exercise_id):
    """Delete a specific exercise"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Verify exercise exists
        cursor.execute(
            "SELECT chapter_id, class_id FROM class_exercises WHERE exercise_id = %s",
            (exercise_id,),
        )
        result = cursor.fetchone()

        if not result:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Exercise not found"}), 404

        # Delete the exercise
        cursor.execute("DELETE FROM class_exercises WHERE exercise_id = %s", (exercise_id,))
        conn.commit()

        cursor.close()
        close_conn_safely(conn)

        return jsonify({"success": True}), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500
