"""
Users blueprint — profile, settings, password, delete, conversations, AI digest/memory,
preferences, practice progress.

Routes:
  GET/PUT  /api/users/profile
  GET/PUT  /api/users/settings
  PUT      /api/users/password
  DELETE   /api/users/delete
  GET/POST /api/users/conversations
  GET/PUT/DELETE /api/users/conversations/<id>
  GET/PUT  /api/users/ai-digest
  GET/PUT  /api/users/ai-memory
  GET/PUT  /api/users/preferences
  GET/PUT  /api/users/practice-progress
"""

import json
import logging
from datetime import datetime

from flask import Blueprint, g, jsonify, request

import config
import cache
import utils
from audit import audit
from auth_helpers import (
    hash_password,
    require_auth,
    validate_email,
    validate_fields,
    verify_password,
)
from db import get_db_connection
from extensions import csrf_exempt
from repositories import user_repository as user_repo

logger = logging.getLogger(__name__)
bp = Blueprint("users", __name__)


@bp.route("/api/users/profile", methods=["GET"])
@require_auth
@cache.cache_response(ttl=60, key_prefix="profile")
def get_profile():
    """Get user profile"""
    try:
        user_id = g.user_id
        conn = get_db_connection()

        result = user_repo.get_profile(conn, user_id)
        if not result:
            return jsonify({"error": "User not found"}), 404

        return (
            jsonify(
                {
                    "id": result[0],
                    "name": result[1],
                    "email": result[2],
                    "fullName": result[3],
                    "bio": result[4],
                    "profilePicture": result[5],
                }
            ),
            200,
        )

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/users/profile", methods=["PUT"])
@csrf_exempt
@require_auth
def update_profile():
    """Update user profile"""
    try:
        data = request.json or {}
        user_id = g.user_id
        full_name = data.get("fullName")
        email = data.get("email")
        bio = data.get("bio")
        profile_picture = data.get("profilePicture")

        errors = validate_fields(
            data,
            [
                ("fullName", False, config.MAX_NAME_LENGTH),
                ("email", False, config.MAX_EMAIL_LENGTH),
                ("bio", False, config.MAX_GENERIC_TEXT_LENGTH),
            ],
        )
        if errors:
            return jsonify({"error": errors[0]}), 400

        if email and not validate_email(email):
            return jsonify({"error": "Invalid email address"}), 400

        conn = get_db_connection()

        if email:
            user_repo.update_user_email(conn, user_id, email)
        if full_name:
            user_repo.update_user_name(conn, user_id, full_name)

        user_repo.upsert_profile(conn, user_id, full_name, bio, profile_picture)
        audit(conn, "UPDATE_PROFILE", resource_type="user", resource_id=user_id)
        conn.commit()

        cache.invalidate_cache(f"profile:{user_id}")
        return jsonify({"success": True}), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/users/settings", methods=["GET"])
@require_auth
def get_settings():
    """Get user settings"""
    try:
        user_id = g.user_id
        conn = get_db_connection()

        result = user_repo.get_settings(conn, user_id)
        if not result:
            return jsonify({"emailNotifications": False}), 200

        return jsonify({"emailNotifications": result[0]}), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/users/settings", methods=["PUT"])
@csrf_exempt
@require_auth
def update_settings():
    """Update user settings"""
    try:
        data = request.json
        user_id = g.user_id
        email_notifications = data.get("emailNotifications")
        email_notifications = (
            bool(email_notifications) if email_notifications is not None else False
        )

        conn = get_db_connection()
        user_repo.upsert_settings(conn, user_id, email_notifications)
        conn.commit()

        return jsonify({"success": True}), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/users/password", methods=["PUT"])
@csrf_exempt
@require_auth
def update_password():
    """Update user password"""
    conn = None
    try:
        data = request.json or {}
        user_id = g.user_id
        current_password = data.get("currentPassword")
        new_password = data.get("newPassword")

        errors = validate_fields(
            data,
            [
                ("currentPassword", True, config.MAX_PASSWORD_LENGTH),
                ("newPassword", True, config.MAX_PASSWORD_LENGTH),
            ],
        )
        if errors:
            return jsonify({"error": errors[0]}), 400

        if new_password and len(new_password) < config.MIN_PASSWORD_LENGTH:
            return (
                jsonify(
                    {
                        "error": f"New password must be at least {config.MIN_PASSWORD_LENGTH} characters"
                    }
                ),
                400,
            )

        conn = get_db_connection()

        stored_hash = user_repo.get_password_hash(conn, user_id)
        if stored_hash is None:
            return jsonify({"error": "User not found"}), 404

        is_valid, _ = verify_password(current_password, stored_hash)
        if not is_valid:
            return jsonify({"error": "Current password is incorrect"}), 401

        new_hash = hash_password(new_password)
        user_repo.update_password_hash(conn, user_id, new_hash)
        audit(conn, "UPDATE_PASSWORD", resource_type="user", resource_id=user_id)
        conn.commit()

        return jsonify({"success": True}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/users/delete", methods=["DELETE"])
@csrf_exempt
@require_auth
def delete_user():
    """Delete user account"""
    try:
        user_id = g.user_id
        conn = get_db_connection()

        user_repo.delete_user(conn, user_id)
        audit(conn, "DELETE_USER", resource_type="user", resource_id=user_id)
        conn.commit()

        return jsonify({"success": True}), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/users/conversations", methods=["GET"])
@csrf_exempt
@require_auth
def get_conversations():
    """Get all conversations for a user"""
    try:
        user_id = g.user_id
        archived = request.args.get("archived", "false").lower() == "true"
        limit, offset = utils.get_pagination_params(request.args)

        conn = get_db_connection()

        total_count = user_repo.count_conversations(conn, user_id, archived)
        rows = user_repo.get_conversations(conn, user_id, archived, limit, offset)

        conversations = [
            {
                "id": row[0],
                "title": row[1],
                "archived": row[2],
                "date": row[4].isoformat() if row[4] else row[3].isoformat(),
            }
            for row in rows
        ]

        response = utils.build_paginated_response(
            conversations, total_count, limit, offset, "conversations"
        )
        return jsonify(response), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/users/conversations", methods=["POST"])
@csrf_exempt
@require_auth
def create_conversation():
    """Create a new conversation"""
    try:
        data = request.json
        user_id = g.user_id
        conversation_id = data.get("conversation_id") or str(int(datetime.now().timestamp() * 1000))
        title = data.get("title", "New Conversation")

        conn = get_db_connection()
        conv_id = user_repo.upsert_conversation(conn, conversation_id, user_id, title)
        conn.commit()

        return jsonify({"conversation_id": conv_id}), 201

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/users/conversations/<conversation_id>", methods=["GET"])
@csrf_exempt
@require_auth
def get_conversation(conversation_id):
    """Get a specific conversation with messages"""
    try:
        user_id = g.user_id
        conn = get_db_connection()

        conv = user_repo.get_conversation(conn, conversation_id, user_id)
        if not conv:
            return jsonify({"error": "Conversation not found"}), 404

        msg_rows = user_repo.get_conversation_messages(conn, conversation_id)
        messages = [{"role": row[0], "content": row[1], "order": row[2]} for row in msg_rows]

        return (
            jsonify(
                {
                    "id": conv[0],
                    "title": conv[1],
                    "archived": conv[2],
                    "date": conv[4].isoformat() if conv[4] else conv[3].isoformat(),
                    "messages": messages,
                }
            ),
            200,
        )

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/users/conversations/<conversation_id>", methods=["PUT"])
@csrf_exempt
@require_auth
def update_conversation(conversation_id):
    """Update conversation (title, archive status, etc)"""
    conn = None
    try:
        data = request.json
        user_id = g.user_id
        title = data.get("title")
        archived = data.get("archived")
        messages = data.get("messages", [])

        conn = get_db_connection()

        update_fields = []
        params = []
        if title is not None:
            update_fields.append("title = %s")
            params.append(title)
        if archived is not None:
            update_fields.append("archived = %s")
            params.append(archived)

        if update_fields:
            user_repo.update_conversation_fields(
                conn, conversation_id, user_id, update_fields, params
            )

        if messages:
            user_repo.replace_conversation_messages(conn, conversation_id, messages)

        conn.commit()
        return jsonify({"success": True}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/users/conversations/<conversation_id>/messages", methods=["POST"])
@csrf_exempt
@require_auth
def append_conversation_message(conversation_id):
    """Append a single message to a conversation (append-only, no full replace)."""
    conn = None
    try:
        data = request.json or {}
        user_id = g.user_id
        role = data.get("role")
        content = data.get("content")

        if role not in ("user", "model"):
            return jsonify({"error": "role must be 'user' or 'model'"}), 400
        if not content or not isinstance(content, str):
            return jsonify({"error": "content is required"}), 400
        if len(content) > 50000:
            return jsonify({"error": "Message content too large"}), 413

        conn = get_db_connection()

        conv = user_repo.get_conversation(conn, conversation_id, user_id)
        if not conv:
            return jsonify({"error": "Conversation not found"}), 404

        user_repo.append_conversation_message(conn, conversation_id, role, content)
        conn.commit()

        return jsonify({"success": True}), 201

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/users/conversations/<conversation_id>", methods=["DELETE"])
@csrf_exempt
@require_auth
def delete_conversation(conversation_id):
    """Delete (soft delete) a conversation"""
    try:
        user_id = g.user_id
        conn = get_db_connection()

        user_repo.soft_delete_conversation(conn, conversation_id, user_id)
        conn.commit()

        return jsonify({"success": True}), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/users/ai-digest", methods=["GET"])
@require_auth
def get_ai_digest():
    """Get AI agent digest for user"""
    try:
        user_id = g.user_id
        conn = get_db_connection()

        result = user_repo.get_ai_digest(conn, user_id)
        if not result:
            return (
                jsonify(
                    {
                        "goal": "",
                        "constraints": [],
                        "decisions": [],
                        "current_state": [],
                        "open_questions": [],
                    }
                ),
                200,
            )

        def parse_array(value):
            if not value:
                return []
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, list) else []
            except (json.JSONDecodeError, TypeError):
                return [value] if value else []

        return (
            jsonify(
                {
                    "goal": result[0] or "",
                    "constraints": parse_array(result[1]),
                    "decisions": parse_array(result[2]),
                    "current_state": parse_array(result[3]),
                    "open_questions": parse_array(result[4]),
                }
            ),
            200,
        )

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/users/ai-digest", methods=["PUT"])
@csrf_exempt
@require_auth
def update_ai_digest():
    """Update AI agent digest"""
    try:
        data = request.json
        user_id = g.user_id
        digest = data.get("digest", {})

        def serialize_array(value):
            if isinstance(value, list):
                return json.dumps(value)
            if isinstance(value, str):
                try:
                    json.loads(value)
                    return value
                except json.JSONDecodeError:
                    return json.dumps([value] if value else [])
            return json.dumps([])

        conn = get_db_connection()
        user_repo.upsert_ai_digest(
            conn,
            user_id,
            digest.get("goal", ""),
            serialize_array(digest.get("constraints", [])),
            serialize_array(digest.get("decisions", [])),
            serialize_array(digest.get("current_state", [])),
            serialize_array(digest.get("open_questions", [])),
        )
        conn.commit()

        return jsonify({"success": True}), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/users/ai-memory", methods=["GET"])
@require_auth
def get_ai_memory():
    """Get AI agent memory for user"""
    try:
        user_id = g.user_id
        conn = get_db_connection()

        memory = user_repo.get_ai_memory(conn, user_id)
        return jsonify({"memory": memory}), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/users/ai-memory", methods=["PUT"])
@csrf_exempt
@require_auth
def update_ai_memory():
    """Update AI agent memory (replaces all)"""
    try:
        data = request.json
        user_id = g.user_id
        memory_items = data.get("memory", [])

        conn = get_db_connection()
        user_repo.replace_ai_memory(conn, user_id, memory_items)
        conn.commit()

        return jsonify({"success": True}), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/users/preferences", methods=["GET"])
@csrf_exempt
@require_auth
def get_preferences():
    """Get user preferences"""
    try:
        user_id = g.user_id
        conn = get_db_connection()

        result = user_repo.get_preferences(conn, user_id)
        if not result:
            return (
                jsonify(
                    {
                        "currentLanguage": "python",
                        "geminiModel": "gemini-2.5-flash",
                        "aiProvider": "gemini",
                    }
                ),
                200,
            )

        return (
            jsonify(
                {
                    "currentLanguage": result[0] or "python",
                    "geminiModel": result[1] or "gemini-2.5-flash",
                    "aiProvider": result[2] or "gemini",
                }
            ),
            200,
        )

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/users/preferences", methods=["PUT"])
@csrf_exempt
@require_auth
def update_preferences():
    """Update user preferences"""
    conn = None
    try:
        data = request.json
        user_id = g.user_id
        current_language = data.get("currentLanguage")
        gemini_model = data.get("geminiModel")
        ai_provider = data.get("aiProvider")

        conn = get_db_connection()

        update_fields = []
        insert_fields = []
        insert_placeholders = []
        params_insert = [user_id]
        params_update = []

        if current_language is not None:
            insert_fields.append("current_language")
            insert_placeholders.append("%s")
            params_insert.append(current_language)
            update_fields.append("current_language = %s")
            params_update.append(current_language)

        if gemini_model is not None:
            insert_fields.append("gemini_model")
            insert_placeholders.append("%s")
            params_insert.append(gemini_model)
            update_fields.append("gemini_model = %s")
            params_update.append(gemini_model)

        if ai_provider is not None:
            insert_fields.append("ai_provider")
            insert_placeholders.append("%s")
            params_insert.append(ai_provider)
            update_fields.append("ai_provider = %s")
            params_update.append(ai_provider)

        if update_fields:
            user_repo.upsert_preferences(
                conn,
                user_id,
                insert_fields,
                insert_placeholders,
                params_insert,
                update_fields,
                params_update,
            )

        conn.commit()
        return jsonify({"success": True}), 200

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/users/practice-progress", methods=["GET"])
@require_auth
def get_practice_progress():
    """Get practice progress for user"""
    try:
        user_id = g.user_id
        exercise_id = request.args.get("exercise_id")

        conn = get_db_connection()

        if exercise_id:
            result = user_repo.get_practice_progress_single(conn, user_id, exercise_id)
            if result:
                return (
                    jsonify(
                        {
                            "exercise_id": result[0],
                            "exercise_title": result[1],
                            "best_score": result[2] or 0,
                            "best_accuracy": float(result[3]) if result[3] else 0,
                            "best_time": result[4],
                            "total_attempts": result[5] or 0,
                            "last_attempt_score": result[6] or 0,
                            "completed": result[7] or False,
                            "last_completed_at": result[8].isoformat() if result[8] else None,
                        }
                    ),
                    200,
                )
            else:
                return jsonify({}), 200
        else:
            rows = user_repo.get_practice_progress_all(conn, user_id)
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
            return jsonify(progress), 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/users/practice-progress", methods=["PUT"])
@csrf_exempt
@require_auth
def update_practice_progress():
    """Update practice progress"""
    try:
        data = request.json
        user_id = g.user_id
        exercise_id = data.get("exercise_id")

        if not exercise_id:
            return jsonify({"error": "Missing exercise_id"}), 400

        exercise_title = data.get("exercise_title", "")
        score = data.get("score", 0)
        accuracy = data.get("accuracy", 0)
        time_spent = data.get("time_spent", 0)
        progress_data = data.get("progress_data", {})

        if progress_data:
            exercise_title = progress_data.get("exercise_title", exercise_title)

        conn = get_db_connection()

        if not user_repo.user_exists(conn, user_id):
            return jsonify({"error": "User not found in database. Please sign up first."}), 404

        existing = user_repo.get_current_progress(conn, user_id, exercise_id)
        current_best_score = existing[0] if existing and existing[0] else 0
        current_attempts = existing[1] if existing and existing[1] else 0

        is_new_best = score > current_best_score
        new_best_score = max(score, current_best_score)

        accuracy = progress_data.get("accuracy", 0) if progress_data else 0
        time_spent_seconds = time_spent if time_spent else 0

        class_id = data.get("class_id")
        class_exercise_id = data.get("class_exercise_id") or exercise_id

        user_repo.upsert_practice_progress(
            conn,
            user_id,
            exercise_id,
            progress_data.get("exercise_title", exercise_id) if progress_data else exercise_id,
            new_best_score,
            accuracy,
            time_spent_seconds,
            current_attempts + 1,
            score,
            is_new_best,
            class_id,
            class_exercise_id,
        )

        user_repo.insert_exercise_attempt(
            conn,
            user_id,
            exercise_id,
            score,
            accuracy,
            time_spent_seconds,
            current_attempts + 1,
        )

        audit(
            conn,
            "EXERCISE_SUBMISSION",
            resource_type="exercise",
            resource_id=exercise_id,
            details={"score": score, "accuracy": accuracy, "is_new_best": is_new_best},
        )
        conn.commit()

        return (
            jsonify({"success": True, "is_new_best": is_new_best, "best_score": new_best_score}),
            200,
        )

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500
