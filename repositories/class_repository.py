"""
Class Repository — SQL operations for classes, enrollments, progress, leaderboards, and resources.

Every function receives a DB *connection* and returns plain Python data.
The caller (blueprint) is responsible for commit / rollback / connection lifecycle.
"""

import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Classes CRUD
# ---------------------------------------------------------------------------


def class_code_exists(conn, class_code):
    """Return True if a class with the given code already exists."""
    cur = conn.cursor()
    cur.execute("SELECT class_id FROM classes WHERE class_id = %s", (class_code,))
    exists = cur.fetchone() is not None
    cur.close()
    return exists


def insert_class(conn, class_code, professor_id, name, description):
    """Insert a new class and return the created row as a tuple."""
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO classes (class_id, professor_id, name, description)
           VALUES (%s, %s, %s, %s)
           RETURNING class_id, name, description, created_at""",
        (class_code, professor_id, name, description),
    )
    row = cur.fetchone()
    cur.close()
    return row


def get_class_owner(conn, class_id):
    """Return the professor_id that owns *class_id*, or None."""
    cur = conn.cursor()
    cur.execute("SELECT professor_id FROM classes WHERE class_id = %s", (class_id,))
    row = cur.fetchone()
    cur.close()
    return row[0] if row else None


def get_class_detail(conn, class_id):
    """Return full class row joined with professor info, or None."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT c.class_id, c.name, c.description, c.professor_id, c.created_at,
               u.name AS professor_name, u.email AS professor_email,
               c.lti_context_id, c.ags_enabled
        FROM classes c
        JOIN users u ON c.professor_id = u.user_id
        WHERE c.class_id = %s
        """,
        (class_id,),
    )
    row = cur.fetchone()
    cur.close()
    return row


def count_professor_classes(conn, professor_id):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM classes WHERE professor_id = %s", (professor_id,))
    count = cur.fetchone()[0] or 0
    cur.close()
    return count


def get_professor_classes(conn, professor_id, limit, offset):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT c.class_id, c.name, c.description, c.created_at,
               COUNT(DISTINCT ce.student_id) AS student_count,
               COUNT(DISTINCT ch.chapter_id) AS chapter_count
        FROM classes c
        LEFT JOIN class_enrollments ce ON c.class_id = ce.class_id
        LEFT JOIN class_chapters ch ON c.class_id = ch.class_id
        WHERE c.professor_id = %s
        GROUP BY c.class_id, c.name, c.description, c.created_at
        ORDER BY c.created_at DESC
        LIMIT %s OFFSET %s
        """,
        (professor_id, limit, offset),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def count_student_enrolled_classes(conn, student_id):
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM class_enrollments WHERE student_id = %s",
        (student_id,),
    )
    count = cur.fetchone()[0] or 0
    cur.close()
    return count


def get_student_classes(conn, student_id, limit, offset):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT c.class_id, c.name, c.description, c.created_at,
               COUNT(DISTINCT ce.student_id) AS student_count,
               COUNT(DISTINCT ch.chapter_id) AS chapter_count
        FROM classes c
        INNER JOIN class_enrollments ce ON c.class_id = ce.class_id
        LEFT JOIN class_chapters ch ON c.class_id = ch.class_id
        WHERE ce.student_id = %s
        GROUP BY c.class_id, c.name, c.description, c.created_at
        ORDER BY c.created_at DESC
        LIMIT %s OFFSET %s
        """,
        (student_id, limit, offset),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def count_class_students(conn, class_id):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM class_enrollments WHERE class_id = %s", (class_id,))
    count = cur.fetchone()[0] or 0
    cur.close()
    return count


def count_class_chapters(conn, class_id):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM class_chapters WHERE class_id = %s", (class_id,))
    count = cur.fetchone()[0] or 0
    cur.close()
    return count


def count_class_exercises(conn, class_id):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM class_exercises WHERE class_id = %s", (class_id,))
    count = cur.fetchone()[0] or 0
    cur.close()
    return count


def update_class_fields(conn, class_id, update_fields, params):
    """Update whitelisted fields on a class.

    *update_fields* is a list of safe SQL fragments like ``["name = %s"]``.
    *params* is the matching value list **without** class_id (appended here).
    """
    cur = conn.cursor()
    params = list(params) + [class_id]
    query = f"""
        UPDATE classes
        SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
        WHERE class_id = %s
    """
    cur.execute(query, params)
    cur.close()


def delete_class(conn, class_id):
    cur = conn.cursor()
    cur.execute("DELETE FROM classes WHERE class_id = %s", (class_id,))
    cur.close()


# ---------------------------------------------------------------------------
# Enrollments
# ---------------------------------------------------------------------------


def check_enrollment(conn, class_id, student_id):
    """Return True if *student_id* is enrolled in *class_id*."""
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM class_enrollments WHERE class_id = %s AND student_id = %s",
        (class_id, student_id),
    )
    enrolled = cur.fetchone() is not None
    cur.close()
    return enrolled


def get_class_with_name(conn, class_id):
    """Return (class_id, name, professor_id) or None."""
    cur = conn.cursor()
    cur.execute(
        "SELECT class_id, name, professor_id FROM classes WHERE class_id = %s",
        (class_id,),
    )
    row = cur.fetchone()
    cur.close()
    return row


def enroll_student(conn, class_id, student_id):
    """Insert enrollment row and return enrolled_at timestamp."""
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO class_enrollments (class_id, student_id)
        VALUES (%s, %s)
        RETURNING enrolled_at
        """,
        (class_id, student_id),
    )
    enrolled_at = cur.fetchone()[0]
    cur.close()
    return enrolled_at


def get_enrolled_classes_paginated(conn, student_id, limit, offset):
    """Return enrolled classes with professor info and counts."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            c.class_id, c.name, c.description, c.created_at,
            u.name AS professor_name, u.email AS professor_email,
            ce.enrolled_at,
            (SELECT COUNT(*) FROM class_enrollments WHERE class_id = c.class_id) AS student_count,
            (SELECT COUNT(*) FROM class_chapters WHERE class_id = c.class_id) AS chapter_count
        FROM class_enrollments ce
        JOIN classes c ON ce.class_id = c.class_id
        JOIN users u ON c.professor_id = u.user_id
        WHERE ce.student_id = %s
        ORDER BY ce.enrolled_at DESC
        LIMIT %s OFFSET %s
        """,
        (student_id, limit, offset),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def get_class_students_list(conn, class_id):
    """Return list of enrolled students (user_id, name, email, enrolled_at)."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT u.user_id, u.name, u.email, ce.enrolled_at
        FROM class_enrollments ce
        JOIN users u ON ce.student_id = u.user_id
        WHERE ce.class_id = %s
        ORDER BY ce.enrolled_at ASC
        """,
        (class_id,),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


# ---------------------------------------------------------------------------
# Progress
# ---------------------------------------------------------------------------


def get_class_exercises_for_progress(conn, class_id):
    """Return exercises for progress tracking."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT exercise_id, title, difficulty
        FROM class_exercises
        WHERE class_id = %s
        ORDER BY exercise_number, created_at
        """,
        (class_id,),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def get_class_enrolled_students_for_progress(conn, class_id):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT u.user_id, u.name, u.email
        FROM class_enrollments ce
        JOIN users u ON ce.student_id = u.user_id
        WHERE ce.class_id = %s
        ORDER BY u.name
        """,
        (class_id,),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def get_class_progress_bulk(conn, class_id):
    """Single aggregated query returning progress for all students × exercises."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            ce.student_id,
            ex.exercise_id,
            COALESCE(pp.best_score, 0)        AS best_score,
            COALESCE(pp.best_accuracy, 0)      AS best_accuracy,
            COALESCE(pp.total_attempts, 0)     AS total_attempts,
            COALESCE(pp.completed, false)      AS completed,
            pp.last_completed_at
        FROM class_enrollments ce
        CROSS JOIN class_exercises ex
        LEFT JOIN practice_progress pp
            ON pp.user_id = ce.student_id
           AND pp.class_exercise_id = ex.exercise_id
        WHERE ce.class_id = %s AND ex.class_id = %s
        ORDER BY ce.student_id, ex.exercise_number, ex.created_at
        """,
        (class_id, class_id),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def get_student_progress_by_class(conn, user_id, class_id):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            pp.class_exercise_id,
            ce.title AS exercise_title,
            ce.difficulty,
            pp.best_score,
            pp.best_accuracy,
            pp.total_attempts,
            pp.completed,
            pp.last_completed_at
        FROM practice_progress pp
        JOIN class_exercises ce ON pp.class_exercise_id = ce.exercise_id
        WHERE pp.user_id = %s AND pp.class_id = %s AND ce.class_id = %s
        ORDER BY ce.exercise_number, ce.created_at
        """,
        (user_id, class_id, class_id),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def get_student_all_progress(conn, user_id):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            exercise_id, exercise_title,
            best_score, best_accuracy,
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


def get_student_by_id(conn, student_id):
    """Return (user_id, name, email) or None."""
    cur = conn.cursor()
    cur.execute("SELECT user_id, name, email FROM users WHERE user_id = %s", (student_id,))
    row = cur.fetchone()
    cur.close()
    return row


def get_student_progress_for_class(conn, student_id, class_id):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            pp.class_exercise_id,
            ce.title AS exercise_title,
            ce.difficulty,
            pp.best_score,
            pp.best_accuracy,
            pp.total_attempts,
            pp.completed,
            pp.last_completed_at
        FROM practice_progress pp
        JOIN class_exercises ce ON pp.class_exercise_id = ce.exercise_id
        WHERE pp.user_id = %s AND pp.class_id = %s AND ce.class_id = %s
        ORDER BY ce.exercise_number, ce.created_at
        """,
        (student_id, class_id, class_id),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def get_student_progress_for_professor(conn, student_id, professor_id):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            pp.class_exercise_id,
            ce.title AS exercise_title,
            ce.difficulty,
            pp.class_id,
            c.name AS class_name,
            pp.best_score,
            pp.best_accuracy,
            pp.total_attempts,
            pp.completed,
            pp.last_completed_at
        FROM practice_progress pp
        JOIN class_exercises ce ON pp.class_exercise_id = ce.exercise_id
        JOIN classes c ON pp.class_id = c.class_id
        WHERE pp.user_id = %s AND c.professor_id = %s
        ORDER BY c.name, ce.exercise_number
        """,
        (student_id, professor_id),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


# ---------------------------------------------------------------------------
# Leaderboards
# ---------------------------------------------------------------------------


def get_class_average_leaderboard(conn, class_id):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            u.user_id, u.name, u.email,
            COALESCE(AVG(pp.best_score), 0) AS average_score,
            COUNT(DISTINCT pp.exercise_id)  AS exercises_completed
        FROM class_enrollments ce
        JOIN users u ON ce.student_id = u.user_id
        LEFT JOIN practice_progress pp
            ON pp.user_id = u.user_id AND pp.class_id = %s AND pp.completed = true
        WHERE ce.class_id = %s
        GROUP BY u.user_id, u.name, u.email
        ORDER BY average_score DESC, u.name ASC
        """,
        (class_id, class_id),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def get_exercise_leaderboard_for_class(conn, class_id, exercise_id):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            u.user_id, u.name, u.email,
            COALESCE(pp.best_score, 0) AS score,
            pp.last_completed_at
        FROM class_enrollments ce
        JOIN users u ON ce.student_id = u.user_id
        LEFT JOIN practice_progress pp
            ON pp.user_id = u.user_id AND pp.class_exercise_id = %s
        WHERE ce.class_id = %s
          AND COALESCE(pp.best_score, 0) > 0
        ORDER BY score DESC, u.name ASC
        """,
        (exercise_id, class_id),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


def ensure_resources_table(conn):
    """Create class_resources table if missing and migrate legacy columns."""
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS class_resources (
            resource_id VARCHAR(255) PRIMARY KEY,
            class_id VARCHAR(255) NOT NULL,
            user_id VARCHAR(255) NOT NULL,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            resource_type VARCHAR(50) NOT NULL,
            resource_url TEXT,
            file_data BYTEA,
            filename VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    columns_to_check = ["user_id", "resource_type", "file_data", "filename"]
    for col in columns_to_check:
        try:
            cur.execute(f"SELECT {col} FROM class_resources LIMIT 1")
        except Exception:
            conn.rollback()
            if col == "user_id":
                cur.execute(
                    f"ALTER TABLE class_resources ADD COLUMN {col} VARCHAR(255) NOT NULL DEFAULT 'admin'"
                )
            elif col == "file_data":
                cur.execute(f"ALTER TABLE class_resources ADD COLUMN {col} BYTEA")
            else:
                cur.execute(f"ALTER TABLE class_resources ADD COLUMN {col} VARCHAR(255)")
            conn.commit()

    try:
        cur.execute("SELECT type FROM class_resources LIMIT 1")
        cur.execute(
            "UPDATE class_resources SET resource_type = type WHERE (resource_type IS NULL OR resource_type = '')"
        )
        cur.execute("ALTER TABLE class_resources DROP COLUMN type")
        conn.commit()
    except Exception:
        conn.rollback()

    conn.commit()
    cur.close()


def get_class_chapters_as_resources(conn, class_id):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT chapter_id, title, description, pdf_url, created_at
        FROM class_chapters
        WHERE class_id = %s
        ORDER BY created_at DESC
        """,
        (class_id,),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def get_class_other_resources(conn, class_id):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT resource_id, title, description, resource_type, resource_url, created_at
        FROM class_resources
        WHERE class_id = %s
        ORDER BY created_at DESC
        """,
        (class_id,),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def insert_resource_link(
    conn, resource_id, class_id, user_id, title, description, resource_type, resource_url
):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO class_resources (resource_id, class_id, user_id, title, description, resource_type, resource_url)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (resource_id, class_id, user_id, title, description, resource_type, resource_url),
    )
    cur.close()


def insert_resource_file(
    conn,
    resource_id,
    class_id,
    user_id,
    title,
    description,
    resource_type,
    resource_url,
    file_data,
    filename,
):
    from psycopg2.extensions import Binary

    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO class_resources
            (resource_id, class_id, user_id, title, description, resource_type, resource_url, file_data, filename)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            resource_id,
            class_id,
            user_id,
            title,
            description,
            resource_type,
            resource_url,
            Binary(file_data),
            filename,
        ),
    )
    cur.close()


def get_resource_file(conn, resource_id):
    """Return (file_data, filename, resource_type) or None."""
    cur = conn.cursor()
    cur.execute(
        "SELECT file_data, filename, resource_type FROM class_resources WHERE resource_id = %s",
        (resource_id,),
    )
    row = cur.fetchone()
    cur.close()
    return row


def delete_resource(conn, resource_id):
    cur = conn.cursor()
    cur.execute("DELETE FROM class_resources WHERE resource_id = %s", (resource_id,))
    cur.close()


def update_resource(conn, resource_id, title, description, resource_type, resource_url):
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE class_resources
        SET title = %s, description = %s, resource_type = %s, resource_url = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE resource_id = %s
        """,
        (title, description, resource_type, resource_url, resource_id),
    )
    cur.close()
