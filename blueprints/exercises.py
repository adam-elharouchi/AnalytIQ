"""
Exercises Blueprint — /api/exercises/* and /api/leaderboard/grand
"""
import logging
import time
import unicodedata
from flask import Blueprint, g, jsonify, request
import core.cache as cache
import config
from core.audit import audit
from core.auth import require_auth, validate_fields
from core.database import get_db_connection
from core.extensions import csrf_exempt
from repositories import exercise_repository as exercise_repo
from repositories import flywheel_repository as flywheel_repo
from services.ai_grader import grade_with_ai
from services.code_runner import run_code

logger = logging.getLogger(__name__)
bp = Blueprint("exercises", __name__)

# ---------------------------------------------------------------------------
# Unicode sanitisation for student code submissions
# ---------------------------------------------------------------------------
# Browsers inside LTI iframes (e.g. Moodle) can silently inject invisible
# Unicode characters into textarea content — zero-width spaces (U+200B), BOM
# (U+FEFF), soft hyphens (U+00AD), etc.  These are Unicode "format" category
# (Cf) chars that survive a plain .strip() but cause "SyntaxError: invalid
# syntax (<student>, line 1)" when Python's tokeniser encounters them.
# Non-breaking-space variants are normalised to regular spaces so that Python
# indentation is not destroyed.

_NBSP_CHARS = frozenset("\u00a0\u2002\u2003\u2009\u202f")

# Curly/smart quotes → straight ASCII equivalents.
# These are Unicode Pi/Pf punctuation (not Cf), so they survive the format-char
# stripper below but cause "SyntaxError: invalid syntax (<student>, line 1)".
# They appear in code copy-pasted from the AI chat, rich-text editors, or Word.
_CURLY_QUOTE_MAP = {
    "\u2018": "'",  # LEFT SINGLE QUOTATION MARK  '
    "\u2019": "'",  # RIGHT SINGLE QUOTATION MARK '
    "\u201c": '"',  # LEFT DOUBLE QUOTATION MARK  "
    "\u201d": '"',  # RIGHT DOUBLE QUOTATION MARK "
    "\u201a": "'",  # SINGLE LOW-9 QUOTATION MARK ‚
    "\u201e": '"',  # DOUBLE LOW-9 QUOTATION MARK „
    "\u2032": "'",  # PRIME                        ′
    "\u2033": '"',  # DOUBLE PRIME                 ″
    "\u00ab": '"',  # LEFT-POINTING DOUBLE ANGLE QUOTATION MARK «
    "\u00bb": '"',  # RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK »
}


def _sanitise_student_code(code: str) -> str:
    """Strip invisible Unicode format chars; normalise non-breaking spaces and curly quotes."""
    out = []
    for ch in code:
        if ch in _NBSP_CHARS:
            out.append(" ")
        elif ch in _CURLY_QUOTE_MAP:
            out.append(_CURLY_QUOTE_MAP[ch])
        elif unicodedata.category(ch) == "Cf":  # format chars: U+200B, U+FEFF, …
            pass  # drop silently
        else:
            out.append(ch)
    return "".join(out).strip()


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
        cache.invalidate_cache(f"chap_exercises:*:chapter_id={chapter_id}")
        return jsonify({"success": True}), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/exercises/<exercise_id>/grade", methods=["POST"])
@csrf_exempt
@require_auth
def grade_exercise(exercise_id):
    """
    Grade a student's code submission using AI.

    Runs the code in a sandbox, captures stdout/stderr, then asks Gemini to
    evaluate whether the logic and output fulfil the exercise description.
    Grading is style-agnostic — any correct approach scores equally.

    Body:    { "code": "<student source code>" }
    Returns: {
      "total_score":       int,   // 0-100
      "correctness_score": int,   // 0-70
      "quality_score":     int,   // 0-30
      "feedback":          str,   // AI feedback (2-3 sentences)
      "output":            str,   // stdout produced by the code
      "passed":            bool,
      "graded_by":         "ai"
    }
    """
    try:
        conn = get_db_connection()
        data = request.json or {}

        student_code = _sanitise_student_code(data.get("code") or "")
        if not student_code:
            return jsonify({"error": "No code submitted."}), 400

        # Fetch exercise title, description, language from DB
        row = exercise_repo.get_exercise_detail(conn, exercise_id)
        if not row:
            return jsonify({"error": "Exercise not found."}), 404
        # row: (exercise_id, chapter_id, class_id, title, description, difficulty, solution_code)
        _, _, _, title, description, _, _ = row

        # Language is stored in the test_cases row; default to Python
        _, language, _ = exercise_repo.get_exercise_test_cases(conn, exercise_id)
        language = language or "Python"

        # ── Step 1: Run the code in a sandbox, capture output ─────────────────
        _run_t0 = time.monotonic()
        run_result = run_code(student_code, language=language, timeout=10)
        execution_time_ms = int((time.monotonic() - _run_t0) * 1000)

        stdout = run_result.get("stdout", "")
        stderr = run_result.get("stderr", "")
        timed_out = run_result.get("timed_out", False)

        if timed_out:
            actual_output = "[Code timed out after 10 seconds — possible infinite loop]"
        elif stderr and not stdout:
            actual_output = stderr
        elif stderr:
            actual_output = f"{stdout}\n{stderr}".strip()
        else:
            actual_output = stdout

        # ── Step 2: AI grades the code + output against the description ───────
        result = grade_with_ai(
            title=title,
            description=description,
            language=language,
            student_code=student_code,
            actual_output=actual_output,
            api_key=config.GEMINI_API_KEY,
        )

        audit(
            conn,
            "GRADE_EXERCISE",
            resource_type="exercise",
            resource_id=exercise_id,
            details={"score": result["total_score"], "language": language, "graded_by": "ai"},
        )

        # ── Flywheel: record outcome event (must never break grading) ─────────
        class_id_for_flywheel = None
        try:
            user_id = g.user_id
            tenant_id = getattr(g, "tenant_id", None)

            ex_location = exercise_repo.get_exercise_location(conn, exercise_id)
            class_id_for_flywheel = ex_location[1] if ex_location else None

            gen_event = flywheel_repo.get_generation_event_by_exercise(conn, exercise_id)
            generation_event_id = gen_event["id"] if gen_event else None

            attempt_number = (
                flywheel_repo.get_outcome_count_for_user_exercise(conn, user_id, exercise_id) + 1
            )

            flywheel_repo.insert_outcome_event(
                conn,
                {
                    "exercise_id": exercise_id,
                    "generation_event_id": generation_event_id,
                    "user_id": user_id,
                    "class_id": class_id_for_flywheel,
                    "tenant_id": str(tenant_id) if tenant_id else None,
                    "attempt_number": attempt_number,
                    "time_spent_seconds": int(data["time_spent"]) if data.get("time_spent") else None,
                    "hints_requested": 0,
                    "ai_chat_messages": 0,
                    "code_char_count": len(student_code),
                    "passed": result["passed"],
                    "total_score": result["total_score"],
                    "correctness_score": result["correctness_score"],
                    "quality_score": result["quality_score"],
                    "tests_total": 0,
                    "tests_passed": 0,
                    "test_results": [{"description": result["feedback"], "passed": result["passed"]}],
                    "error_category": "none" if result["passed"] else "logic",
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

        # ── AGS grade passback ────────────────────────────────────────────────
        try:
            if class_id_for_flywheel:
                from blueprints.lti import _push_ags_grade

                cur = conn.cursor()
                cur.execute("SELECT lti_sub FROM users WHERE user_id = %s", (g.user_id,))
                lti_row = cur.fetchone()
                cur.close()
                lti_user_id = lti_row[0] if lti_row and lti_row[0] else None
                if lti_user_id:
                    _push_ags_grade(
                        conn, class_id_for_flywheel, exercise_id,
                        lti_user_id, result["total_score"],
                    )
                    logger.info(
                        "AGS grade pushed: exercise=%s class=%s score=%s",
                        exercise_id, class_id_for_flywheel, result["total_score"],
                    )
        except Exception as ags_err:
            logger.warning("AGS passback skipped for %s: %s", exercise_id, ags_err)

        return jsonify({
            **result,
            "output": stdout,
            "timed_out": timed_out,
        }), 200

    except Exception as e:
        logger.error("Unexpected error grading exercise %s: %s", exercise_id, e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/code/run", methods=["POST"])
@csrf_exempt
@require_auth
def run_code_endpoint():
    """
    Execute code in a live sandbox and return stdout/stderr — no grading.
    Network access is allowed so pd.read_csv(url) and similar work.

    Body:  { "code": "...", "language": "python" }
    Returns: { "stdout": "...", "stderr": "...", "timed_out": bool }
    """
    data = request.get_json(silent=True) or {}
    code = _sanitise_student_code(data.get("code") or "")
    language = data.get("language", "python")

    if not code:
        return jsonify({"stdout": "", "stderr": "No code provided.", "timed_out": False}), 400

    result = run_code(code, language=language)
    return jsonify(result), 200
