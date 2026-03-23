"""
Celery Tasks for AnalytIQ
Async tasks for PDF processing, exercise generation, and email sending.
"""

import json
import logging
import uuid

import config
from celery import Task
from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Base task with database connection
# ---------------------------------------------------------------------------


class DatabaseTask(Task):
    """Base task providing a per-worker psycopg2 connection pool."""

    _db_pool = None
    _db_conn = None

    def get_db_connection(self):
        """Return a database connection, initialising the pool on first call."""
        if self._db_conn is None:
            import psycopg2
            import psycopg2.pool
            import os

            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                raise ValueError("DATABASE_URL environment variable not set")

            self._db_pool = psycopg2.pool.SimpleConnectionPool(
                1, 10, database_url, connect_timeout=10
            )
            self._db_conn = self._db_pool.getconn()

        return self._db_conn

    def close_db_connection(self):
        """Return the connection to the pool."""
        if self._db_conn and self._db_pool:
            self._db_pool.putconn(self._db_conn)
            self._db_conn = None

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Structured failure logging for all DatabaseTask subclasses."""
        logger.error(
            "Celery task failed",
            exc_info=True,
            extra={
                "task_id": task_id,
                "task_name": self.name,
                "exception": str(exc),
            },
        )
        super().on_failure(exc, task_id, args, kwargs, einfo)


# ---------------------------------------------------------------------------
# PDF text extraction
# ---------------------------------------------------------------------------

try:
    from services.content_extractor import extract_text_from_pdf_bytes
except ImportError:
    extract_text_from_pdf_bytes = None  # type: ignore[assignment]


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="workers.tasks.process_pdf_and_extract_text",
    max_retries=2,
    default_retry_delay=30,
)
def process_pdf_and_extract_text(self, pdf_bytes, chapter_id):
    """
    Extract text from PDF bytes and persist to class_chapters.pdf_text.

    Returns:
        dict: {success, text_length, chapter_id, pdf_text (first 500 chars)}
    """
    try:
        if not extract_text_from_pdf_bytes:
            return {
                "success": False,
                "error": "PDF processor not available",
                "chapter_id": chapter_id,
            }

        pdf_text = extract_text_from_pdf_bytes(bytes(pdf_bytes))
        if not pdf_text:
            return {
                "success": False,
                "error": "PDF extraction returned no text",
                "chapter_id": chapter_id,
            }

        conn = self.get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE class_chapters SET pdf_text = %s WHERE chapter_id = %s",
            (pdf_text, chapter_id),
        )
        conn.commit()
        cur.close()
        self.close_db_connection()

        return {
            "success": True,
            "text_length": len(pdf_text),
            "chapter_id": chapter_id,
            "pdf_text": pdf_text[:500],
        }

    except Exception as e:
        logger.warning(
            "process_pdf_and_extract_text failed (attempt %d): %s",
            self.request.retries + 1,
            e,
        )
        try:
            raise self.retry(exc=e, countdown=30 * (2**self.request.retries))
        except self.MaxRetriesExceededError:
            return {"success": False, "error": str(e), "chapter_id": chapter_id}


# ---------------------------------------------------------------------------
# Async exercise generation
# ---------------------------------------------------------------------------

try:
    from services.exercise_generator import generate_exercises_from_pdf_content
except ImportError:
    generate_exercises_from_pdf_content = None  # type: ignore[assignment]


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="workers.tasks.generate_exercises_async",
    max_retries=3,
    default_retry_delay=60,
)
def generate_exercises_async(self, pdf_text, chapter_title, chapter_id, class_id, api_key=None):
    """
    Generate exercises from PDF text via Gemini and persist using the repository.

    Uses chapter_repository.insert_exercise() so all columns (function_name,
    test_cases, language) are written correctly.

    Returns:
        dict: {success, exercise_count, chapter_id}
    """
    try:
        if not generate_exercises_from_pdf_content:
            return {
                "success": False,
                "error": "Exercise generator not available",
                "chapter_id": chapter_id,
            }

        effective_api_key = api_key or config.GEMINI_API_KEY
        if not effective_api_key:
            return {
                "success": False,
                "error": "GEMINI_API_KEY not configured",
                "chapter_id": chapter_id,
            }

        exercises = generate_exercises_from_pdf_content(pdf_text, chapter_title, effective_api_key)
        if not exercises:
            return {"success": False, "error": "No exercises generated", "chapter_id": chapter_id}

        conn = self.get_db_connection()

        # Determine starting exercise_number for this chapter
        cur = conn.cursor()
        cur.execute(
            "SELECT COALESCE(MAX(exercise_number), 0) FROM class_exercises WHERE chapter_id = %s",
            (chapter_id,),
        )
        base_number = (cur.fetchone() or [0])[0]
        cur.close()

        exercise_count = 0
        for i, ex in enumerate(exercises, start=1):
            exercise_id = str(uuid.uuid4())
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO class_exercises
                    (exercise_id, chapter_id, class_id, title, description, difficulty,
                     solution_code, exercise_number, function_name, test_cases, language)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    exercise_id,
                    chapter_id,
                    class_id,
                    ex.get("title", "Untitled Exercise"),
                    ex.get("description", ""),
                    ex.get("difficulty", "medium"),
                    ex.get("solution_code", ""),
                    base_number + i,
                    ex.get("function_name", "solution"),
                    json.dumps(ex.get("test_cases")) if ex.get("test_cases") else None,
                    ex.get("language", "Python"),
                ),
            )
            cur.close()
            exercise_count += 1

        conn.commit()
        self.close_db_connection()

        return {"success": True, "exercise_count": exercise_count, "chapter_id": chapter_id}

    except Exception as e:
        logger.warning(
            "generate_exercises_async failed (attempt %d): %s",
            self.request.retries + 1,
            e,
        )
        try:
            raise self.retry(exc=e, countdown=60 * (2**self.request.retries))
        except self.MaxRetriesExceededError:
            return {"success": False, "error": str(e), "chapter_id": chapter_id}


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------


@celery_app.task(
    bind=True,
    name="workers.tasks.send_email_async",
    max_retries=3,
    default_retry_delay=30,
)
def send_email_async(self, recipient, subject, body):
    """
    Send an email asynchronously via the core.email module.

    Retries up to 3 times with exponential backoff (30s, 60s, 120s).

    Returns:
        dict: {success, recipient}
    """
    try:
        from core.email import send_email

        send_email(to_email=recipient, subject=subject, html_content=body)
        return {"success": True, "recipient": recipient}

    except Exception as e:
        logger.warning(
            "send_email_async failed (attempt %d) for %s: %s",
            self.request.retries + 1,
            recipient,
            e,
        )
        try:
            raise self.retry(exc=e, countdown=30 * (2**self.request.retries))
        except self.MaxRetriesExceededError:
            logger.error("send_email_async: max retries exceeded for %s", recipient)
            return {"success": False, "error": str(e), "recipient": recipient}


# ---------------------------------------------------------------------------
# Combined chapter upload workflow
# ---------------------------------------------------------------------------


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="workers.tasks.process_chapter_upload",
    max_retries=1,
    default_retry_delay=60,
)
def process_chapter_upload(
    self, chapter_id, pdf_bytes, auto_generate_exercises, class_id, chapter_title, api_key=None
):
    """
    Orchestrate PDF extraction → optional exercise generation in one task.

    Returns:
        dict: {success, text_extracted, exercises_generated, chapter_id, exercise_count?}
    """
    result: dict = {
        "success": False,
        "text_extracted": False,
        "exercises_generated": False,
        "chapter_id": chapter_id,
    }

    try:
        extract_result = process_pdf_and_extract_text(bytes(pdf_bytes), chapter_id)
        if not extract_result["success"]:
            result["error"] = f"PDF extraction failed: {extract_result.get('error')}"
            return result

        result["text_extracted"] = True
        pdf_text = extract_result.get("pdf_text", "")

        if auto_generate_exercises and pdf_text:
            exercise_result = generate_exercises_async(
                pdf_text, chapter_title, chapter_id, class_id, api_key
            )
            if exercise_result["success"]:
                result["exercises_generated"] = True
                result["exercise_count"] = exercise_result.get("exercise_count", 0)
            else:
                result["exercise_error"] = exercise_result.get("error")

        result["success"] = True
        return result

    except Exception as e:
        logger.error("process_chapter_upload failed: %s", e, exc_info=True)
        result["error"] = str(e)
        return result


# ---------------------------------------------------------------------------
# Quality score computation (scheduled every 6 hours)
# ---------------------------------------------------------------------------


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="workers.tasks.compute_exercise_quality_scores",
)
def compute_exercise_quality_scores(self, min_outcomes=5):
    """
    Compute quality scores for exercises with enough outcome data.

    Scheduled every 6 hours via Celery beat.
    Also callable manually via POST /api/flywheel/compute-quality (superadmin only).

    Returns:
        dict: {success, exercises_scored}
    """
    import statistics

    try:
        conn = self.get_db_connection()
        cur = conn.cursor()

        from repositories import flywheel_repository as flywheel_repo

        candidates = flywheel_repo.get_exercises_needing_quality_update(conn, min_outcomes)

        exercises_scored = 0
        for candidate in candidates:
            exercise_id = candidate["exercise_id"]
            gen_event_id = candidate.get("generation_event_id")
            try:
                cur.execute(
                    """
                    SELECT user_id, attempt_number, passed, total_score,
                           time_spent_seconds, hints_requested, error_category,
                           test_results
                    FROM exercise_outcome_events
                    WHERE exercise_id = %s
                    ORDER BY created_at ASC
                    """,
                    (exercise_id,),
                )
                rows = cur.fetchall()
                if not rows:
                    continue

                total_attempts = len(rows)
                unique_students = len({r[0] for r in rows})

                first_attempts = [r for r in rows if r[1] == 1]
                first_attempt_pass_rate = (
                    sum(1 for r in first_attempts if r[2]) / len(first_attempts)
                    if first_attempts
                    else None
                )

                overall_pass_rate = sum(1 for r in rows if r[2]) / total_attempts

                passing_attempts_per_user: dict = {}
                for r in rows:
                    uid, attempt_num, passed = r[0], r[1], r[2]
                    if passed and uid not in passing_attempts_per_user:
                        passing_attempts_per_user[uid] = attempt_num

                avg_attempts_to_pass = (
                    sum(passing_attempts_per_user.values()) / len(passing_attempts_per_user)
                    if passing_attempts_per_user
                    else None
                )

                pass_times = [r[4] for r in rows if r[2] and r[4] is not None]
                median_time_to_pass_seconds = (
                    int(statistics.median(pass_times)) if pass_times else None
                )

                all_uids = {r[0] for r in rows}
                passed_uids = set(passing_attempts_per_user.keys())
                dropout_rate = len(all_uids - passed_uids) / len(all_uids) if all_uids else 0.0

                failing_cats = [r[6] for r in rows if not r[2] and r[6]]
                dominant_error_category = (
                    max(set(failing_cats), key=failing_cats.count) if failing_cats else None
                )

                test_fail_counts: dict = {}
                for r in rows:
                    if r[2]:
                        continue
                    tr = r[7]
                    if not isinstance(tr, list):
                        continue
                    for i, t in enumerate(tr):
                        if not (t or {}).get("passed", True):
                            test_fail_counts[i] = test_fail_counts.get(i, 0) + 1

                most_failed_index = (
                    max(test_fail_counts, key=test_fail_counts.get) if test_fail_counts else None
                )
                common_failure_pattern = {
                    "most_failed_test_index": most_failed_index,
                    "most_common_error": dominant_error_category,
                }

                def _norm(value, ideal, max_val=1.0):
                    if value is None:
                        return 0.5
                    deviation = abs(value - ideal) / max(abs(ideal), abs(max_val - ideal), 1e-9)
                    return max(0.0, 1.0 - deviation)

                if (
                    dominant_error_category in ("syntax_error", "import_error")
                    and (len(failing_cats) / max(total_attempts, 1)) > 0.5
                ):
                    quality_label = "broken"
                elif first_attempt_pass_rate is not None and first_attempt_pass_rate > 0.9:
                    quality_label = "too_easy"
                elif (
                    first_attempt_pass_rate is not None and first_attempt_pass_rate < 0.15
                ) or dropout_rate > 0.5:
                    quality_label = "too_hard"
                elif (
                    first_attempt_pass_rate is not None
                    and 0.3 <= first_attempt_pass_rate <= 0.9
                    and dropout_rate < 0.3
                ):
                    quality_label = "good"
                else:
                    quality_label = "good"

                err_ok = 1.0 if dominant_error_category in (None, "none", "logic_error") else 0.5
                quality_score = (
                    0.4 * _norm(first_attempt_pass_rate, ideal=0.5)
                    + 0.3 * (1.0 - min(dropout_rate, 1.0))
                    + 0.2 * _norm(avg_attempts_to_pass or 2.5, ideal=2.5, max_val=10.0)
                    + 0.1 * err_ok
                )
                quality_score = round(min(1.0, max(0.0, quality_score)), 4)

                flywheel_repo.upsert_quality_score(
                    conn,
                    {
                        "exercise_id": exercise_id,
                        "generation_event_id": gen_event_id,
                        "total_attempts": total_attempts,
                        "unique_students": unique_students,
                        "first_attempt_pass_rate": first_attempt_pass_rate,
                        "overall_pass_rate": overall_pass_rate,
                        "avg_attempts_to_pass": avg_attempts_to_pass,
                        "median_time_to_pass_seconds": median_time_to_pass_seconds,
                        "avg_hints_before_pass": 0.0,  # hints not yet tracked
                        "dropout_rate": dropout_rate,
                        "quality_score": quality_score,
                        "quality_label": quality_label,
                        "dominant_error_category": dominant_error_category,
                        "common_failure_pattern": common_failure_pattern,
                        "sample_size": total_attempts,
                    },
                )
                conn.commit()
                exercises_scored += 1

            except Exception as ex_err:
                logger.error(
                    "compute_exercise_quality_scores: failed for %s: %s",
                    exercise_id,
                    ex_err,
                    exc_info=True,
                )
                continue

        cur.close()
        self.close_db_connection()
        logger.info("compute_exercise_quality_scores: scored %d exercises", exercises_scored)
        return {"success": True, "exercises_scored": exercises_scored}

    except Exception as e:
        logger.error("compute_exercise_quality_scores task failed: %s", e, exc_info=True)
        return {"success": False, "error": str(e), "exercises_scored": 0}


# ---------------------------------------------------------------------------
# LTI session cleanup (scheduled daily)
# ---------------------------------------------------------------------------


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="workers.tasks.cleanup_expired_lti_sessions",
)
def cleanup_expired_lti_sessions(self):
    """
    Delete expired LTI sessions. Scheduled daily via Celery beat.

    Returns:
        dict: {deleted: int}
    """
    try:
        conn = self.get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM lti_sessions WHERE expires_at < NOW()")
        deleted = cur.rowcount
        conn.commit()
        cur.close()
        self.close_db_connection()
        logger.info("cleanup_expired_lti_sessions: deleted %d expired sessions", deleted)
        return {"deleted": deleted}
    except Exception as e:
        logger.error("cleanup_expired_lti_sessions failed: %s", e, exc_info=True)
        return {"deleted": 0}
