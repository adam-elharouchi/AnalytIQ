"""
Chapters Blueprint — /api/classes/<id>/chapters and /api/chapters/*
"""
import logging
import os
import sys
import uuid
from datetime import datetime

import psycopg2
from flask import Blueprint, Response, g, jsonify, redirect, request, send_from_directory
from werkzeug.utils import secure_filename

import cache
import config
from auth_helpers import require_auth, validate_fields
from blueprints.exercises import ensure_exercises_table
from db import close_conn_safely, get_db_connection
from extensions import csrf_exempt

logger = logging.getLogger(__name__)
bp = Blueprint("chapters", __name__)

# Add python directory to path for PDF processor and exercise generator
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
try:
    from pdf_processor import extract_text_from_pdf_bytes
except ImportError:
    print("Warning: PDF processor not available. PDF uploads will not work.")
    extract_text_from_pdf_bytes = None

try:
    from exercise_generator import generate_exercises_from_pdf_content
except ImportError:
    print("Warning: Exercise generator not available. Exercise generation will not work.")
    generate_exercises_from_pdf_content = None

ALLOWED_EXTENSIONS = {"pdf", "csv", "xlsx", "xls", "json", "txt", "ipynb"}


def allowed_file(filename):
    """Check if file extension is allowed"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_pdf_file(file):
    """
    Comprehensive PDF file validation without external dependencies.
    Returns (is_valid, error_message)
    """
    MAX_PDF_SIZE = 50 * 1024 * 1024  # 50MB
    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)

    if file_size > MAX_PDF_SIZE:
        logger.warning(
            "File upload rejected: too large", extra={"size_mb": file_size / 1024 / 1024}
        )
        return False, f"File too large: {file_size / 1024 / 1024:.1f}MB (max 50MB)"

    if file_size == 0:
        logger.warning("File upload rejected: empty file")
        return False, "File is empty"

    try:
        file_header = file.read(1024)
        file.seek(0)

        if not file_header.startswith(b"%PDF-"):
            logger.warning("File upload rejected: invalid PDF header")
            return False, "Invalid PDF: file does not start with PDF header"

        valid_versions = [b"%PDF-1." + bytes([i]) for i in range(ord("0"), ord("8"))] + [
            b"%PDF-2.0"
        ]
        if not any(file_header.startswith(version) for version in valid_versions):
            logger.warning("File upload rejected: unsupported PDF version")
            return False, "Unsupported PDF version (must be 1.0-1.7 or 2.0)"

        suspicious_patterns = [
            b"/JavaScript",
            b"/JS",
            b"/Launch",
            b"/EmbeddedFile",
        ]

        file.seek(0)
        sample_content = file.read(10240)
        file.seek(0)

        for pattern in suspicious_patterns:
            if pattern in sample_content:
                logger.warning(
                    "File upload rejected: suspicious content",
                    extra={"pattern": pattern.decode("utf-8", errors="ignore")},
                )
                return False, "PDF contains potentially unsafe content"

    except Exception as e:
        logger.error("PDF validation error", extra={"error": str(e)})
        return False, f"PDF validation error: {str(e)}"

    logger.info("PDF validation passed", extra={"size_mb": file_size / 1024 / 1024})
    return True, None


@bp.route("/api/classes/<class_id>/chapters", methods=["POST"])
@csrf_exempt
@require_auth
def upload_chapter(class_id):
    """Upload PDF and create chapter for a class (professor only)"""
    try:
        user_id = g.user_id
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT professor_id FROM classes WHERE class_id = %s", (class_id,))
        class_data = cursor.fetchone()
        if not class_data:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Class not found"}), 404

        if class_data[0] != user_id:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Only the class owner can upload chapters"}), 403

        if "pdf_file" not in request.files:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "No PDF file provided"}), 400

        file = request.files["pdf_file"]
        if file.filename == "":
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "No file selected"}), 400

        if not allowed_file(file.filename):
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Invalid file type. Only PDF files are allowed."}), 400

        is_valid, error_message = validate_pdf_file(file)
        if not is_valid:
            cursor.close()
            close_conn_safely(conn)
            logger.warning(
                "PDF upload rejected",
                extra={
                    "filename": file.filename,
                    "error": error_message,
                    "user_id": user_id,
                    "class_id": class_id,
                },
            )
            return jsonify({"error": error_message}), 400

        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        exercise_mode = request.form.get("exercise_mode", "auto")

        if not title:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Chapter title is required"}), 400

        file_bytes = file.read()
        chapter_id = f"{class_id}_{int(datetime.now().timestamp() * 1000)}"
        filename = secure_filename(file.filename)
        pdf_filename = f"{chapter_id}_{filename}"
        pdf_url = f"/api/chapters/{chapter_id}/pdf"

        pdf_text = None
        if extract_text_from_pdf_bytes:
            try:
                pdf_text = extract_text_from_pdf_bytes(file_bytes)
            except Exception as e:
                print(f"Warning: Could not extract text from PDF: {e}")
                pdf_text = None

        cursor.execute(
            """
            SELECT COALESCE(MAX(chapter_number), 0) + 1
            FROM class_chapters
            WHERE class_id = %s
        """,
            (class_id,),
        )
        chapter_number = cursor.fetchone()[0] or 1

        cursor.execute(
            """
            INSERT INTO class_chapters (chapter_id, class_id, title, description, chapter_number, pdf_url, pdf_filename, pdf_data)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING chapter_id, title, description, chapter_number, created_at
        """,
            (
                chapter_id,
                class_id,
                title,
                description,
                chapter_number,
                pdf_url,
                pdf_filename,
                psycopg2.Binary(file_bytes),
            ),
        )

        chapter_data = cursor.fetchone()
        chapter_id_result = chapter_data[0]
        chapter_title_result = chapter_data[1]

        exercises_generated = 0
        if exercise_mode == "auto" and pdf_text and generate_exercises_from_pdf_content:
            try:
                api_key = os.getenv("GEMINI_API_KEY")
                if not api_key:
                    raise ValueError("GEMINI_API_KEY not set")
                exercises = generate_exercises_from_pdf_content(
                    pdf_text, chapter_title_result, api_key
                )

                if exercises:
                    for idx, exercise in enumerate(exercises, 1):
                        exercise_id = (
                            f"{chapter_id_result}_ex_{idx}_{int(datetime.now().timestamp() * 1000)}"
                        )
                        cursor.execute(
                            """
                            INSERT INTO class_exercises (exercise_id, chapter_id, class_id, title, description, difficulty, solution_code, exercise_number)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                            (
                                exercise_id,
                                chapter_id_result,
                                class_id,
                                exercise["title"],
                                exercise["description"],
                                exercise["difficulty"],
                                exercise["solution_code"],
                                idx,
                            ),
                        )
                    exercises_generated = len(exercises)
                    conn.commit()
            except Exception as e:
                print(f"Warning: Could not generate exercises: {e}")
                exercises_generated = 0

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        return (
            jsonify(
                {
                    "chapter_id": chapter_id_result,
                    "title": chapter_title_result,
                    "description": chapter_data[2],
                    "chapter_number": chapter_data[3],
                    "created_at": chapter_data[4].isoformat() if chapter_data[4] else None,
                    "pdf_url": pdf_url,
                    "pdf_text_extracted": pdf_text is not None,
                    "exercise_mode": exercise_mode,
                    "exercises_generated": exercises_generated,
                    "success": True,
                }
            ),
            201,
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/classes/<class_id>/chapters", methods=["GET"])
@require_auth
def get_class_chapters(class_id):
    """Get all chapters for a class"""
    try:
        user_id = g.user_id
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT professor_id FROM classes WHERE class_id = %s", (class_id,))
        class_data = cursor.fetchone()
        if not class_data:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Class not found"}), 404

        role = getattr(g, "user_role", None) or "student"
        is_professor = role == "professor"
        is_owner = class_data[0] == user_id

        if not is_owner and not is_professor:
            cursor.execute(
                """
                SELECT 1 FROM class_enrollments
                WHERE class_id = %s AND student_id = %s
            """,
                (class_id, user_id),
            )
            if not cursor.fetchone():
                cursor.close()
                close_conn_safely(conn)
                return jsonify({"error": "Access denied"}), 403

        cursor.execute(
            """
            SELECT chapter_id, title, description, chapter_number, pdf_url, pdf_filename, created_at
            FROM class_chapters
            WHERE class_id = %s
            ORDER BY chapter_number ASC
        """,
            (class_id,),
        )

        chapters = []
        for row in cursor.fetchall():
            chapters.append(
                {
                    "chapter_id": row[0],
                    "title": row[1],
                    "description": row[2],
                    "chapter_number": row[3],
                    "pdf_url": row[4],
                    "pdf_filename": row[5],
                    "created_at": row[6].isoformat() if row[6] else None,
                }
            )

        cursor.close()
        close_conn_safely(conn)

        return jsonify({"chapters": chapters}), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/chapters/<chapter_id>", methods=["PUT"])
@csrf_exempt
@require_auth
def update_chapter(chapter_id):
    """Update a chapter"""
    try:
        data = request.json or {}
        user_id = g.user_id

        errors = validate_fields(data, [
            ("title", False, config.MAX_CHAPTER_TITLE_LENGTH),
            ("description", False, config.MAX_CLASS_DESCRIPTION_LENGTH),
        ])
        if errors:
            return jsonify({"error": errors[0]}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT c.professor_id
            FROM class_chapters ch
            JOIN classes c ON ch.class_id = c.class_id
            WHERE ch.chapter_id = %s
        """,
            (chapter_id,),
        )

        result = cursor.fetchone()
        if not result:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Chapter not found"}), 404

        if result[0] != user_id:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Unauthorized"}), 403

        cursor.execute(
            """
            UPDATE class_chapters
            SET title = %s, description = %s, updated_at = CURRENT_TIMESTAMP
            WHERE chapter_id = %s
        """,
            (data.get("title"), data.get("description"), chapter_id),
        )

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/chapters/<chapter_id>", methods=["DELETE"])
@csrf_exempt
@require_auth
def delete_chapter(chapter_id):
    """Delete a chapter and all its exercises (professor only)"""
    try:
        user_id = g.user_id
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT cc.class_id, cc.pdf_filename, c.professor_id
            FROM class_chapters cc
            JOIN classes c ON cc.class_id = c.class_id
            WHERE cc.chapter_id = %s
        """,
            (chapter_id,),
        )
        chapter_data = cursor.fetchone()

        if not chapter_data:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Chapter not found"}), 404

        professor_id = chapter_data[2]

        if professor_id != user_id:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Only the class owner can delete chapters"}), 403

        cursor.execute("DELETE FROM class_exercises WHERE chapter_id = %s", (chapter_id,))
        cursor.execute("DELETE FROM class_chapters WHERE chapter_id = %s", (chapter_id,))

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        return jsonify({"success": True, "message": "Chapter deleted successfully"}), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/chapters/<chapter_id>/generate-exercises", methods=["POST"])
@csrf_exempt
@require_auth
def generate_exercises_for_chapter(chapter_id):
    """Generate exercises from an existing chapter's PDF data"""
    try:
        data = request.get_json() or {}
        user_id = g.user_id

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT cc.pdf_data, cc.title, cc.class_id, c.professor_id
            FROM class_chapters cc
            JOIN classes c ON cc.class_id = c.class_id
            WHERE cc.chapter_id = %s
        """,
            (chapter_id,),
        )

        result = cursor.fetchone()
        if not result:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Chapter not found"}), 404

        pdf_data, chapter_title, class_id, professor_id = result

        if professor_id != user_id:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Only the class professor can generate exercises"}), 403

        if not pdf_data:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "PDF data not found for this chapter"}), 404

        if not extract_text_from_pdf_bytes:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "PDF processor not available"}), 500

        try:
            pdf_text = extract_text_from_pdf_bytes(bytes(pdf_data))
        except Exception as e:
            cursor.close()
            close_conn_safely(conn)
            logger.error("Failed to extract text from PDF: %s", e, exc_info=True)
            return jsonify({"error": "Failed to extract text from the PDF. Please check the file and try again."}), 500

        if not pdf_text:
            cursor.close()
            close_conn_safely(conn)
            return (
                jsonify(
                    {"error": "Could not extract text from PDF. PDF may be empty or image-based."}
                ),
                400,
            )

        if not generate_exercises_from_pdf_content:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Exercise generator not available"}), 500

        try:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not set")
            exercises = generate_exercises_from_pdf_content(pdf_text, chapter_title, api_key)
        except Exception as e:
            cursor.close()
            close_conn_safely(conn)
            logger.error("Failed to generate exercises: %s", e, exc_info=True)
            return jsonify({"error": "Failed to generate exercises. Please try again."}), 500

        if not exercises:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "No exercises were generated"}), 400

        exercises_generated = 0
        for idx, exercise in enumerate(exercises, 1):
            exercise_id = f"{chapter_id}_ex_{idx}_{int(datetime.now().timestamp() * 1000)}"
            cursor.execute(
                """
                INSERT INTO class_exercises (exercise_id, chapter_id, class_id, title, description, difficulty, solution_code, exercise_number)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
                (
                    exercise_id,
                    chapter_id,
                    class_id,
                    exercise["title"],
                    exercise["description"],
                    exercise["difficulty"],
                    exercise["solution_code"],
                    idx,
                ),
            )
            exercises_generated += 1

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        return (
            jsonify(
                {
                    "success": True,
                    "exercises_generated": exercises_generated,
                    "chapter_id": chapter_id,
                }
            ),
            201,
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/chapters/<chapter_id>/exercises", methods=["GET"])
@require_auth
def get_chapter_exercises(chapter_id):
    """Get all exercises for a chapter"""
    try:
        user_id = g.user_id
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT cc.class_id, c.professor_id
            FROM class_chapters cc
            JOIN classes c ON cc.class_id = c.class_id
            WHERE cc.chapter_id = %s
        """,
            (chapter_id,),
        )
        chapter_data = cursor.fetchone()
        if not chapter_data:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Chapter not found"}), 404

        class_id_result = chapter_data[0]
        professor_id = chapter_data[1]

        role = getattr(g, "user_role", None) or "student"
        is_professor = role == "professor"
        is_owner = professor_id == user_id

        if not is_owner and not is_professor:
            cursor.execute(
                """
                SELECT 1 FROM class_enrollments
                WHERE class_id = %s AND student_id = %s
            """,
                (class_id_result, user_id),
            )
            if not cursor.fetchone():
                cursor.close()
                close_conn_safely(conn)
                return jsonify({"error": "Access denied"}), 403

        cursor.execute(
            """
            SELECT exercise_id, title, description, difficulty, exercise_number, created_at, solution_code
            FROM class_exercises
            WHERE chapter_id = %s
            ORDER BY exercise_number ASC
        """,
            (chapter_id,),
        )

        exercises = []
        for row in cursor.fetchall():
            exercises.append(
                {
                    "exercise_id": row[0],
                    "title": row[1],
                    "description": row[2],
                    "difficulty": row[3],
                    "exercise_number": row[4],
                    "created_at": row[5].isoformat() if row[5] else None,
                    "solution_code": row[6] or "",
                }
            )

        cursor.close()
        close_conn_safely(conn)

        return jsonify({"exercises": exercises}), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/classes/<class_id>/chapters/<chapter_id>/exercises", methods=["POST"])
@csrf_exempt
@require_auth
def create_exercise(class_id, chapter_id):
    """Manually create a new exercise"""
    try:
        ensure_exercises_table()

        if request.content_type and "multipart/form-data" in request.content_type:
            data = request.form
        else:
            data = request.json or {}

        user_id = g.user_id

        errors = validate_fields(data, [
            ("title", False, config.MAX_EXERCISE_TITLE_LENGTH),
            ("description", False, config.MAX_EXERCISE_DESCRIPTION_LENGTH),
            ("solution_code", False, config.MAX_SOLUTION_CODE_LENGTH),
        ])
        if errors:
            return jsonify({"error": errors[0]}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT c.professor_id
            FROM classes c
            WHERE c.class_id = %s
        """,
            (class_id,),
        )

        result = cursor.fetchone()
        if not result:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Class not found"}), 404

        professor_id = result[0]

        if professor_id != user_id:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Unauthorized"}), 403

        cursor.execute(
            "SELECT 1 FROM class_chapters WHERE chapter_id = %s AND class_id = %s",
            (chapter_id, class_id),
        )
        if not cursor.fetchone():
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Chapter not found in this class"}), 404

        exercise_id = f"ex_{str(uuid.uuid4())[:8]}"

        cursor.execute(
            """
            INSERT INTO class_exercises (
                exercise_id, class_id, chapter_id, title, description,
                difficulty, solution_code, created_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
            (
                exercise_id,
                class_id,
                chapter_id,
                data.get("title"),
                data.get("description"),
                data.get("difficulty", "medium"),
                data.get("solution_code", ""),
                user_id,
            ),
        )

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        return jsonify({"success": True, "exercise_id": exercise_id}), 201

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/chapters/<chapter_id>/pdf", methods=["GET"])
def serve_chapter_pdf(chapter_id):
    """Serve PDF file from database binary storage or filesystem (backward compatibility)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT pdf_data, pdf_filename, pdf_url
            FROM class_chapters
            WHERE chapter_id = %s
        """,
            (chapter_id,),
        )

        result = cursor.fetchone()
        cursor.close()
        close_conn_safely(conn)

        if not result:
            return jsonify({"error": "Chapter not found"}), 404

        pdf_data = result[0]
        pdf_filename = result[1] or "chapter.pdf"
        pdf_url = result[2]

        self_ref = f"/api/chapters/{chapter_id}/pdf"
        if pdf_url and pdf_url.rstrip("/") == self_ref.rstrip("/"):
            pdf_url = None

        if pdf_url:
            return redirect(pdf_url)

        if pdf_data:
            pdf_bytes = bytes(pdf_data)
            from flask import current_app
            origin = request.headers.get("Origin", "")
            allowed = config.CORS_ORIGINS
            cors_origin = "*" if "*" in allowed else (origin if origin in allowed else None)

            response = Response(pdf_bytes, mimetype="application/pdf")
            response.headers["Content-Disposition"] = (
                f'inline; filename="{pdf_filename}"'
            )
            if cors_origin:
                response.headers["Access-Control-Allow-Origin"] = cors_origin
            return response

        elif pdf_filename:
            from flask import current_app
            upload_folder = current_app.config.get("UPLOAD_FOLDER", "uploads")
            pdf_path = os.path.join(upload_folder, pdf_filename)
            if os.path.exists(pdf_path):
                origin = request.headers.get("Origin", "")
                allowed = config.CORS_ORIGINS
                cors_origin = "*" if "*" in allowed else (origin if origin in allowed else None)
                response = send_from_directory(upload_folder, pdf_filename)
                if cors_origin:
                    response.headers["Access-Control-Allow-Origin"] = cors_origin
                return response
            else:
                return jsonify({"error": f"PDF file not found: {pdf_filename}"}), 404

    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500
