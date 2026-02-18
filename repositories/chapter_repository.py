"""
Chapter Repository — SQL operations for chapters, PDF storage, and exercise generation inserts.

Every function receives a DB *connection* and returns plain Python data.
The caller (blueprint) is responsible for commit / rollback / connection lifecycle.
"""

import logging

import psycopg2

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Chapter CRUD
# ---------------------------------------------------------------------------

def get_next_chapter_number(conn, class_id):
    """Return the next chapter_number for a class."""
    cur = conn.cursor()
    cur.execute(
        "SELECT COALESCE(MAX(chapter_number), 0) + 1 FROM class_chapters WHERE class_id = %s",
        (class_id,),
    )
    num = cur.fetchone()[0] or 1
    cur.close()
    return num


def insert_chapter(conn, chapter_id, class_id, title, description, chapter_number, pdf_url, pdf_filename, file_bytes):
    """Insert a new chapter with binary PDF data.  Returns the RETURNING tuple."""
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO class_chapters
            (chapter_id, class_id, title, description, chapter_number, pdf_url, pdf_filename, pdf_data)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING chapter_id, title, description, chapter_number, created_at
        """,
        (
            chapter_id, class_id, title, description,
            chapter_number, pdf_url, pdf_filename,
            psycopg2.Binary(file_bytes),
        ),
    )
    row = cur.fetchone()
    cur.close()
    return row


def insert_exercise(conn, exercise_id, chapter_id, class_id, title, description, difficulty, solution_code, exercise_number):
    """Insert a single exercise row (used during auto-generation from PDF)."""
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO class_exercises
            (exercise_id, chapter_id, class_id, title, description, difficulty, solution_code, exercise_number)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (exercise_id, chapter_id, class_id, title, description, difficulty, solution_code, exercise_number),
    )
    cur.close()


def get_class_chapters(conn, class_id):
    """Return all chapters for a class ordered by chapter_number."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT chapter_id, title, description, chapter_number, pdf_url, pdf_filename, created_at
        FROM class_chapters
        WHERE class_id = %s
        ORDER BY chapter_number ASC
        """,
        (class_id,),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def get_chapter_owner(conn, chapter_id):
    """Return professor_id for the class that owns this chapter, or None."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT c.professor_id
        FROM class_chapters ch
        JOIN classes c ON ch.class_id = c.class_id
        WHERE ch.chapter_id = %s
        """,
        (chapter_id,),
    )
    row = cur.fetchone()
    cur.close()
    return row[0] if row else None


def update_chapter(conn, chapter_id, title, description):
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE class_chapters
        SET title = %s, description = %s, updated_at = CURRENT_TIMESTAMP
        WHERE chapter_id = %s
        """,
        (title, description, chapter_id),
    )
    cur.close()


def get_chapter_for_delete(conn, chapter_id):
    """Return (class_id, pdf_filename, professor_id) or None."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT cc.class_id, cc.pdf_filename, c.professor_id
        FROM class_chapters cc
        JOIN classes c ON cc.class_id = c.class_id
        WHERE cc.chapter_id = %s
        """,
        (chapter_id,),
    )
    row = cur.fetchone()
    cur.close()
    return row


def delete_chapter_and_exercises(conn, chapter_id):
    """Delete a chapter and its exercises."""
    cur = conn.cursor()
    cur.execute("DELETE FROM class_exercises WHERE chapter_id = %s", (chapter_id,))
    cur.execute("DELETE FROM class_chapters WHERE chapter_id = %s", (chapter_id,))
    cur.close()


# ---------------------------------------------------------------------------
# Exercise generation from existing chapter
# ---------------------------------------------------------------------------

def get_chapter_pdf_data(conn, chapter_id):
    """Return (pdf_data, title, class_id, professor_id) or None."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT cc.pdf_data, cc.title, cc.class_id, c.professor_id
        FROM class_chapters cc
        JOIN classes c ON cc.class_id = c.class_id
        WHERE cc.chapter_id = %s
        """,
        (chapter_id,),
    )
    row = cur.fetchone()
    cur.close()
    return row


# ---------------------------------------------------------------------------
# Chapter exercises listing
# ---------------------------------------------------------------------------

def get_chapter_class_info(conn, chapter_id):
    """Return (class_id, professor_id) for the chapter, or None."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT cc.class_id, c.professor_id
        FROM class_chapters cc
        JOIN classes c ON cc.class_id = c.class_id
        WHERE cc.chapter_id = %s
        """,
        (chapter_id,),
    )
    row = cur.fetchone()
    cur.close()
    return row


def get_chapter_exercises(conn, chapter_id):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT exercise_id, title, description, difficulty, exercise_number, created_at, solution_code
        FROM class_exercises
        WHERE chapter_id = %s
        ORDER BY exercise_number ASC
        """,
        (chapter_id,),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def chapter_belongs_to_class(conn, chapter_id, class_id):
    """Return True if chapter exists in the given class."""
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM class_chapters WHERE chapter_id = %s AND class_id = %s",
        (chapter_id, class_id),
    )
    exists = cur.fetchone() is not None
    cur.close()
    return exists


def insert_manual_exercise(conn, exercise_id, class_id, chapter_id, title, description, difficulty, solution_code, created_by):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO class_exercises
            (exercise_id, class_id, chapter_id, title, description, difficulty, solution_code, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (exercise_id, class_id, chapter_id, title, description, difficulty, solution_code, created_by),
    )
    cur.close()


# ---------------------------------------------------------------------------
# PDF serving
# ---------------------------------------------------------------------------

def get_chapter_pdf(conn, chapter_id):
    """Return (pdf_data, pdf_filename, pdf_url) or None."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT pdf_data, pdf_filename, pdf_url
        FROM class_chapters
        WHERE chapter_id = %s
        """,
        (chapter_id,),
    )
    row = cur.fetchone()
    cur.close()
    return row
