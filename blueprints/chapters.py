"""
Chapters Blueprint — /api/classes/<id>/chapters and /api/chapters/*
"""
import logging
import os
import sys
import uuid
from datetime import datetime

from flask import Blueprint, Response, g, jsonify, redirect, request, send_from_directory
from werkzeug.utils import secure_filename

import cache
import config
import supabase_storage
from audit import audit
from auth_helpers import require_auth, validate_fields
from db import get_db_connection
from extensions import csrf_exempt
from repositories import chapter_repository as chapter_repo
from repositories import class_repository as class_repo

logger = logging.getLogger(__name__)
bp = Blueprint("chapters", __name__)

# Add python directory to path for content extractor and exercise generator
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
try:
    import content_extractor
except ImportError:
    logger.warning("Content extractor not available. File text extraction will not work.")
    content_extractor = None

try:
    from exercise_generator import generate_exercises_from_pdf_content
except ImportError:
    logger.warning("Exercise generator not available. Exercise generation will not work.")
    generate_exercises_from_pdf_content = None

ALLOWED_EXTENSIONS = config.ALLOWED_EXTENSIONS


def allowed_file(filename):
    """Check if file extension is allowed"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_pdf_file(file):
    """
    Comprehensive PDF file validation without external dependencies.
    Returns (is_valid, error_message)
    """
    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)

    if file_size > config.MAX_PDF_SIZE_BYTES:
        logger.warning(
            "File upload rejected: too large", extra={"size_mb": file_size / 1024 / 1024}
        )
        return False, f"File too large: {file_size / 1024 / 1024:.1f}MB (max {config.MAX_PDF_SIZE_MB}MB)"

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

    except Exception:
        logger.error("PDF validation error", exc_info=True)
        return False, "PDF validation error"

    logger.info("PDF validation passed", extra={"size_mb": file_size / 1024 / 1024})
    return True, None


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _auto_generate_exercises(conn, pdf_text, chapter_id, chapter_title, class_id):
    """Generate exercises from chapter text. Returns count generated (0 on any failure)."""
    if not pdf_text or not generate_exercises_from_pdf_content:
        return 0
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set")
        exercises = generate_exercises_from_pdf_content(pdf_text, chapter_title, api_key)
        if not exercises:
            return 0
        for idx, exercise in enumerate(exercises, 1):
            exercise_id = f"{chapter_id}_ex_{idx}_{int(datetime.now().timestamp() * 1000)}"
            chapter_repo.insert_exercise(
                conn,
                exercise_id,
                chapter_id,
                class_id,
                exercise["title"],
                exercise["description"],
                exercise["difficulty"],
                exercise["solution_code"],
                idx,
            )
        conn.commit()
        return len(exercises)
    except Exception as e:
        logger.warning("Could not generate exercises: %s", e)
        return 0


def _get_cors_origin(req):
    """Return the appropriate CORS origin header value for a file response, or None."""
    origin = req.headers.get("Origin", "")
    allowed = config.CORS_ORIGINS
    if "*" in allowed:
        return "*"
    return origin if origin in allowed else None


@bp.route("/api/chapters/upload-url", methods=["GET"])
@require_auth
def get_chapter_upload_url():
    """Return a Supabase presigned upload URL for direct browser-to-Supabase PDF upload."""
    try:
        filename = request.args.get("filename", "upload.pdf")
        safe_name = secure_filename(filename) or "upload.pdf"
        storage_path = f"chapters/{uuid.uuid4().hex[:8]}_{safe_name}"

        signed = supabase_storage.get_presigned_upload_url(storage_path)
        if not signed:
            return jsonify({"error": "Storage service unavailable"}), 503

        return (
            jsonify(
                {
                    "upload_url": signed.get("signedURL") or signed.get("signed_url"),
                    "storage_path": storage_path,
                }
            ),
            200,
        )

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


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

        owner = class_repo.get_class_owner(conn, class_id)
        if owner is None:
            return jsonify({"error": "Class not found"}), 404
        if owner != user_id:
            return jsonify({"error": "Only the class owner can upload chapters"}), 403

        if "pdf_file" not in request.files:
            return jsonify({"error": "No PDF file provided"}), 400

        file = request.files["pdf_file"]
        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        if not allowed_file(file.filename):
            return jsonify({"error": "Invalid file type. Allowed: pdf, txt, csv, ipynb, docx"}), 400

        # PDF-specific security validation (magic bytes + suspicious pattern scan)
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if ext == "pdf":
            is_valid, error_message = validate_pdf_file(file)
            if not is_valid:
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
            return jsonify({"error": "Chapter title is required"}), 400

        file_bytes = file.read()
        chapter_id = f"{class_id}_{int(datetime.now().timestamp() * 1000)}"
        filename = secure_filename(file.filename)
        pdf_filename = f"{chapter_id}_{filename}"
        pdf_url = f"/api/chapters/{chapter_id}/pdf"

        pdf_text = None
        if content_extractor:
            try:
                pdf_text = content_extractor.extract_text(file_bytes, filename)
            except ValueError as e:
                logger.warning("Content extraction rejected: %s", e)
                return jsonify({"error": "Content extraction failed. Please try a different file."}), 400
            except Exception as e:
                logger.warning("Could not extract text from file: %s", e)
                pdf_text = None

        chapter_number = chapter_repo.get_next_chapter_number(conn, class_id)
        chapter_data = chapter_repo.insert_chapter(
            conn,
            chapter_id,
            class_id,
            title,
            description,
            chapter_number,
            pdf_url,
            pdf_filename,
            file_bytes,
        )

        chapter_id_result = chapter_data[0]
        chapter_title_result = chapter_data[1]

        audit(
            conn,
            "CREATE_CHAPTER",
            resource_type="chapter",
            resource_id=chapter_id_result,
            details={"class_id": class_id},
        )
        exercises_generated = 0
        if exercise_mode == "auto":
            exercises_generated = _auto_generate_exercises(
                conn, pdf_text, chapter_id_result, chapter_title_result, class_id
            )

        conn.commit()

        cache.invalidate_cache(f"chapters:*:{class_id}")

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
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/classes/<class_id>/chapters", methods=["GET"])
@require_auth
@cache.cache_response(ttl=60, key_prefix="chapters")
def get_class_chapters(class_id):
    """Get all chapters for a class"""
    try:
        user_id = g.user_id
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        conn = get_db_connection()

        owner = class_repo.get_class_owner(conn, class_id)
        if owner is None:
            return jsonify({"error": "Class not found"}), 404

        role = getattr(g, "user_role", None) or "student"
        is_professor = role == "professor"
        is_owner = owner == user_id

        if not is_owner and not is_professor:
            if not class_repo.check_enrollment(conn, class_id, user_id):
                return jsonify({"error": "Access denied"}), 403

        rows = chapter_repo.get_class_chapters(conn, class_id)

        chapters = [
            {
                "chapter_id": row[0],
                "title": row[1],
                "description": row[2],
                "chapter_number": row[3],
                "pdf_url": row[4],
                "pdf_filename": row[5],
                "created_at": row[6].isoformat() if row[6] else None,
            }
            for row in rows
        ]

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

        errors = validate_fields(
            data,
            [
                ("title", False, config.MAX_CHAPTER_TITLE_LENGTH),
                ("description", False, config.MAX_CLASS_DESCRIPTION_LENGTH),
            ],
        )
        if errors:
            return jsonify({"error": errors[0]}), 400

        conn = get_db_connection()

        chapter_data = chapter_repo.get_chapter_for_delete(conn, chapter_id)
        if chapter_data is None:
            return jsonify({"error": "Chapter not found"}), 404
        class_id, _, professor_id = chapter_data
        if professor_id != user_id:
            return jsonify({"error": "Unauthorized"}), 403

        chapter_repo.update_chapter(conn, chapter_id, data.get("title"), data.get("description"))
        conn.commit()

        cache.invalidate_cache(f"chapters:*:{class_id}")
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

        chapter_data = chapter_repo.get_chapter_for_delete(conn, chapter_id)
        if not chapter_data:
            return jsonify({"error": "Chapter not found"}), 404

        class_id = chapter_data[0]
        professor_id = chapter_data[2]
        if professor_id != user_id:
            return jsonify({"error": "Only the class owner can delete chapters"}), 403

        chapter_repo.delete_chapter_and_exercises(conn, chapter_id)
        audit(
            conn,
            "DELETE_CHAPTER",
            resource_type="chapter",
            resource_id=chapter_id,
            details={"class_id": class_id},
        )
        conn.commit()

        cache.invalidate_cache(f"chapters:*:{class_id}")
        cache.invalidate_cache(f"chap_exercises:*:{chapter_id}")
        return jsonify({"success": True, "message": "Chapter deleted successfully"}), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/chapters/<chapter_id>/generate-exercises", methods=["POST"])
@csrf_exempt
@require_auth
def generate_exercises_for_chapter(chapter_id):
    """Generate exercises from an existing chapter's PDF data"""
    try:
        user_id = g.user_id
        conn = get_db_connection()

        result = chapter_repo.get_chapter_pdf_data(conn, chapter_id)
        if not result:
            return jsonify({"error": "Chapter not found"}), 404

        pdf_data, chapter_title, class_id, professor_id = result

        if professor_id != user_id:
            return jsonify({"error": "Only the class professor can generate exercises"}), 403

        if not pdf_data:
            return jsonify({"error": "PDF data not found for this chapter"}), 404

        if not content_extractor:
            return jsonify({"error": "Content extractor not available"}), 500

        try:
            pdf_text = content_extractor.extract_text(bytes(pdf_data), "chapter.pdf")
        except Exception as e:
            logger.error("Failed to extract text from chapter file: %s", e, exc_info=True)
            return (
                jsonify(
                    {
                        "error": "Failed to extract text from the file. Please check the file and try again."
                    }
                ),
                500,
            )

        if not pdf_text:
            return (
                jsonify(
                    {"error": "Could not extract text from PDF. PDF may be empty or image-based."}
                ),
                400,
            )

        if not generate_exercises_from_pdf_content:
            return jsonify({"error": "Exercise generator not available"}), 500

        try:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not set")
            exercises = generate_exercises_from_pdf_content(pdf_text, chapter_title, api_key)
        except Exception as e:
            logger.error("Failed to generate exercises: %s", e, exc_info=True)
            return jsonify({"error": "Failed to generate exercises. Please try again."}), 500

        if not exercises:
            return jsonify({"error": "No exercises were generated"}), 400

        exercises_generated = 0
        for idx, exercise in enumerate(exercises, 1):
            exercise_id = f"{chapter_id}_ex_{idx}_{int(datetime.now().timestamp() * 1000)}"
            chapter_repo.insert_exercise(
                conn,
                exercise_id,
                chapter_id,
                class_id,
                exercise["title"],
                exercise["description"],
                exercise["difficulty"],
                exercise["solution_code"],
                idx,
            )
            exercises_generated += 1

        conn.commit()

        cache.invalidate_cache(f"chap_exercises:*:{chapter_id}")

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
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/chapters/<chapter_id>/exercises", methods=["GET"])
@require_auth
@cache.cache_response(ttl=60, key_prefix="chap_exercises")
def get_chapter_exercises(chapter_id):
    """Get all exercises for a chapter"""
    try:
        user_id = g.user_id
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        conn = get_db_connection()

        chapter_info = chapter_repo.get_chapter_class_info(conn, chapter_id)
        if not chapter_info:
            return jsonify({"error": "Chapter not found"}), 404

        class_id_result = chapter_info[0]
        professor_id = chapter_info[1]

        role = getattr(g, "user_role", None) or "student"
        is_professor = role == "professor"
        is_owner = professor_id == user_id

        if not is_owner and not is_professor:
            if not class_repo.check_enrollment(conn, class_id_result, user_id):
                return jsonify({"error": "Access denied"}), 403

        rows = chapter_repo.get_chapter_exercises(conn, chapter_id)

        exercises = [
            {
                "exercise_id": row[0],
                "title": row[1],
                "description": row[2],
                "difficulty": row[3],
                "exercise_number": row[4],
                "created_at": row[5].isoformat() if row[5] else None,
                "solution_code": row[6] or "",
            }
            for row in rows
        ]

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
        conn = get_db_connection()

        if request.content_type and "multipart/form-data" in request.content_type:
            data = request.form
        else:
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

        owner = class_repo.get_class_owner(conn, class_id)
        if owner is None:
            return jsonify({"error": "Class not found"}), 404
        if owner != user_id:
            return jsonify({"error": "Unauthorized"}), 403

        if not chapter_repo.chapter_belongs_to_class(conn, chapter_id, class_id):
            return jsonify({"error": "Chapter not found in this class"}), 404

        exercise_id = f"ex_{str(uuid.uuid4())[:8]}"

        chapter_repo.insert_manual_exercise(
            conn,
            exercise_id,
            class_id,
            chapter_id,
            data.get("title"),
            data.get("description"),
            data.get("difficulty", "medium"),
            data.get("solution_code", ""),
            user_id,
        )
        conn.commit()

        cache.invalidate_cache(f"chap_exercises:*:{chapter_id}")
        return jsonify({"success": True, "exercise_id": exercise_id}), 201

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/chapters/<chapter_id>/pdf", methods=["GET"])
def serve_chapter_pdf(chapter_id):
    """Serve PDF file from database binary storage or filesystem (backward compatibility)"""
    try:
        conn = get_db_connection()
        result = chapter_repo.get_chapter_pdf(conn, chapter_id)

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
            # Imported HTML chapters are stored with a .html extension
            if pdf_filename and pdf_filename.lower().endswith(".html"):
                mimetype = "text/html; charset=utf-8"
            else:
                mimetype = "application/pdf"
            response = Response(pdf_bytes, mimetype=mimetype)
            response.headers["Content-Disposition"] = f'inline; filename="{pdf_filename}"'
            cors_origin = _get_cors_origin(request)
            if cors_origin:
                response.headers["Access-Control-Allow-Origin"] = cors_origin
            return response

        elif pdf_filename:
            from flask import current_app

            upload_folder = current_app.config.get("UPLOAD_FOLDER", "uploads")
            pdf_path = os.path.join(upload_folder, pdf_filename)
            if not os.path.exists(pdf_path):
                return jsonify({"error": f"PDF file not found: {pdf_filename}"}), 404
            response = send_from_directory(upload_folder, pdf_filename)
            cors_origin = _get_cors_origin(request)
            if cors_origin:
                response.headers["Access-Control-Allow-Origin"] = cors_origin
            return response

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500
