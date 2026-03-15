"""
Celery Tasks for AnalytIQ
Async tasks for PDF processing, exercise generation, and email sending
"""

import logging
import os
import sys
from celery import Task
from workers.celery_app import celery_app
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Add python directory to path for imports

# Import PDF processor and exercise generator
try:
    from services.content_extractor import extract_text_from_pdf_bytes
except ImportError:
    extract_text_from_pdf_bytes = None

try:
    from services.exercise_generator import generate_exercises_from_pdf_content
except ImportError:
    generate_exercises_from_pdf_content = None

# Import Resend for email
try:
    import resend
except ImportError:
    resend = None


class DatabaseTask(Task):
    """Base task with database connection handling"""

    _db_conn = None

    def get_db_connection(self):
        """Get database connection (reuse connection pool)"""
        if self._db_conn is None:
            import psycopg2
            from psycopg2 import pool

            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                raise ValueError("DATABASE_URL not set")

            # Create connection pool
            self._db_pool = psycopg2.pool.SimpleConnectionPool(
                1, 10, database_url, connect_timeout=10
            )
            self._db_conn = self._db_pool.getconn()

        return self._db_conn

    def close_db_connection(self):
        """Close database connection"""
        if self._db_conn:
            self._db_pool.putconn(self._db_conn)
            self._db_conn = None

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Log task failures with structured context."""
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


@celery_app.task(bind=True, base=DatabaseTask, name="tasks.process_pdf_and_extract_text")
def process_pdf_and_extract_text(self, pdf_bytes, chapter_id):
    """
    Extract text from PDF bytes and store in database

    Args:
        pdf_bytes: PDF file as bytes
        chapter_id: Chapter ID to update

    Returns:
        dict: {'success': bool, 'text_length': int, 'chapter_id': str}
    """
    try:
        if not extract_text_from_pdf_bytes:
            return {
                "success": False,
                "error": "PDF processor not available",
                "chapter_id": chapter_id,
            }

        # Extract text from PDF
        pdf_text = extract_text_from_pdf_bytes(bytes(pdf_bytes))

        # Store extracted text in database (optional - for caching)
        conn = self.get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE class_chapters 
            SET pdf_text = %s 
            WHERE chapter_id = %s
        """,
            (pdf_text, chapter_id),
        )

        conn.commit()
        cursor.close()
        self.close_db_connection()

        return {
            "success": True,
            "text_length": len(pdf_text),
            "chapter_id": chapter_id,
            "pdf_text": pdf_text[:500],  # First 500 chars for preview
        }

    except Exception as e:
        return {"success": False, "error": str(e), "chapter_id": chapter_id}


@celery_app.task(bind=True, base=DatabaseTask, name="tasks.generate_exercises_async")
def generate_exercises_async(self, pdf_text, chapter_title, chapter_id, class_id, api_key):
    """
    Generate exercises from PDF text using Gemini API

    Args:
        pdf_text: Extracted PDF text
        chapter_title: Chapter title
        chapter_id: Chapter ID
        class_id: Class ID
        api_key: Gemini API key

    Returns:
        dict: {'success': bool, 'exercise_count': int, 'chapter_id': str}
    """
    try:
        if not generate_exercises_from_pdf_content:
            return {
                "success": False,
                "error": "Exercise generator not available",
                "chapter_id": chapter_id,
            }

        # Generate exercises
        exercises = generate_exercises_from_pdf_content(pdf_text, chapter_title, api_key)

        if not exercises:
            return {"success": False, "error": "No exercises generated", "chapter_id": chapter_id}

        # Store exercises in database
        conn = self.get_db_connection()
        cursor = conn.cursor()

        exercise_count = 0
        for exercise in exercises:
            cursor.execute(
                """
                INSERT INTO class_exercises 
                (chapter_id, class_id, title, description, difficulty, solution_code)
                VALUES (%s, %s, %s, %s, %s, %s)
            """,
                (
                    chapter_id,
                    class_id,
                    exercise.get("title", "Untitled Exercise"),
                    exercise.get("description", ""),
                    exercise.get("difficulty", "medium"),
                    exercise.get("solution_code", ""),
                ),
            )
            exercise_count += 1

        conn.commit()
        cursor.close()
        self.close_db_connection()

        return {"success": True, "exercise_count": exercise_count, "chapter_id": chapter_id}

    except Exception as e:
        return {"success": False, "error": str(e), "chapter_id": chapter_id}


@celery_app.task(name="tasks.send_email_async")
def send_email_async(recipient, subject, body):
    """
    Send email asynchronously using Resend API.

    Args:
        recipient: Email recipient
        subject: Email subject
        body: Email body (HTML)

    Returns:
        dict: {'success': bool, 'recipient': str}
    """
    try:
        if not resend:
            return {"success": False, "error": "Resend library not installed", "recipient": recipient}

        # Initialize Resend API key
        if not getattr(resend, "api_key", None):
            resend.api_key = os.getenv("RESEND_API_KEY")

        if not getattr(resend, "api_key", None):
            return {"success": False, "error": "RESEND_API_KEY is missing", "recipient": recipient}

        # Default sender (MUST match verified domain in Resend)
        from_email = os.getenv("MAIL_DEFAULT_SENDER", "techsupport@myanalytiq.org")

        logger.info("Sending email FROM: %s TO: %s", from_email, recipient)

        response = resend.Emails.send({
            "from": f"AnalytIQ Support <{from_email}>",
            "to": [recipient],
            "subject": subject,
            "html": body,
        })

        logger.info("Resend success: %s", response)

        return {"success": True, "recipient": recipient}

    except Exception as e:
        logger.error("Resend error: %s", repr(e))
        return {"success": False, "error": str(e), "recipient": recipient}


@celery_app.task(bind=True, base=DatabaseTask, name="tasks.process_chapter_upload")
def process_chapter_upload(
    self, chapter_id, pdf_bytes, auto_generate_exercises, class_id, chapter_title, api_key
):
    """
    Combined workflow: Extract PDF text and optionally generate exercises

    Args:
        chapter_id: Chapter ID
        pdf_bytes: PDF file bytes
        auto_generate_exercises: Whether to auto-generate exercises
        class_id: Class ID
        chapter_title: Chapter title
        api_key: Gemini API key

    Returns:
        dict: {'success': bool, 'text_extracted': bool, 'exercises_generated': bool}
    """
    result = {
        "success": False,
        "text_extracted": False,
        "exercises_generated": False,
        "chapter_id": chapter_id,
    }

    try:
        # Step 1: Extract PDF text
        extract_result = process_pdf_and_extract_text(pdf_bytes, chapter_id)

        if not extract_result["success"]:
            result["error"] = f"PDF extraction failed: {extract_result.get('error')}"
            return result

        result["text_extracted"] = True
        pdf_text = extract_result.get("pdf_text", "")

        # Step 2: Generate exercises if requested
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
        result["error"] = str(e)
        return result


@celery_app.task(bind=True, base=DatabaseTask, name="tasks.compute_exercise_quality_scores")
def compute_exercise_quality_scores(self, min_outcomes=5):
    """
    Compute and upsert quality scores for exercises that have accumulated
    enough new outcome events since the last computation.

    Scheduled every 6 hours via Celery beat.
    Also callable manually via POST /api/flywheel/compute-quality (superadmin).

    Returns:
        dict: {'success': bool, 'exercises_scored': int}
    """
    try:
        import statistics

        conn = self.get_db_connection()
        cur = conn.cursor()

        # Import here to avoid circular import at module load time
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

                # first_attempt_pass_rate: fraction of students who passed on attempt 1
                first_attempts = [r for r in rows if r[1] == 1]
                first_attempt_pass_rate = (
                    sum(1 for r in first_attempts if r[2]) / len(first_attempts)
                    if first_attempts else None
                )

                overall_pass_rate = sum(1 for r in rows if r[2]) / total_attempts

                # avg_attempts_to_pass: per-student first passing attempt_number
                passing_attempts_per_user: dict = {}
                for r in rows:
                    uid, attempt_num, passed = r[0], r[1], r[2]
                    if passed and uid not in passing_attempts_per_user:
                        passing_attempts_per_user[uid] = attempt_num
                avg_attempts_to_pass = (
                    sum(passing_attempts_per_user.values()) / len(passing_attempts_per_user)
                    if passing_attempts_per_user else None
                )

                pass_times = [r[4] for r in rows if r[2] and r[4] is not None]
                median_time_to_pass_seconds = (
                    int(statistics.median(pass_times)) if pass_times else None
                )

                all_uids = {r[0] for r in rows}
                passed_uids = set(passing_attempts_per_user.keys())
                dropout_rate = (
                    len(all_uids - passed_uids) / len(all_uids) if all_uids else 0.0
                )

                avg_hints_before_pass = 0.0  # hints not yet tracked

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
                    max(test_fail_counts, key=test_fail_counts.get)
                    if test_fail_counts else None
                )
                common_failure_pattern = {
                    "most_failed_test_index": most_failed_index,
                    "most_common_error": dominant_error_category,
                }

                def _norm(value, ideal, max_val=1.0):
                    if value is None:
                        return 0.5
                    deviation = abs(value - ideal) / max(
                        abs(ideal), abs(max_val - ideal), 1e-9
                    )
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

                err_ok = (
                    1.0 if dominant_error_category in (None, "none", "logic_error") else 0.5
                )
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
                        "avg_hints_before_pass": avg_hints_before_pass,
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
                    exercise_id, ex_err, exc_info=True,
                )
                continue

        cur.close()
        self.close_db_connection()
        logger.info(
            "compute_exercise_quality_scores: scored %d exercises", exercises_scored
        )
        return {"success": True, "exercises_scored": exercises_scored}

    except Exception as e:
        logger.error("compute_exercise_quality_scores task failed: %s", e, exc_info=True)
        return {"success": False, "error": str(e), "exercises_scored": 0}


@celery_app.task(name="tasks.cleanup_expired_lti_sessions")
def cleanup_expired_lti_sessions():
    """
    Delete expired LTI sessions from the database.
    Scheduled daily via Celery beat.

    Returns:
        dict: {'deleted': int} — number of rows removed
    """
    try:
        import psycopg2

        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            logger.error("cleanup_expired_lti_sessions: DATABASE_URL not set")
            return {"deleted": 0}

        conn = psycopg2.connect(database_url, connect_timeout=10)
        cur = conn.cursor()
        cur.execute("DELETE FROM lti_sessions WHERE expires_at < NOW()")
        deleted = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
        logger.info("cleanup_expired_lti_sessions: deleted %d expired sessions", deleted)
        return {"deleted": deleted}
    except Exception as e:
        logger.error("cleanup_expired_lti_sessions failed: %s", e, exc_info=True)
        return {"deleted": 0}
