"""
Classes Blueprint — /api/classes/* and /api/resources/* and /api/progress/* and /api/students/*
"""
import logging
import mimetypes
import uuid
from datetime import datetime

from flask import Blueprint, Response, current_app, g, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

import core.cache as cache
import config
import core.pagination as utils
from core.audit import audit
from core.auth import require_auth, require_role, validate_fields
from core.database import get_db_connection
from core.extensions import csrf_exempt
from repositories import class_repository as class_repo

logger = logging.getLogger(__name__)
bp = Blueprint("classes", __name__)


def generate_class_code():
    """Generate a unique 10-character class code (5 letters + 5 numbers)"""
    import random
    import string

    letters = "".join(random.choices(string.ascii_uppercase, k=5))
    numbers = "".join(random.choices(string.digits, k=5))
    return letters + numbers


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _get_other_resources(conn, class_id):
    """Fetch non-chapter resources for a class. Returns [] on error."""
    try:
        return class_repo.get_class_other_resources(conn, class_id)
    except Exception as e:
        logger.warning("Error fetching class_resources: %s", e)
        return []


# ============================================================================
# Classes CRUD
# ============================================================================


@bp.route("/api/classes", methods=["POST"])
@csrf_exempt
@require_auth
@require_role("professor")
def create_class():
    """Create a new class (professor only)"""
    try:
        data = request.json or {}
        user_id = g.user_id
        name = data.get("name")
        description = data.get("description", "")
        class_code = data.get("class_code", "").strip().upper()

        errors = validate_fields(
            data,
            [
                ("name", True, config.MAX_CLASS_NAME_LENGTH),
                ("description", False, config.MAX_CLASS_DESCRIPTION_LENGTH),
            ],
        )
        if errors:
            return jsonify({"error": errors[0]}), 400

        if not class_code:
            return (
                jsonify(
                    {
                        "error": "Class code is required. Please enter a code that matches your school system."
                    }
                ),
                400,
            )

        if not class_code.isalnum() or len(class_code) < 3 or len(class_code) > 20:
            return jsonify({"error": "Class code must be 3-20 alphanumeric characters"}), 400

        conn = get_db_connection()

        if class_repo.class_code_exists(conn, class_code):
            return (
                jsonify(
                    {
                        "error": f'Class code "{class_code}" is already in use. Please choose a different code.'
                    }
                ),
                409,
            )

        new_class = class_repo.insert_class(conn, class_code, user_id, name, description)
        audit(
            conn,
            "CREATE_CLASS",
            resource_type="class",
            resource_id=new_class[0],
            details={"class_code": class_code},
        )
        conn.commit()

        cache.invalidate_cache(f"classes:user:{user_id}:*")

        return (
            jsonify(
                {
                    "class_id": new_class[0],
                    "name": new_class[1],
                    "description": new_class[2],
                    "created_at": new_class[3].isoformat() if new_class[3] else None,
                    "success": True,
                }
            ),
            201,
        )

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/classes", methods=["GET"])
@require_auth
def get_classes():
    """Get classes for current user (professor sees their classes, student sees enrolled classes)"""
    try:
        user_id = g.user_id
        limit, offset = utils.get_pagination_params(request.args)

        cache_key = f"classes:user:{user_id}:limit:{limit}:offset:{offset}"
        cached_result = cache.get_cached(cache_key)
        if cached_result:
            return jsonify(cached_result), 200

        conn = get_db_connection()
        role = getattr(g, "user_role", None) or "student"

        if role == "professor":
            total_count = class_repo.count_professor_classes(conn, user_id)
            rows = class_repo.get_professor_classes(conn, user_id, limit, offset)
        else:
            total_count = class_repo.count_student_enrolled_classes(conn, user_id)
            rows = class_repo.get_student_classes(conn, user_id, limit, offset)

        classes = [
            {
                "class_id": row[0],
                "name": row[1],
                "description": row[2],
                "created_at": row[3].isoformat() if row[3] else None,
                "student_count": row[4] or 0,
                "chapter_count": row[5] or 0,
            }
            for row in rows
        ]

        response = utils.build_paginated_response(classes, total_count, limit, offset, "classes")
        cache.set_cached(cache_key, response, ttl=300)

        return jsonify(response), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/classes/<class_id>", methods=["GET"])
@require_auth
@cache.cache_response(ttl=60, key_prefix="class")
def get_class(class_id):
    """Get class details"""
    try:
        user_id = g.user_id
        conn = get_db_connection()

        class_data = class_repo.get_class_detail(conn, class_id)
        if not class_data:
            return jsonify({"error": "Class not found"}), 404

        role = getattr(g, "user_role", None) or "student"
        is_professor = role == "professor"
        is_owner = class_data[3] == user_id

        if not is_owner and not is_professor:
            if not class_repo.check_enrollment(conn, class_id, user_id):
                return jsonify({"error": "Access denied. You are not enrolled in this class."}), 403

        student_count = class_repo.count_class_students(conn, class_id)
        chapter_count = class_repo.count_class_chapters(conn, class_id)
        exercise_count = class_repo.count_class_exercises(conn, class_id)

        return (
            jsonify(
                {
                    "class_id": class_data[0],
                    "name": class_data[1],
                    "description": class_data[2],
                    "professor_id": class_data[3],
                    "created_at": class_data[4].isoformat() if class_data[4] else None,
                    "professor_name": class_data[5],
                    "professor_email": class_data[6] if len(class_data) > 6 else None,
                    "lti_context_id": class_data[7] if len(class_data) > 7 else None,
                    "ags_enabled": class_data[8] if len(class_data) > 8 else False,
                    "student_count": student_count,
                    "chapter_count": chapter_count,
                    "exercise_count": exercise_count,
                    "is_owner": is_owner,
                }
            ),
            200,
        )

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/classes/<class_id>/resources", methods=["GET"])
@require_auth
def get_class_resources(class_id):
    """Get all resources for a class (including chapters as resources)"""
    try:
        user_id = g.user_id
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        conn = get_db_connection()

        owner = class_repo.get_class_owner(conn, class_id)
        if owner is None:
            return jsonify({"error": "Class not found"}), 404

        chapters = class_repo.get_class_chapters_as_resources(conn, class_id)

        resources = []
        for ch in chapters:
            chapter_id = ch[0]
            pdf_url = f"/api/chapters/{chapter_id}/pdf"
            resources.append(
                {
                    "resource_id": chapter_id,
                    "title": ch[1],
                    "description": ch[2],
                    "resource_type": "pdf",
                    "is_chapter": True,
                    "chapter_id": chapter_id,
                    "resource_url": pdf_url,
                    "created_at": ch[4].isoformat() if ch[4] else None,
                }
            )

        for res in _get_other_resources(conn, class_id):
            resource_url = res[4] or (f"/api/resources/{res[0]}/download" if res[0] else None)
            resources.append(
                {
                    "resource_id": res[0],
                    "title": res[1],
                    "description": res[2],
                    "resource_type": res[3],
                    "url": resource_url,
                    "created_at": res[5].isoformat() if res[5] else None,
                    "is_custom": True,
                }
            )

        return jsonify({"all_resources": resources}), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/classes/<class_id>", methods=["PUT"])
@csrf_exempt
@require_auth
def update_class(class_id):
    """Update class (professor only, must be owner)"""
    conn = None
    try:
        data = request.json
        user_id = g.user_id
        name = data.get("name")
        description = data.get("description")

        conn = get_db_connection()

        owner = class_repo.get_class_owner(conn, class_id)
        if owner is None:
            return jsonify({"error": "Class not found"}), 404
        if owner != user_id:
            return jsonify({"error": "Only the class owner can update the class"}), 403

        update_fields = []
        params = []
        if name is not None:
            update_fields.append("name = %s")
            params.append(name)
        if description is not None:
            update_fields.append("description = %s")
            params.append(description)

        if not update_fields:
            return jsonify({"error": "No fields to update"}), 400

        class_repo.update_class_fields(conn, class_id, update_fields, params)
        conn.commit()

        cache.invalidate_cache(f"classes:user:{user_id}:*")
        cache.invalidate_cache(f"class:*:{class_id}")
        return jsonify({"success": True}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/classes/<class_id>", methods=["DELETE"])
@csrf_exempt
@require_auth
def delete_class(class_id):
    """Delete class (professor only, must be owner)"""
    try:
        user_id = g.user_id
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        conn = get_db_connection()

        owner = class_repo.get_class_owner(conn, class_id)
        if owner is None:
            return jsonify({"error": "Class not found"}), 404
        if owner != user_id:
            return jsonify({"error": "Only the class owner can delete the class"}), 403

        class_repo.delete_class(conn, class_id)
        audit(conn, "DELETE_CLASS", resource_type="class", resource_id=class_id)
        conn.commit()

        cache.invalidate_cache(f"classes:user:{user_id}:*")
        cache.invalidate_cache(f"class:*:{class_id}")
        cache.invalidate_cache(f"chapters:*:class_id={class_id}")
        return jsonify({"success": True}), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


# ============================================================================
# Enrollments
# ============================================================================


@bp.route("/api/classes/enroll", methods=["POST"])
@csrf_exempt
@require_auth
@require_role("student", "superadmin", "tenant_admin")
def enroll_in_class():
    """Enroll student in a class using class_id (class code)"""
    try:
        data = request.json
        user_id = g.user_id
        class_id = data.get("class_id")

        if not class_id:
            return jsonify({"error": "Missing required field (class_id)"}), 400

        conn = get_db_connection()

        class_data = class_repo.get_class_with_name(conn, class_id)
        if not class_data:
            return jsonify({"error": "Class not found. Please check the class code."}), 404

        class_name = class_data[1]

        if class_repo.check_enrollment(conn, class_id, user_id):
            return jsonify({"error": "Already enrolled in this class"}), 400

        enrolled_at = class_repo.enroll_student(conn, class_id, user_id)
        audit(
            conn,
            "ENROLL_CLASS",
            resource_type="class",
            resource_id=class_id,
            details={"class_name": class_name},
        )
        conn.commit()

        cache.invalidate_cache(f"enrolled:{user_id}")
        cache.invalidate_cache(f"classes:user:{user_id}:*")

        return (
            jsonify(
                {
                    "class_id": class_id,
                    "class_name": class_name,
                    "enrolled_at": enrolled_at.isoformat() if enrolled_at else None,
                    "success": True,
                }
            ),
            201,
        )

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/classes/enrolled", methods=["GET"])
@require_auth
@cache.cache_response(ttl=60, key_prefix="enrolled")
def get_enrolled_classes():
    """Get all classes a student is enrolled in"""
    try:
        user_id = g.user_id
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        limit, offset = utils.get_pagination_params(request.args)
        conn = get_db_connection()

        total_count = class_repo.count_student_enrolled_classes(conn, user_id)
        rows = class_repo.get_enrolled_classes_paginated(conn, user_id, limit, offset)

        classes = [
            {
                "class_id": row[0],
                "name": row[1],
                "description": row[2],
                "created_at": row[3].isoformat() if row[3] else None,
                "professor_name": row[4],
                "professor_email": row[5],
                "enrolled_at": row[6].isoformat() if row[6] else None,
                "student_count": row[7],
                "chapter_count": row[8],
            }
            for row in rows
        ]

        response = utils.build_paginated_response(classes, total_count, limit, offset, "classes")
        return jsonify(response), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/classes/<class_id>/students", methods=["GET"])
@require_auth
def get_class_students(class_id):
    """Get all students enrolled in a class (professor only)"""
    try:
        user_id = g.user_id
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        conn = get_db_connection()

        owner = class_repo.get_class_owner(conn, class_id)
        if owner is None:
            return jsonify({"error": "Class not found"}), 404
        if owner != user_id:
            return jsonify({"error": "Only the class owner can view enrolled students"}), 403

        rows = class_repo.get_class_students_list(conn, class_id)

        students = [
            {
                "student_id": row[0],
                "name": row[1],
                "email": row[2],
                "enrolled_at": row[3].isoformat() if row[3] else None,
            }
            for row in rows
        ]

        return jsonify({"students": students}), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


# ============================================================================
# Progress Tracking
# ============================================================================


@bp.route("/api/classes/<class_id>/progress", methods=["GET"])
@require_auth
def get_class_progress(class_id):
    """Get all students' progress for a class (professor only)"""
    conn = None
    try:
        user_id = g.user_id
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        conn = get_db_connection()

        owner = class_repo.get_class_owner(conn, class_id)
        if owner is None:
            return jsonify({"error": "Class not found"}), 404
        if owner != user_id:
            return jsonify({"error": "Only the class owner can view progress"}), 403

        exercises = class_repo.get_class_exercises_for_progress(conn, class_id)
        students = class_repo.get_class_enrolled_students_for_progress(conn, class_id)
        progress_rows = class_repo.get_class_progress_bulk(conn, class_id)

        # O(1) lookup by exercise_id instead of O(n) scan per progress row
        exercise_lookup = {ex[0]: (ex[1], ex[2]) for ex in exercises}

        # Build nested structure from flat result set
        progress_data = {}
        for student in students:
            student_id, student_name, student_email = student
            progress_data[student_id] = {
                "student_id": student_id,
                "student_name": student_name,
                "student_email": student_email,
                "exercises": {},
            }

        for row in progress_rows:
            student_id = row[0]
            exercise_id = row[1]

            if student_id in progress_data:
                exercise_title, exercise_difficulty = exercise_lookup.get(exercise_id, (None, None))

                progress_data[student_id]["exercises"][exercise_id] = {
                    "exercise_id": exercise_id,
                    "exercise_title": exercise_title,
                    "difficulty": exercise_difficulty,
                    "best_score": row[2],
                    "best_accuracy": float(row[3]),
                    "total_attempts": row[4],
                    "completed": row[5],
                    "last_completed_at": row[6].isoformat() if row[6] else None,
                }

        progress_list = list(progress_data.values())

        return (
            jsonify(
                {
                    "class_id": class_id,
                    "exercises": [
                        {"exercise_id": ex[0], "title": ex[1], "difficulty": ex[2]}
                        for ex in exercises
                    ],
                    "students_progress": progress_list,
                }
            ),
            200,
        )

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/progress", methods=["GET"])
@require_auth
def get_progress():
    """Get student's progress for exercises (optionally filtered by class_id)"""
    try:
        user_id = g.user_id
        class_id = request.args.get("class_id")

        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        conn = get_db_connection()

        if class_id:
            rows = class_repo.get_student_progress_by_class(conn, user_id, class_id)
            progress = [
                {
                    "exercise_id": row[0],
                    "exercise_title": row[1],
                    "difficulty": row[2],
                    "best_score": row[3] or 0,
                    "best_accuracy": float(row[4]) if row[4] else 0,
                    "total_attempts": row[5] or 0,
                    "completed": row[6] or False,
                    "last_completed_at": row[7].isoformat() if row[7] else None,
                }
                for row in rows
            ]
        else:
            rows = class_repo.get_student_all_progress(conn, user_id)
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


@bp.route("/api/students/<student_id>/progress", methods=["GET"])
@require_auth
@require_role("professor", "superadmin", "tenant_admin")
def get_student_progress(student_id):
    """Get specific student's progress (professor / admin only)"""
    try:
        user_id = g.user_id
        class_id = request.args.get("class_id")

        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        conn = get_db_connection()

        student = class_repo.get_student_by_id(conn, student_id)
        if not student:
            return jsonify({"error": "Student not found"}), 404

        if class_id:
            owner = class_repo.get_class_owner(conn, class_id)
            if not owner or owner != user_id:
                return jsonify({"error": "Access denied"}), 403

            rows = class_repo.get_student_progress_for_class(conn, student_id, class_id)
            progress = [
                {
                    "exercise_id": row[0],
                    "exercise_title": row[1],
                    "difficulty": row[2],
                    "best_score": row[3] or 0,
                    "best_accuracy": float(row[4]) if row[4] else 0,
                    "total_attempts": row[5] or 0,
                    "completed": row[6] or False,
                    "last_completed_at": row[7].isoformat() if row[7] else None,
                }
                for row in rows
            ]
        else:
            rows = class_repo.get_student_progress_for_professor(conn, student_id, user_id)
            progress = [
                {
                    "exercise_id": row[0],
                    "exercise_title": row[1],
                    "difficulty": row[2],
                    "class_id": row[3],
                    "class_name": row[4],
                    "best_score": row[5] or 0,
                    "best_accuracy": float(row[6]) if row[6] else 0,
                    "total_attempts": row[7] or 0,
                    "completed": row[8] or False,
                    "last_completed_at": row[9].isoformat() if row[9] else None,
                }
                for row in rows
            ]

        return (
            jsonify(
                {
                    "student_id": student_id,
                    "student_name": student[1],
                    "student_email": student[2],
                    "progress": progress,
                }
            ),
            200,
        )

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


# ============================================================================
# Leaderboards
# ============================================================================


@bp.route("/api/classes/<class_id>/leaderboard/average", methods=["GET"])
@require_auth
@cache.cache_response(ttl=60, key_prefix="leaderboard")
def get_class_average_leaderboard(class_id):
    """Get average leaderboard for a class (all students ranked by average score)"""
    try:
        user_id = g.user_id
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        conn = get_db_connection()

        owner = class_repo.get_class_owner(conn, class_id)
        if owner is None:
            return jsonify({"error": "Class not found"}), 404

        is_professor = owner == user_id
        if not is_professor:
            if not class_repo.check_enrollment(conn, class_id, user_id):
                return jsonify({"error": "Not authorized to view this leaderboard"}), 403

        try:
            students = class_repo.get_class_average_leaderboard(conn, class_id)
        except Exception as query_err:
            logger.warning("Error executing leaderboard query: %s", query_err)
            students = []

        leaderboard = [
            {
                "rank": rank,
                "student_id": student[0],
                "name": student[1],
                "average_score": round(float(student[2]), 1),
                "exercises_completed": int(student[3]),
            }
            for rank, student in enumerate(students, 1)
        ]

        return jsonify({"leaderboard": leaderboard}), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/classes/<class_id>/leaderboard/exercise/<exercise_id>", methods=["GET"])
@require_auth
def get_exercise_leaderboard_for_class(class_id, exercise_id):
    """Get leaderboard for a specific exercise in a class"""
    try:
        user_id = g.user_id
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        conn = get_db_connection()

        owner = class_repo.get_class_owner(conn, class_id)
        if owner is None:
            return jsonify({"error": "Class not found"}), 404

        is_professor = owner == user_id
        if not is_professor:
            if not class_repo.check_enrollment(conn, class_id, user_id):
                return jsonify({"error": "Not authorized to view this leaderboard"}), 403

        students = class_repo.get_exercise_leaderboard_for_class(conn, class_id, exercise_id)

        leaderboard = [
            {
                "rank": rank,
                "student_id": student[0],
                "name": student[1],
                "score": round(float(student[2]), 1),
                "submitted_at": student[3].isoformat() if student[3] else None,
            }
            for rank, student in enumerate(students, 1)
        ]

        return jsonify({"leaderboard": leaderboard}), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


# ============================================================================
# Resources
# ============================================================================


@bp.route("/api/classes/<class_id>/resources", methods=["POST"])
@csrf_exempt
@require_auth
def add_class_resource(class_id):
    """Add a new resource (link) to the class"""
    try:
        conn = get_db_connection()

        data = request.json
        user_id = g.user_id
        resource_id = f"res_{str(uuid.uuid4())}"

        class_repo.insert_resource_link(
            conn,
            resource_id,
            class_id,
            user_id,
            data.get("title"),
            data.get("description", ""),
            data.get("resource_type", "link"),
            data.get("resource_url"),
        )
        conn.commit()

        return jsonify({"success": True, "resource_id": resource_id}), 201

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/classes/<class_id>/resources/upload", methods=["POST"])
@csrf_exempt
@require_auth
def upload_class_resource(class_id):
    """Upload a file as a resource"""
    try:
        conn = get_db_connection()

        if "file" not in request.files:
            return jsonify({"error": "No file part"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400

        user_id = g.user_id
        filename = secure_filename(file.filename)
        file_data = file.read()

        resource_id = f"res_{int(datetime.now().timestamp() * 1000)}"
        resource_url = f"/api/resources/{resource_id}/download"

        class_repo.insert_resource_file(
            conn,
            resource_id,
            class_id,
            user_id,
            request.form.get("title"),
            request.form.get("description", ""),
            request.form.get("resource_type", "file"),
            resource_url,
            file_data,
            filename,
        )
        conn.commit()

        return (
            jsonify({"success": True, "resource_id": resource_id, "resource_url": resource_url}),
            201,
        )

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/resources/<resource_id>/download", methods=["GET"])
def serve_resource_download(resource_id):
    """Serve resource file from database (BLOB)"""
    try:
        conn = get_db_connection()
        result = class_repo.get_resource_file(conn, resource_id)

        if not result:
            return jsonify({"error": "Resource not found"}), 404

        file_data = result[0]
        filename = result[1] or "download.file"

        if not file_data:
            return jsonify({"error": "File content is empty"}), 404

        mimetype = "application/octet-stream"
        guessed_type = mimetypes.guess_type(filename)[0]
        if guessed_type in ["application/pdf", "image/jpeg", "image/png"]:
            mimetype = guessed_type
        if filename.endswith(".pdf"):
            mimetype = "application/pdf"

        disposition = "attachment"
        if mimetype in ["application/pdf", "image/jpeg", "image/png"] or filename.endswith(".pdf"):
            disposition = "inline"

        origin = request.headers.get("Origin", "")
        allowed = config.CORS_ORIGINS
        cors_origin = "*" if "*" in allowed else (origin if origin in allowed else "")

        return Response(
            bytes(file_data),
            mimetype=mimetype,
            headers={
                "Content-Disposition": f'{disposition}; filename="{filename}"',
                "Access-Control-Allow-Origin": cors_origin,
            },
        )

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/classes/<class_id>/resources/<resource_id>", methods=["PUT", "DELETE"])
@csrf_exempt
def manage_resource(class_id, resource_id):
    """Update or Delete a resource"""
    try:
        conn = get_db_connection()

        if request.method == "DELETE":
            class_repo.delete_resource(conn, resource_id)
            conn.commit()
            return jsonify({"success": True}), 200

        elif request.method == "PUT":
            data = request.json
            class_repo.update_resource(
                conn,
                resource_id,
                data.get("title"),
                data.get("description"),
                data.get("resource_type"),
                data.get("resource_url"),
            )
            conn.commit()
            return jsonify({"success": True}), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/resources/files/<filename>", methods=["GET"])
def serve_resource_file(filename):
    """Serve uploaded resource file (Legacy - kept for older non-migrated files)"""
    try:
        return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)
    except Exception:
        return jsonify({"error": "File not found"}), 404
