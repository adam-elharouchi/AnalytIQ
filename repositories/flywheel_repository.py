"""
Flywheel Repository — SQL operations for the data flywheel instrumentation layer.

Tracks exercise generation events and grading outcome events so we can measure
which syllabus content types, prompt versions, and exercise structures produce
the best student outcomes over time.

Every function receives a DB *connection* and returns plain Python data.
The caller (blueprint or task) is responsible for commit / rollback / connection lifecycle.

CRITICAL: Every insert function is wrapped in try/except and will NEVER raise.
Instrumentation must never break generation or grading.
"""

import json
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Generation events
# ---------------------------------------------------------------------------


def insert_generation_event(conn, event_data: dict) -> Optional[str]:
    """
    Insert a generation event row.  Returns the new event UUID as a string,
    or None if the insert fails for any reason.

    event_data keys (all optional — missing keys are stored as NULL):
        exercise_id, class_id, chapter_id, tenant_id,
        source_content_hash, source_content_type, source_char_count, was_truncated,
        detected_language, detected_topics,
        gemini_model, prompt_template_version, prompt_tokens, completion_tokens,
        generation_params, difficulty_requested, difficulty_generated,
        exercise_type, exercise_structure, num_test_cases, generation_time_ms
    """
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO exercise_generation_events (
                exercise_id, class_id, chapter_id, tenant_id,
                source_content_hash, source_content_type, source_char_count, was_truncated,
                detected_language, detected_topics,
                gemini_model, prompt_template_version, prompt_tokens, completion_tokens,
                generation_params, difficulty_requested, difficulty_generated,
                exercise_type, exercise_structure, num_test_cases, generation_time_ms
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s
            )
            RETURNING id
            """,
            (
                event_data.get("exercise_id"),
                event_data.get("class_id"),
                event_data.get("chapter_id"),
                event_data.get("tenant_id"),
                event_data.get("source_content_hash"),
                event_data.get("source_content_type"),
                event_data.get("source_char_count"),
                event_data.get("was_truncated", False),
                event_data.get("detected_language"),
                json.dumps(event_data.get("detected_topics") or []),
                event_data.get("gemini_model"),
                event_data.get("prompt_template_version"),
                event_data.get("prompt_tokens"),
                event_data.get("completion_tokens"),
                json.dumps(event_data.get("generation_params") or {}),
                event_data.get("difficulty_requested"),
                event_data.get("difficulty_generated"),
                event_data.get("exercise_type"),
                json.dumps(event_data.get("exercise_structure") or {}),
                event_data.get("num_test_cases"),
                event_data.get("generation_time_ms"),
            ),
        )
        row = cur.fetchone()
        cur.close()
        return str(row[0]) if row else None
    except Exception as e:
        logger.error("flywheel: insert_generation_event failed: %s", e, exc_info=True)
        return None


def get_generation_event_by_exercise(conn, exercise_id: str) -> Optional[Dict]:
    """
    Return the most recent generation event for the given exercise_id, or None.
    """
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, exercise_id, class_id, chapter_id, detected_language,
                   gemini_model, prompt_template_version, difficulty_generated,
                   num_test_cases, generation_time_ms, created_at
            FROM exercise_generation_events
            WHERE exercise_id = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (exercise_id,),
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            return None
        return {
            "id": str(row[0]),
            "exercise_id": row[1],
            "class_id": row[2],
            "chapter_id": row[3],
            "detected_language": row[4],
            "gemini_model": row[5],
            "prompt_template_version": row[6],
            "difficulty_generated": row[7],
            "num_test_cases": row[8],
            "generation_time_ms": row[9],
            "created_at": row[10].isoformat() if row[10] else None,
        }
    except Exception as e:
        logger.error("flywheel: get_generation_event_by_exercise failed: %s", e, exc_info=True)
        return None


def update_exercise_generation_event_id(conn, exercise_id: str, generation_event_id: str) -> None:
    """
    Back-link class_exercises.generation_event_id after the exercise row is created.
    Must not raise.
    """
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE class_exercises SET generation_event_id = %s WHERE exercise_id = %s",
            (generation_event_id, exercise_id),
        )
        cur.close()
    except Exception as e:
        logger.error(
            "flywheel: update_exercise_generation_event_id failed for %s: %s",
            exercise_id, e, exc_info=True,
        )


# ---------------------------------------------------------------------------
# Outcome events
# ---------------------------------------------------------------------------


def insert_outcome_event(conn, outcome_data: dict) -> Optional[str]:
    """
    Insert an outcome event row.  Returns the new event UUID as a string,
    or None if the insert fails.

    outcome_data keys:
        exercise_id, generation_event_id, user_id, class_id, tenant_id,
        attempt_number, time_spent_seconds, hints_requested, ai_chat_messages,
        code_char_count, passed, total_score, correctness_score, quality_score,
        tests_total, tests_passed, test_results, error_category, execution_time_ms
    """
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO exercise_outcome_events (
                exercise_id, generation_event_id, user_id, class_id, tenant_id,
                attempt_number, time_spent_seconds, hints_requested, ai_chat_messages,
                code_char_count, passed, total_score, correctness_score, quality_score,
                tests_total, tests_passed, test_results, error_category, execution_time_ms
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            )
            RETURNING id
            """,
            (
                outcome_data.get("exercise_id"),
                outcome_data.get("generation_event_id"),
                outcome_data.get("user_id"),
                outcome_data.get("class_id"),
                outcome_data.get("tenant_id"),
                outcome_data.get("attempt_number"),
                outcome_data.get("time_spent_seconds"),
                outcome_data.get("hints_requested", 0),
                outcome_data.get("ai_chat_messages", 0),
                outcome_data.get("code_char_count"),
                outcome_data.get("passed"),
                outcome_data.get("total_score"),
                outcome_data.get("correctness_score"),
                outcome_data.get("quality_score"),
                outcome_data.get("tests_total"),
                outcome_data.get("tests_passed"),
                json.dumps(outcome_data.get("test_results") or []),
                outcome_data.get("error_category"),
                outcome_data.get("execution_time_ms"),
            ),
        )
        row = cur.fetchone()
        cur.close()
        return str(row[0]) if row else None
    except Exception as e:
        logger.error("flywheel: insert_outcome_event failed: %s", e, exc_info=True)
        return None


def get_outcome_count_for_user_exercise(conn, user_id: str, exercise_id: str) -> int:
    """
    Return the count of existing outcome events for this user + exercise pair.
    Used to derive attempt_number (count + 1).  Returns 0 on any error.
    """
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM exercise_outcome_events WHERE user_id = %s AND exercise_id = %s",
            (user_id, exercise_id),
        )
        row = cur.fetchone()
        cur.close()
        return int(row[0]) if row else 0
    except Exception as e:
        logger.error("flywheel: get_outcome_count_for_user_exercise failed: %s", e, exc_info=True)
        return 0


# ---------------------------------------------------------------------------
# Quality scores
# ---------------------------------------------------------------------------


def upsert_quality_score(conn, score_data: dict) -> None:
    """
    INSERT … ON CONFLICT (exercise_id) DO UPDATE for exercise_quality_scores.
    Must not raise.
    """
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO exercise_quality_scores (
                exercise_id, generation_event_id, total_attempts, unique_students,
                first_attempt_pass_rate, overall_pass_rate, avg_attempts_to_pass,
                median_time_to_pass_seconds, avg_hints_before_pass, dropout_rate,
                quality_score, quality_label, dominant_error_category,
                common_failure_pattern, last_computed_at, sample_size
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, NOW(), %s
            )
            ON CONFLICT (exercise_id) DO UPDATE SET
                generation_event_id       = EXCLUDED.generation_event_id,
                total_attempts            = EXCLUDED.total_attempts,
                unique_students           = EXCLUDED.unique_students,
                first_attempt_pass_rate   = EXCLUDED.first_attempt_pass_rate,
                overall_pass_rate         = EXCLUDED.overall_pass_rate,
                avg_attempts_to_pass      = EXCLUDED.avg_attempts_to_pass,
                median_time_to_pass_seconds = EXCLUDED.median_time_to_pass_seconds,
                avg_hints_before_pass     = EXCLUDED.avg_hints_before_pass,
                dropout_rate              = EXCLUDED.dropout_rate,
                quality_score             = EXCLUDED.quality_score,
                quality_label             = EXCLUDED.quality_label,
                dominant_error_category   = EXCLUDED.dominant_error_category,
                common_failure_pattern    = EXCLUDED.common_failure_pattern,
                last_computed_at          = NOW(),
                sample_size               = EXCLUDED.sample_size
            """,
            (
                score_data.get("exercise_id"),
                score_data.get("generation_event_id"),
                score_data.get("total_attempts", 0),
                score_data.get("unique_students", 0),
                score_data.get("first_attempt_pass_rate"),
                score_data.get("overall_pass_rate"),
                score_data.get("avg_attempts_to_pass"),
                score_data.get("median_time_to_pass_seconds"),
                score_data.get("avg_hints_before_pass"),
                score_data.get("dropout_rate"),
                score_data.get("quality_score"),
                score_data.get("quality_label"),
                score_data.get("dominant_error_category"),
                json.dumps(score_data.get("common_failure_pattern") or {}),
                score_data.get("sample_size"),
            ),
        )
        cur.close()
    except Exception as e:
        logger.error("flywheel: upsert_quality_score failed: %s", e, exc_info=True)


def get_quality_score(conn, exercise_id: str) -> Optional[Dict]:
    """Return the quality score row for a single exercise, or None."""
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT exercise_id, generation_event_id, total_attempts, unique_students,
                   first_attempt_pass_rate, overall_pass_rate, avg_attempts_to_pass,
                   median_time_to_pass_seconds, avg_hints_before_pass, dropout_rate,
                   quality_score, quality_label, dominant_error_category,
                   common_failure_pattern, last_computed_at, sample_size
            FROM exercise_quality_scores
            WHERE exercise_id = %s
            """,
            (exercise_id,),
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            return None
        return _quality_row_to_dict(row)
    except Exception as e:
        logger.error("flywheel: get_quality_score failed: %s", e, exc_info=True)
        return None


def get_class_quality_scores(conn, class_id: str) -> List[Dict]:
    """
    Return all quality scores for exercises in a class, sorted by quality_score ASC
    (worst exercises first — for the professor dashboard).
    """
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT qs.exercise_id, qs.generation_event_id, qs.total_attempts, qs.unique_students,
                   qs.first_attempt_pass_rate, qs.overall_pass_rate, qs.avg_attempts_to_pass,
                   qs.median_time_to_pass_seconds, qs.avg_hints_before_pass, qs.dropout_rate,
                   qs.quality_score, qs.quality_label, qs.dominant_error_category,
                   qs.common_failure_pattern, qs.last_computed_at, qs.sample_size
            FROM exercise_quality_scores qs
            JOIN class_exercises ce ON qs.exercise_id = ce.exercise_id
            WHERE ce.class_id = %s
            ORDER BY qs.quality_score ASC NULLS LAST
            """,
            (class_id,),
        )
        rows = cur.fetchall()
        cur.close()
        return [_quality_row_to_dict(row) for row in rows]
    except Exception as e:
        logger.error("flywheel: get_class_quality_scores failed: %s", e, exc_info=True)
        return []


def get_exercises_needing_quality_update(conn, min_outcomes: int = 5) -> List[Dict]:
    """
    Find exercises where the count of outcome events since last quality computation
    is >= min_outcomes (or where no quality score has ever been computed).
    Returns list of {exercise_id, generation_event_id, new_outcome_count}.
    """
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                eoe.exercise_id,
                qs.generation_event_id,
                COUNT(eoe.id) AS new_outcome_count
            FROM exercise_outcome_events eoe
            LEFT JOIN exercise_quality_scores qs ON eoe.exercise_id = qs.exercise_id
            WHERE qs.last_computed_at IS NULL
               OR eoe.created_at > qs.last_computed_at
            GROUP BY eoe.exercise_id, qs.generation_event_id
            HAVING COUNT(eoe.id) >= %s
            """,
            (min_outcomes,),
        )
        rows = cur.fetchall()
        cur.close()
        return [
            {
                "exercise_id": row[0],
                "generation_event_id": str(row[1]) if row[1] else None,
                "new_outcome_count": row[2],
            }
            for row in rows
        ]
    except Exception as e:
        logger.error("flywheel: get_exercises_needing_quality_update failed: %s", e, exc_info=True)
        return []


def get_generation_effectiveness(conn) -> dict:
    """
    Aggregate stats grouped by prompt_template_version, detected_language,
    source_content_type, and difficulty_generated.
    Returns dict of groups with avg quality_score, exercise count, and problem counts.
    """
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                ge.prompt_template_version,
                ge.detected_language,
                ge.source_content_type,
                ge.difficulty_generated,
                COUNT(DISTINCT ge.exercise_id)                           AS exercise_count,
                AVG(qs.quality_score)                                    AS avg_quality_score,
                COUNT(CASE WHEN qs.quality_label IN ('broken', 'too_hard') THEN 1 END)
                                                                         AS problem_count
            FROM exercise_generation_events ge
            LEFT JOIN exercise_quality_scores qs ON ge.exercise_id = qs.exercise_id
            WHERE ge.exercise_id IS NOT NULL
            GROUP BY ge.prompt_template_version, ge.detected_language,
                     ge.source_content_type, ge.difficulty_generated
            ORDER BY ge.prompt_template_version, ge.detected_language
            """
        )
        rows = cur.fetchall()
        cur.close()
        return {
            "groups": [
                {
                    "prompt_template_version": row[0],
                    "detected_language": row[1],
                    "source_content_type": row[2],
                    "difficulty_generated": row[3],
                    "exercise_count": row[4],
                    "avg_quality_score": float(row[5]) if row[5] is not None else None,
                    "problem_count": row[6],
                }
                for row in rows
            ]
        }
    except Exception as e:
        logger.error("flywheel: get_generation_effectiveness failed: %s", e, exc_info=True)
        return {"groups": []}


def get_flywheel_health(conn) -> dict:
    """
    Coverage and quality distribution stats for the superadmin flywheel health endpoint.
    """
    try:
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM class_exercises")
        total_exercises = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(*) FROM class_exercises WHERE generation_event_id IS NOT NULL"
        )
        instrumented = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM exercise_outcome_events")
        total_outcomes = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM exercise_quality_scores")
        exercises_with_quality = cur.fetchone()[0]

        cur.execute(
            """
            SELECT quality_label, COUNT(*) FROM exercise_quality_scores
            GROUP BY quality_label
            """
        )
        dist_rows = cur.fetchall()
        quality_distribution = {row[0]: row[1] for row in dist_rows}

        cur.execute(
            """
            SELECT qs.exercise_id, ce.title, qs.quality_score, qs.quality_label, qs.total_attempts
            FROM exercise_quality_scores qs
            JOIN class_exercises ce ON qs.exercise_id = ce.exercise_id
            WHERE qs.total_attempts >= 10
            ORDER BY qs.quality_score ASC NULLS LAST
            LIMIT 5
            """
        )
        top_problematic_rows = cur.fetchall()
        cur.close()

        coverage_pct = round(instrumented / total_exercises * 100, 1) if total_exercises else 0.0

        return {
            "total_exercises": total_exercises,
            "instrumented_exercises": instrumented,
            "coverage_pct": coverage_pct,
            "total_outcome_events": total_outcomes,
            "exercises_with_quality_scores": exercises_with_quality,
            "quality_distribution": quality_distribution,
            "top_problematic": [
                {
                    "exercise_id": row[0],
                    "title": row[1],
                    "quality_score": float(row[2]) if row[2] is not None else None,
                    "quality_label": row[3],
                    "total_attempts": row[4],
                }
                for row in top_problematic_rows
            ],
        }
    except Exception as e:
        logger.error("flywheel: get_flywheel_health failed: %s", e, exc_info=True)
        return {}


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _quality_row_to_dict(row) -> dict:
    return {
        "exercise_id": row[0],
        "generation_event_id": str(row[1]) if row[1] else None,
        "total_attempts": row[2],
        "unique_students": row[3],
        "first_attempt_pass_rate": row[4],
        "overall_pass_rate": row[5],
        "avg_attempts_to_pass": row[6],
        "median_time_to_pass_seconds": row[7],
        "avg_hints_before_pass": row[8],
        "dropout_rate": row[9],
        "quality_score": row[10],
        "quality_label": row[11],
        "dominant_error_category": row[12],
        "common_failure_pattern": row[13],
        "last_computed_at": row[14].isoformat() if row[14] else None,
        "sample_size": row[15],
    }
