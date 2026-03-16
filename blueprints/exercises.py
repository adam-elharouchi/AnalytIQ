"""
Exercises Blueprint — /api/exercises/* and /api/leaderboard/grand
"""
import logging
import time
from flask import Blueprint, g, jsonify, request
import core.cache as cache
import config
from core.audit import audit
from core.auth import require_auth, validate_fields
from core.database import get_db_connection
from core.extensions import csrf_exempt
from repositories import exercise_repository as exercise_repo
from repositories import flywheel_repository as flywheel_repo
from services.code_runner import run_test_cases
from services.exercise_generator import generate_test_cases_for_exercise

logger = logging.getLogger(__name__)
bp = Blueprint("exercises", __name__)

_PY_EXCEPTION_NAMES = (
    "SyntaxError",
    "NameError",
    "TypeError",
    "IndexError",
    "ValueError",
    "ZeroDivisionError",
    "ImportError",
    "ModuleNotFoundError",
    "TimeoutError",
    "AttributeError",
    "KeyError",
    "RuntimeError",
)


def _classify_error_category(results: list) -> str:
    """
    Derive the dominant error category from a list of per-test grading results.
    Returns a short label string or 'none' when all tests pass.
    """
    if all(r.get("passed") for r in results):
        return "none"

    failing = [r for r in results if not r.get("passed")]
    categories: list = []
    for r in failing:
        err = str(r.get("error") or "")
        if "timed out" in err.lower() or "timeout" in err.lower():
            categories.append("timeout")
        elif "memory" in err.lower():
            categories.append("memory")
        elif any(name in err for name in _PY_EXCEPTION_NAMES):
            # Find the first matching exception name
            for name in _PY_EXCEPTION_NAMES:
                if name in err:
                    categories.append(name.lower().replace("error", "_error"))
                    break
        elif r.get("actual") is not None or r.get("printed") is not None:
            # Test ran but output didn't match
            categories.append("logic_error")
        else:
            categories.append("runtime_error")

    if not categories:
        return "unknown"
    # Return the most common category
    return max(set(categories), key=categories.count)


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


@bp.route("/api/exercises/<exercise_id>/grade", methods=["POST"])
@csrf_exempt
@require_auth
def grade_exercise(exercise_id):
    """
    Grade a student's code submission against pre-generated test cases.

    Body:
      { "code": "<student source code>" }
      (language is read from the DB, not trusted from the client)

    Returns:
      {
        "total_score":       int,   // 0-100  ← store this as the submission score
        "correctness_score": int,   // 0-80
        "quality_score":     int,   // 0-20
        "tests_passed":      int,
        "tests_total":       int,
        "results":           [...], // per-test detail
        "quality_details":   {...},
        "has_test_cases":    bool   // false when exercise was generated before migration
      }

    Grading is purely output-based — no Levenshtein, no time bonus.
    The frontend should store total_score via PUT /api/users/practice-progress.
    """
    try:
        conn = get_db_connection()
        data = request.json or {}

        student_code = (data.get("code") or "").strip()
        if not student_code:
            return jsonify({"error": "No code submitted."}), 400

        # Retrieve test cases stored at generation time.
        # Language comes from the DB (set at generation time) — we do NOT trust
        # the client-supplied language to select the sandbox runner.
        function_name, language, test_cases = exercise_repo.get_exercise_test_cases(
            conn, exercise_id
        )

        if function_name is None:
            return jsonify({"error": "Exercise not found."}), 404

        # Exercise predates test-case generation — auto-generate now
        _retroactive_gen_meta = None
        if not test_cases:
            row = exercise_repo.get_exercise_detail(conn, exercise_id)
            if not row:
                return jsonify({"error": "Exercise not found."}), 404
            title, description, solution_code = row[3], row[4], row[6]
            try:
                generated = generate_test_cases_for_exercise(
                    title=title,
                    description=description,
                    solution_code=solution_code,
                    language=language,
                )
                function_name = generated["function_name"]
                test_cases = generated["test_cases"]
                _retroactive_gen_meta = generated.get("_gen_meta")
                exercise_repo.save_exercise_test_cases(conn, exercise_id, function_name, test_cases)
                conn.commit()
            except Exception as gen_err:
                logger.error("Auto test-case generation failed for %s: %s", exercise_id, gen_err)
                return (
                    jsonify(
                        {
                            "has_test_cases": False,
                            "total_score": 0,
                            "correctness_score": 0,
                            "quality_score": 0,
                            "tests_passed": 0,
                            "tests_total": 0,
                            "results": [],
                            "quality_details": {},
                            "message": "Could not generate test cases. Please try again.",
                        }
                    ),
                    200,
                )

        # Run the code against every test case in the sandbox
        _grade_t0 = time.monotonic()
        result = run_test_cases(
            student_code=student_code,
            language=language,
            function_name=function_name,
            test_cases=test_cases,
            timeout=5,
        )
        execution_time_ms = int((time.monotonic() - _grade_t0) * 1000)

        audit(
            conn,
            "GRADE_EXERCISE",
            resource_type="exercise",
            resource_id=exercise_id,
            details={
                "score": result["total_score"],
                "tests_passed": result["tests_passed"],
                "tests_total": result["tests_total"],
                "language": language,
            },
        )

        # --- Flywheel: record outcome event (must never break grading) -------
        try:
            user_id = g.user_id
            tenant_id = getattr(g, "tenant_id", None)

            # Look up class_id and generation_event_id from the exercise row
            ex_location = exercise_repo.get_exercise_location(conn, exercise_id)
            class_id_for_flywheel = ex_location[1] if ex_location else None

            # If this was a retroactive test-case generation, record that first
            if _retroactive_gen_meta:
                retro_event_id = flywheel_repo.insert_generation_event(
                    conn,
                    {
                        **_retroactive_gen_meta,
                        "exercise_id": exercise_id,
                        "class_id": class_id_for_flywheel,
                        "tenant_id": str(tenant_id) if tenant_id else None,
                    },
                )
                if retro_event_id:
                    flywheel_repo.update_exercise_generation_event_id(
                        conn, exercise_id, retro_event_id
                    )
                    conn.commit()

            # Look up the generation_event_id that was set at exercise creation
            gen_event = flywheel_repo.get_generation_event_by_exercise(conn, exercise_id)
            generation_event_id = gen_event["id"] if gen_event else None

            attempt_number = (
                flywheel_repo.get_outcome_count_for_user_exercise(conn, user_id, exercise_id) + 1
            )

            # Truncate per-test stderr to 200 chars to keep the JSONB payload small
            sanitised_results = []
            for r in result.get("results", []):
                sr = {k: v for k, v in r.items()}
                if isinstance(sr.get("error"), str) and len(sr["error"]) > 200:
                    sr["error"] = sr["error"][:200]
                sanitised_results.append(sr)

            # TODO: wire frontend timer to send time_spent in grade request
            time_spent_seconds = data.get("time_spent")

            # TODO: count AI interactions per exercise session once
            #       conversation-exercise linking exists
            flywheel_repo.insert_outcome_event(
                conn,
                {
                    "exercise_id": exercise_id,
                    "generation_event_id": generation_event_id,
                    "user_id": user_id,
                    "class_id": class_id_for_flywheel,
                    "tenant_id": str(tenant_id) if tenant_id else None,
                    "attempt_number": attempt_number,
                    "time_spent_seconds": int(time_spent_seconds) if time_spent_seconds else None,
                    "hints_requested": 0,
                    "ai_chat_messages": 0,
                    "code_char_count": len(student_code),
                    "passed": result["total_score"] >= 50,
                    "total_score": result["total_score"],
                    "correctness_score": result["correctness_score"],
                    "quality_score": result["quality_score"],
                    "tests_total": result["tests_total"],
                    "tests_passed": result["tests_passed"],
                    "test_results": sanitised_results,
                    "error_category": _classify_error_category(result.get("results", [])),
                    "execution_time_ms": execution_time_ms,
                },
            )
            conn.commit()
        except Exception as flywheel_err:
            logger.error(
                "flywheel: outcome event recording failed for %s: %s",
                exercise_id,
                flywheel_err,
                exc_info=True,
            )
            # Intentional: do not re-raise — student must always get their grade

        return jsonify({**result, "has_test_cases": True}), 200

    except Exception as e:
        logger.error("Unexpected error grading exercise %s: %s", exercise_id, e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500
