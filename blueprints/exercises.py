"""
Exercises Blueprint — /api/exercises/* and /api/leaderboard/grand
"""
import logging
from flask import Blueprint, g, jsonify, request
import cache
import config
from audit import audit
from auth_helpers import require_auth, validate_fields
from db import get_db_connection
from extensions import csrf_exempt
from repositories import exercise_repository as exercise_repo

logger = logging.getLogger(__name__)
bp = Blueprint("exercises", __name__)


@bp.route("/api/exercises/progress", methods=["GET"])
@require_auth
def get_all_progress():
    """Get progress for all exercises for current user"""
    try:
        user_id = g.user_id
        conn = get_db_connection()

        rows = exercise_repo.get_all_user_progress(conn, user_id)

        progress = [
            {
                "exercise_id": row[0],
                "exercise_title": row[1],
                "best_score": row[2] or 0,
                "best_accuracy": float(row[3]) if row[3] else 0,
                "total_attempts": row[4] or 0,
                "completed": row[5] or False,
                "last_completed_at": row[6].isoformat() if row[6] else None,
            }
            for row in rows
        ]

        return jsonify({"progress": progress}), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/exercises/<exercise_id>/leaderboard", methods=["GET"])
@require_auth
def get_exercise_leaderboard(exercise_id):
    """Get leaderboard for a specific exercise"""
    try:
        limit = min(int(request.args.get("limit", 10)), config.MAX_PAGE_SIZE)
        conn = get_db_connection()

        rows = exercise_repo.get_exercise_leaderboard(conn, exercise_id, limit)

        leaderboard = [
            {
                "rank": rank,
                "name": row[0],
                "best_score": row[1],
                "best_accuracy": float(row[2]) if row[2] else 0,
                "best_time": row[3],
                "total_attempts": row[4] or 0,
            }
            for rank, row in enumerate(rows, 1)
        ]

        return jsonify({"leaderboard": leaderboard}), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/leaderboard/grand", methods=["GET"])
@require_auth
def get_grand_leaderboard():
    """Get grand leaderboard - ranked by average score across all exercises"""
    try:
        limit = min(int(request.args.get("limit", 10)), config.MAX_PAGE_SIZE)
        conn = get_db_connection()

        rows = exercise_repo.get_grand_leaderboard(conn, limit)

        leaderboard = [
            {
                "rank": rank,
                "user_id": row[0],
                "name": row[1],
                "exercises_completed": row[2],
                "average_score": float(row[3]) if row[3] else 0,
                "total_score": int(row[4]) if row[4] else 0,
            }
            for rank, row in enumerate(rows, 1)
        ]

        return jsonify({"leaderboard": leaderboard}), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/exercises/<exercise_id>", methods=["GET"])
@require_auth
@cache.cache_response(ttl=120, key_prefix="exercise")
def get_exercise_details(exercise_id):
    """Get details of a single exercise"""
    try:
        conn = get_db_connection()
        row = exercise_repo.get_exercise_detail(conn, exercise_id)

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
        conn = get_db_connection()
        data = request.json or {}
        user_id = g.user_id

        errors = validate_fields(
            data,
            [
                ("title", False, config.MAX_EXERCISE_TITLE_LENGTH),
                ("description", False, config.MAX_EXERCISE_DESCRIPTION_LENGTH),
                ("solution_code", False, config.MAX_SOLUTION_CODE_LENGTH),
            ],
        )
        if errors:
            return jsonify({"error": errors[0]}), 400

        owner = exercise_repo.get_exercise_owner(conn, exercise_id)
        if owner is None or owner != user_id:
            return jsonify({"error": "Not authorized"}), 403

        exercise_repo.update_exercise(
            conn,
            exercise_id,
            data.get("title"),
            data.get("description"),
            data.get("difficulty"),
            data.get("solution_code"),
        )
        conn.commit()

        cache.invalidate_cache(f"exercise:*:{exercise_id}")
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

        location = exercise_repo.get_exercise_location(conn, exercise_id)
        if not location:
            return jsonify({"error": "Exercise not found"}), 404

        chapter_id = location[0]
        exercise_repo.delete_exercise(conn, exercise_id)
        audit(
            conn,
            "DELETE_EXERCISE",
            resource_type="exercise",
            resource_id=exercise_id,
            details={"chapter_id": chapter_id},
        )
        conn.commit()

        cache.invalidate_cache(f"exercise:*:{exercise_id}")
        cache.invalidate_cache(f"chap_exercises:*:{chapter_id}")
        return jsonify({"success": True}), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500
