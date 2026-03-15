"""
Flywheel Blueprint — /api/flywheel/* and /api/exercises/<id>/quality and /api/classes/<id>/exercise-quality

Exposes data flywheel instrumentation metrics to professors and superadmins.
"""

import logging
import os

from flask import Blueprint, g, jsonify, request

from core.auth import require_auth, require_role, require_super_admin
from core.database import get_db_connection
from repositories import exercise_repository as exercise_repo
from repositories import flywheel_repository as flywheel_repo

logger = logging.getLogger(__name__)
bp = Blueprint("flywheel", __name__)


# ---------------------------------------------------------------------------
# Professor-facing endpoints
# ---------------------------------------------------------------------------


@bp.route("/api/exercises/<exercise_id>/quality", methods=["GET"])
@require_auth
def get_exercise_quality(exercise_id):
    """
    Return the pre-computed quality score for a single exercise.

    Access: The professor who owns the exercise's class, or superadmin.
    Returns 404 if quality has not yet been computed (needs >= 5 outcome events).
    """
    try:
        conn = get_db_connection()
        user_id = g.user_id
        user_role = getattr(g, "user_role", "student")

        # Authorization: professor must own the exercise's class
        if user_role != "superadmin":
            owner = exercise_repo.get_exercise_owner(conn, exercise_id)
            if owner is None:
                return jsonify({"error": "Exercise not found"}), 404
            if owner != user_id:
                return jsonify({"error": "Forbidden"}), 403

        quality = flywheel_repo.get_quality_score(conn, exercise_id)
        if quality is None:
            return (
                jsonify(
                    {
                        "error": "Quality score not yet computed. "
                        "Exercise needs at least 5 grading outcomes."
                    }
                ),
                404,
            )

        return jsonify(quality), 200

    except Exception as e:
        logger.error("Unexpected error in get_exercise_quality: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/classes/<class_id>/exercise-quality", methods=["GET"])
@require_auth
@require_role("professor", "superadmin")
def get_class_exercise_quality(class_id):
    """
    Return quality scores for all exercises in a class, sorted worst-first.

    Access: Professor who owns the class, or superadmin.
    Exercises with no quality score yet are excluded.
    """
    try:
        conn = get_db_connection()
        user_id = g.user_id
        user_role = getattr(g, "user_role", "student")

        if user_role != "superadmin":
            from repositories import class_repository as class_repo
            owner = class_repo.get_class_owner(conn, class_id)
            if owner is None:
                return jsonify({"error": "Class not found"}), 404
            if owner != user_id:
                return jsonify({"error": "Forbidden"}), 403

        scores = flywheel_repo.get_class_quality_scores(conn, class_id)
        return jsonify({"class_id": class_id, "exercise_quality": scores}), 200

    except Exception as e:
        logger.error("Unexpected error in get_class_exercise_quality: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


# ---------------------------------------------------------------------------
# Superadmin-only endpoints
# ---------------------------------------------------------------------------


@bp.route("/api/flywheel/generation-effectiveness", methods=["GET"])
@require_auth
@require_super_admin
def get_generation_effectiveness():
    """
    Aggregate stats grouped by prompt_template_version, detected_language,
    source_content_type, and difficulty_generated.

    Shows which prompt versions / content types produce the highest quality exercises.
    """
    try:
        conn = get_db_connection()
        data = flywheel_repo.get_generation_effectiveness(conn)
        return jsonify(data), 200

    except Exception as e:
        logger.error("Unexpected error in get_generation_effectiveness: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/flywheel/health", methods=["GET"])
@require_auth
@require_super_admin
def get_flywheel_health():
    """
    Platform-level flywheel coverage and quality distribution stats.

    Returns:
        total_exercises, instrumented_exercises, coverage_pct,
        total_outcome_events, exercises_with_quality_scores,
        quality_distribution, top_problematic (5 lowest-quality exercises
        with >= 10 attempts).
    """
    try:
        conn = get_db_connection()
        data = flywheel_repo.get_flywheel_health(conn)
        return jsonify(data), 200

    except Exception as e:
        logger.error("Unexpected error in get_flywheel_health: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/flywheel/compute-quality", methods=["POST"])
@require_auth
@require_super_admin
def trigger_compute_quality():
    """
    Manually trigger quality score computation.

    Runs synchronously when FEATURE_ASYNC_TASKS=False (test/dev environment),
    otherwise dispatches to the Celery ai_tasks queue.

    Returns:
        {"status": "started", "task_id": "..."} or {"status": "completed", "exercises_scored": N}
    """
    try:
        import config as app_config

        if not app_config.FEATURE_ASYNC_TASKS:
            # Synchronous execution — useful in dev/test environments
            from workers.tasks import compute_exercise_quality_scores
            result = compute_exercise_quality_scores()
            return (
                jsonify(
                    {
                        "status": "completed",
                        "exercises_scored": result.get("exercises_scored", 0),
                    }
                ),
                200,
            )
        else:
            from workers.tasks import compute_exercise_quality_scores
            task = compute_exercise_quality_scores.apply_async(queue="ai_tasks")
            return jsonify({"status": "started", "task_id": task.id}), 202

    except Exception as e:
        logger.error("Unexpected error in trigger_compute_quality: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500
