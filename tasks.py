"""
Celery Tasks for AnalytIQ
Async tasks for PDF processing, exercise generation, and email sending
"""

import logging
import os
import sys
from celery import Task
from celery_app import celery_app
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Add python directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "python"))

# Import PDF processor and exercise generator
try:
    from pdf_processor import extract_text_from_pdf_bytes
except ImportError:
    extract_text_from_pdf_bytes = None

try:
    from exercise_generator import generate_exercises_from_pdf_content
except ImportError:
    generate_exercises_from_pdf_content = None

# Import Flask-Mail for email
try:
    from flask_mail import Message
except ImportError:
    Message = None


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
    Send email asynchronously

    Args:
        recipient: Email recipient
        subject: Email subject
        body: Email body (HTML)

    Returns:
        dict: {'success': bool, 'recipient': str}
    """
    try:
        # Import Flask app and mail
        from app import app, mail

        if not mail:
            return {"success": False, "error": "Flask-Mail not configured", "recipient": recipient}

        with app.app_context():
            msg = Message(subject=subject, recipients=[recipient], html=body)
            mail.send(msg)

        return {"success": True, "recipient": recipient}

    except Exception as e:
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
