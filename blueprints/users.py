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
from auth_helpers import hash_password, require_auth, validate_fields, verify_password
from db import close_conn_safely, get_db_connection
from extensions import csrf_exempt

logger = logging.getLogger(__name__)
bp = Blueprint("users", __name__)


@bp.route("/api/users/profile", methods=["GET"])
@require_auth
def get_profile():
    """Get user profile"""
    try:
        user_id = g.user_id

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT u.user_id, u.name, u.email, 
                   p.full_name, p.bio, p.profile_picture
            FROM users u
            LEFT JOIN user_profiles p ON u.user_id = p.user_id
            WHERE u.user_id = %s
        """,
            (user_id,),
        )
        result = cursor.fetchone()

        cursor.close()
        close_conn_safely(conn)

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

        errors = validate_fields(data, [
            ("fullName", False, config.MAX_NAME_LENGTH),
            ("email", False, config.MAX_EMAIL_LENGTH),
            ("bio", False, config.MAX_GENERIC_TEXT_LENGTH),
        ])
        if errors:
            return jsonify({"error": errors[0]}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Update users table if email/name changed
        if email or full_name:
            if email:
                cursor.execute(
                    "UPDATE users SET email = %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s",
                    (email, user_id),
                )
            if full_name:
                cursor.execute(
                    "UPDATE users SET name = %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s",
                    (full_name, user_id),
                )

        # Update profile
        cursor.execute(
            """
            INSERT INTO user_profiles (user_id, full_name, bio, profile_picture, updated_at)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) 
            DO UPDATE SET 
                full_name = EXCLUDED.full_name,
                bio = EXCLUDED.bio,
                profile_picture = EXCLUDED.profile_picture,
                updated_at = CURRENT_TIMESTAMP
        """,
            (user_id, full_name, bio, profile_picture),
        )

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

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
        cursor = conn.cursor()

        cursor.execute(
            "SELECT email_notifications FROM user_settings WHERE user_id = %s", (user_id,)
        )
        result = cursor.fetchone()

        cursor.close()
        close_conn_safely(conn)

        if not result:
            return jsonify({"emailNotifications": False}), 200

        return (
            jsonify(
                {
                    "emailNotifications": result[0],
                }
            ),
            200,
        )

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

        # Ensure boolean values (handle None/undefined)
        email_notifications = (
            bool(email_notifications) if email_notifications is not None else False
        )

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO user_settings (user_id, email_notifications, updated_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id)
            DO UPDATE SET
                email_notifications = EXCLUDED.email_notifications,
                updated_at = CURRENT_TIMESTAMP
        """,
            (user_id, email_notifications),
        )

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        return jsonify({"success": True}), 200

    except Exception as e:
        print(f"Error updating settings: {str(e)}")
        import traceback

        traceback.print_exc()
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

        errors = validate_fields(data, [
            ("currentPassword", True, config.MAX_PASSWORD_LENGTH),
            ("newPassword", True, config.MAX_PASSWORD_LENGTH),
        ])
        if errors:
            return jsonify({"error": errors[0]}), 400

        if new_password and len(new_password) < config.MIN_PASSWORD_LENGTH:
            return jsonify({"error": f"New password must be at least {config.MIN_PASSWORD_LENGTH} characters"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch current password hash
        cursor.execute("SELECT password_hash FROM users WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()

        if not result:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "User not found"}), 404

        stored_hash = result[0]

        # Verify current password
        is_valid, _ = verify_password(current_password, stored_hash)

        if not is_valid:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Current password is incorrect"}), 401

        # Update password with new bcrypt hash
        new_hash = hash_password(new_password)
        cursor.execute(
            "UPDATE users SET password_hash = %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s",
            (new_hash, user_id),
        )

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

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
        cursor = conn.cursor()

        # Delete user (cascade will delete profile and settings)
        cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

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

        # Get pagination parameters
        limit, offset = utils.get_pagination_params(request.args)

        conn = get_db_connection()
        cursor = conn.cursor()

        # Get total count
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM conversations
            WHERE user_id = %s AND deleted = false AND archived = %s
        """,
            (user_id, archived),
        )
        total_count = cursor.fetchone()[0] or 0

        # Get paginated conversations
        cursor.execute(
            """
            SELECT conversation_id, title, archived, created_at, updated_at
            FROM conversations
            WHERE user_id = %s AND deleted = false AND archived = %s
            ORDER BY updated_at DESC
            LIMIT %s OFFSET %s
        """,
            (user_id, archived, limit, offset),
        )

        conversations = []
        for row in cursor.fetchall():
            conversations.append(
                {
                    "id": row[0],
                    "title": row[1],
                    "archived": row[2],
                    "date": row[4].isoformat() if row[4] else row[3].isoformat(),
                }
            )

        cursor.close()
        close_conn_safely(conn)

        # Return paginated response
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
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO conversations (conversation_id, user_id, title)
            VALUES (%s, %s, %s)
            ON CONFLICT (conversation_id) DO UPDATE SET
                title = EXCLUDED.title,
                updated_at = CURRENT_TIMESTAMP
            RETURNING conversation_id
        """,
            (conversation_id, user_id, title),
        )

        conv_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        close_conn_safely(conn)

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
        cursor = conn.cursor()

        # Get conversation
        cursor.execute(
            """
            SELECT conversation_id, title, archived, created_at, updated_at
            FROM conversations
            WHERE conversation_id = %s AND user_id = %s AND deleted = false
        """,
            (conversation_id, user_id),
        )

        conv = cursor.fetchone()
        if not conv:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Conversation not found"}), 404

        # Get messages
        cursor.execute(
            """
            SELECT role, content, message_order, created_at
            FROM conversation_messages
            WHERE conversation_id = %s
            ORDER BY message_order ASC
        """,
            (conversation_id,),
        )

        messages = []
        for row in cursor.fetchall():
            messages.append({"role": row[0], "content": row[1], "order": row[2]})

        cursor.close()
        close_conn_safely(conn)

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
        cursor = conn.cursor()

        # Update conversation - use explicit field updates to prevent SQL injection
        # Build update query safely with whitelisted fields
        update_fields = []
        params = []

        if title is not None:
            update_fields.append("title = %s")
            params.append(title)
        if archived is not None:
            update_fields.append("archived = %s")
            params.append(archived)

        if update_fields:
            # Safe: update_fields contains only whitelisted field assignments
            params.extend([conversation_id, user_id])
            query = f"""
                UPDATE conversations
                SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                WHERE conversation_id = %s AND user_id = %s
            """
            cursor.execute(query, params)

        # Update messages if provided
        if messages:
            # Delete existing messages
            cursor.execute(
                "DELETE FROM conversation_messages WHERE conversation_id = %s", (conversation_id,)
            )

            # Insert new messages
            for idx, msg in enumerate(messages):
                cursor.execute(
                    """
                    INSERT INTO conversation_messages (conversation_id, role, content, message_order)
                    VALUES (%s, %s, %s, %s)
                """,
                    (conversation_id, msg.get("role"), msg.get("content"), idx),
                )

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        return jsonify({"success": True}), 200

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
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE conversations
            SET deleted = true, updated_at = CURRENT_TIMESTAMP
            WHERE conversation_id = %s AND user_id = %s
        """,
            (conversation_id, user_id),
        )

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

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
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT goal, constraints, decisions, current_state, open_questions
            FROM ai_agent_digest
            WHERE user_id = %s
        """,
            (user_id,),
        )

        result = cursor.fetchone()
        cursor.close()
        close_conn_safely(conn)

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

        # Helper function to parse array from TEXT field
        def parse_array(value):
            if not value:
                return []
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, list) else []
            except (json.JSONDecodeError, TypeError):
                # If not JSON, treat as single value in array or empty
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

        conn = get_db_connection()
        cursor = conn.cursor()

        # Helper function to serialize array to JSON string
        def serialize_array(value):
            if isinstance(value, list):
                return json.dumps(value)
            if isinstance(value, str):
                try:
                    # If it's already JSON, validate it
                    json.loads(value)
                    return value
                except json.JSONDecodeError:
                    # If not JSON, wrap in array
                    return json.dumps([value] if value else [])
            return json.dumps([])

        cursor.execute(
            """
            INSERT INTO ai_agent_digest (user_id, goal, constraints, decisions, current_state, open_questions, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) DO UPDATE SET
                goal = EXCLUDED.goal,
                constraints = EXCLUDED.constraints,
                decisions = EXCLUDED.decisions,
                current_state = EXCLUDED.current_state,
                open_questions = EXCLUDED.open_questions,
                updated_at = CURRENT_TIMESTAMP
        """,
            (
                user_id,
                digest.get("goal", ""),
                serialize_array(digest.get("constraints", [])),
                serialize_array(digest.get("decisions", [])),
                serialize_array(digest.get("current_state", [])),
                serialize_array(digest.get("open_questions", [])),
            ),
        )

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

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
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT memory_item
            FROM ai_agent_memory
            WHERE user_id = %s
            ORDER BY created_at ASC
        """,
            (user_id,),
        )

        memory = [row[0] for row in cursor.fetchall()]
        cursor.close()
        close_conn_safely(conn)

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
        cursor = conn.cursor()

        # Delete existing memory
        cursor.execute("DELETE FROM ai_agent_memory WHERE user_id = %s", (user_id,))

        # Insert new memory items
        for item in memory_items:
            if item:
                cursor.execute(
                    """
                    INSERT INTO ai_agent_memory (user_id, memory_item)
                    VALUES (%s, %s)
                """,
                    (user_id, item),
                )

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

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
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT current_language, gemini_model, ai_provider
            FROM user_preferences
            WHERE user_id = %s
        """,
            (user_id,),
        )

        result = cursor.fetchone()
        cursor.close()
        close_conn_safely(conn)

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
        cursor = conn.cursor()

        # Use explicit field updates to prevent SQL injection
        # Build safe UPSERT query with whitelisted fields
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
            # Safe: all fields are whitelisted
            query = f"""
                INSERT INTO user_preferences (user_id, {', '.join(insert_fields)}, updated_at)
                VALUES (%s, {', '.join(insert_placeholders)}, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id) DO UPDATE SET
                    {', '.join(update_fields)},
                    updated_at = CURRENT_TIMESTAMP
            """
            params = params_insert + params_update
            cursor.execute(query, params)

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

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
        cursor = conn.cursor()

        if exercise_id:
            cursor.execute(
                """
                SELECT exercise_id, exercise_title, best_score, best_accuracy, best_time, 
                       total_attempts, last_attempt_score, completed, last_completed_at
                FROM practice_progress
                WHERE user_id = %s AND exercise_id = %s
            """,
                (user_id, exercise_id),
            )
            result = cursor.fetchone()
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
            cursor.execute(
                """
                SELECT exercise_id, exercise_title, best_score, best_accuracy, 
                       total_attempts, completed, last_completed_at
                FROM practice_progress
                WHERE user_id = %s
                ORDER BY exercise_id
            """,
                (user_id,),
            )

            progress = []
            for row in cursor.fetchall():
                progress.append(
                    {
                        "exercise_id": row[0],
                        "exercise_title": row[1],
                        "best_score": row[2] or 0,
                        "best_accuracy": float(row[3]) if row[3] else 0,
                        "total_attempts": row[4] or 0,
                        "completed": row[5] or False,
                        "last_completed_at": row[6].isoformat() if row[6] else None,
                    }
                )

            cursor.close()
            close_conn_safely(conn)
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

        # Verify user exists in database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
        if not cursor.fetchone():
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "User not found in database. Please sign up first."}), 404

        # Get current best score if exists
        cursor.execute(
            """
            SELECT best_score, total_attempts FROM practice_progress 
            WHERE user_id = %s AND exercise_id = %s
        """,
            (user_id, exercise_id),
        )

        existing = cursor.fetchone()
        current_best_score = existing[0] if existing and existing[0] else 0
        current_attempts = existing[1] if existing and existing[1] else 0

        # Determine if this is a new best
        is_new_best = score > current_best_score
        new_best_score = max(score, current_best_score)

        # Get accuracy and time from progress_data if provided
        accuracy = progress_data.get("accuracy", 0) if progress_data else 0
        time_spent_seconds = time_spent if time_spent else 0

        # Get class_id and class_exercise_id from request data (optional, for class exercises)
        class_id = data.get("class_id")
        class_exercise_id = (
            data.get("class_exercise_id") or exercise_id
        )  # Use class_exercise_id if provided, else fallback to exercise_id

        # Insert or update practice progress
        cursor.execute(
            """
            INSERT INTO practice_progress 
                (user_id, exercise_id, exercise_title, best_score, best_accuracy, best_time, 
                 total_attempts, last_attempt_score, last_attempt_accuracy, last_attempt_time,
                 completed, last_completed_at, class_id, class_exercise_id, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                    CASE WHEN %s >= 50 THEN CURRENT_TIMESTAMP ELSE NULL END,
                    %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id, exercise_id) DO UPDATE SET
                best_score = GREATEST(practice_progress.best_score, EXCLUDED.best_score),
                best_accuracy = CASE 
                    WHEN EXCLUDED.best_score > practice_progress.best_score THEN EXCLUDED.best_accuracy
                    ELSE practice_progress.best_accuracy
                END,
                best_time = CASE 
                    WHEN EXCLUDED.best_score > practice_progress.best_score THEN EXCLUDED.best_time
                    ELSE practice_progress.best_time
                END,
                total_attempts = practice_progress.total_attempts + 1,
                last_attempt_score = EXCLUDED.last_attempt_score,
                last_attempt_accuracy = EXCLUDED.last_attempt_accuracy,
                last_attempt_time = EXCLUDED.last_attempt_time,
                completed = CASE WHEN EXCLUDED.best_score >= 50 THEN true ELSE practice_progress.completed END,
                last_completed_at = CASE 
                    WHEN EXCLUDED.best_score >= 50 THEN COALESCE(EXCLUDED.last_completed_at, CURRENT_TIMESTAMP)
                    ELSE practice_progress.last_completed_at
                END,
                class_id = COALESCE(EXCLUDED.class_id, practice_progress.class_id),
                class_exercise_id = COALESCE(EXCLUDED.class_exercise_id, practice_progress.class_exercise_id),
                updated_at = CURRENT_TIMESTAMP
        """,
            (
                user_id,
                exercise_id,
                progress_data.get("exercise_title", exercise_id) if progress_data else exercise_id,
                new_best_score,
                accuracy if is_new_best else None,
                time_spent_seconds if is_new_best else None,
                current_attempts + 1,
                score,
                accuracy,
                time_spent_seconds,
                score >= 50,
                score,
                class_id,
                class_exercise_id,
            ),
        )

        # Record this attempt in exercise_attempts table
        cursor.execute(
            """
            INSERT INTO exercise_attempts (user_id, exercise_id, score, accuracy, time_spent, attempt_number)
            VALUES (%s, %s, %s, %s, %s, %s)
        """,
            (user_id, exercise_id, score, accuracy, time_spent_seconds, current_attempts + 1),
        )

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        return (
            jsonify({"success": True, "is_new_best": is_new_best, "best_score": new_best_score}),
            200,
        )

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500
