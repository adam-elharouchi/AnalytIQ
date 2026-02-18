"""
User Repository — SQL operations for profiles, settings, conversations,
AI digest / memory, preferences, and practice progress.

Every function receives a DB *connection* and returns plain Python data.
The caller (blueprint) is responsible for commit / rollback / connection lifecycle.
"""

import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


def get_profile(conn, user_id):
    """Return (user_id, name, email, full_name, bio, profile_picture) or None."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT u.user_id, u.name, u.email,
               p.full_name, p.bio, p.profile_picture
        FROM users u
        LEFT JOIN user_profiles p ON u.user_id = p.user_id
        WHERE u.user_id = %s
        """,
        (user_id,),
    )
    row = cur.fetchone()
    cur.close()
    return row


def update_user_email(conn, user_id, email):
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET email = %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s",
        (email, user_id),
    )
    cur.close()


def update_user_name(conn, user_id, name):
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET name = %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s",
        (name, user_id),
    )
    cur.close()


def upsert_profile(conn, user_id, full_name, bio, profile_picture):
    cur = conn.cursor()
    cur.execute(
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
    cur.close()


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


def get_settings(conn, user_id):
    """Return (email_notifications,) or None."""
    cur = conn.cursor()
    cur.execute(
        "SELECT email_notifications FROM user_settings WHERE user_id = %s",
        (user_id,),
    )
    row = cur.fetchone()
    cur.close()
    return row


def upsert_settings(conn, user_id, email_notifications):
    cur = conn.cursor()
    cur.execute(
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
    cur.close()


# ---------------------------------------------------------------------------
# Password
# ---------------------------------------------------------------------------


def get_password_hash(conn, user_id):
    """Return password_hash string or None."""
    cur = conn.cursor()
    cur.execute("SELECT password_hash FROM users WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    return row[0] if row else None


def update_password_hash(conn, user_id, new_hash):
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET password_hash = %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s",
        (new_hash, user_id),
    )
    cur.close()


# ---------------------------------------------------------------------------
# Delete user
# ---------------------------------------------------------------------------


def delete_user(conn, user_id):
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
    cur.close()


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------


def count_conversations(conn, user_id, archived):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*)
        FROM conversations
        WHERE user_id = %s AND deleted = false AND archived = %s
        """,
        (user_id, archived),
    )
    count = cur.fetchone()[0] or 0
    cur.close()
    return count


def get_conversations(conn, user_id, archived, limit, offset):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT conversation_id, title, archived, created_at, updated_at
        FROM conversations
        WHERE user_id = %s AND deleted = false AND archived = %s
        ORDER BY updated_at DESC
        LIMIT %s OFFSET %s
        """,
        (user_id, archived, limit, offset),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def upsert_conversation(conn, conversation_id, user_id, title):
    """Insert or update conversation, returning conversation_id."""
    cur = conn.cursor()
    cur.execute(
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
    conv_id = cur.fetchone()[0]
    cur.close()
    return conv_id


def get_conversation(conn, conversation_id, user_id):
    """Return conversation row or None."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT conversation_id, title, archived, created_at, updated_at
        FROM conversations
        WHERE conversation_id = %s AND user_id = %s AND deleted = false
        """,
        (conversation_id, user_id),
    )
    row = cur.fetchone()
    cur.close()
    return row


def get_conversation_messages(conn, conversation_id):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT role, content, message_order, created_at
        FROM conversation_messages
        WHERE conversation_id = %s
        ORDER BY message_order ASC
        """,
        (conversation_id,),
    )
    rows = cur.fetchall()
    cur.close()
    return rows


def update_conversation_fields(conn, conversation_id, user_id, update_fields, params):
    """Update whitelisted fields on a conversation."""
    cur = conn.cursor()
    params = list(params) + [conversation_id, user_id]
    query = f"""
        UPDATE conversations
        SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
        WHERE conversation_id = %s AND user_id = %s
    """
    cur.execute(query, params)
    cur.close()


def replace_conversation_messages(conn, conversation_id, messages):
    """Delete all messages and insert the new list."""
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM conversation_messages WHERE conversation_id = %s",
        (conversation_id,),
    )
    for idx, msg in enumerate(messages):
        cur.execute(
            """
            INSERT INTO conversation_messages (conversation_id, role, content, message_order)
            VALUES (%s, %s, %s, %s)
            """,
            (conversation_id, msg.get("role"), msg.get("content"), idx),
        )
    cur.close()


def append_conversation_message(conn, conversation_id, role, content):
    """Append a single message to a conversation (auto-increments message_order)."""
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO conversation_messages (conversation_id, role, content, message_order)
        SELECT %s, %s, %s, COALESCE(MAX(message_order), -1) + 1
        FROM conversation_messages
        WHERE conversation_id = %s
        """,
        (conversation_id, role, content, conversation_id),
    )
    cur.close()


def soft_delete_conversation(conn, conversation_id, user_id):
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE conversations
        SET deleted = true, updated_at = CURRENT_TIMESTAMP
        WHERE conversation_id = %s AND user_id = %s
        """,
        (conversation_id, user_id),
    )
    cur.close()


# ---------------------------------------------------------------------------
# AI digest
# ---------------------------------------------------------------------------


def get_ai_digest(conn, user_id):
    """Return (goal, constraints, decisions, current_state, open_questions) or None."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT goal, constraints, decisions, current_state, open_questions
        FROM ai_agent_digest
        WHERE user_id = %s
        """,
        (user_id,),
    )
    row = cur.fetchone()
    cur.close()
    return row


def upsert_ai_digest(conn, user_id, goal, constraints, decisions, current_state, open_questions):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO ai_agent_digest
            (user_id, goal, constraints, decisions, current_state, open_questions, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (user_id) DO UPDATE SET
            goal = EXCLUDED.goal,
            constraints = EXCLUDED.constraints,
            decisions = EXCLUDED.decisions,
            current_state = EXCLUDED.current_state,
            open_questions = EXCLUDED.open_questions,
            updated_at = CURRENT_TIMESTAMP
        """,
        (user_id, goal, constraints, decisions, current_state, open_questions),
    )
    cur.close()


# ---------------------------------------------------------------------------
# AI memory
# ---------------------------------------------------------------------------


def get_ai_memory(conn, user_id):
    """Return list of memory_item strings."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT memory_item
        FROM ai_agent_memory
        WHERE user_id = %s
        ORDER BY created_at ASC
        """,
        (user_id,),
    )
    items = [row[0] for row in cur.fetchall()]
    cur.close()
    return items


def replace_ai_memory(conn, user_id, memory_items):
    """Delete all and re-insert memory items."""
    cur = conn.cursor()
    cur.execute("DELETE FROM ai_agent_memory WHERE user_id = %s", (user_id,))
    for item in memory_items:
        if item:
            cur.execute(
                "INSERT INTO ai_agent_memory (user_id, memory_item) VALUES (%s, %s)",
                (user_id, item),
            )
    cur.close()


# ---------------------------------------------------------------------------
# Preferences
# ---------------------------------------------------------------------------


def get_preferences(conn, user_id):
    """Return (current_language, gemini_model, ai_provider) or None."""
    cur = conn.cursor()
    cur.execute(
        "SELECT current_language, gemini_model, ai_provider FROM user_preferences WHERE user_id = %s",
        (user_id,),
    )
    row = cur.fetchone()
    cur.close()
    return row


def upsert_preferences(
    conn, user_id, insert_fields, insert_placeholders, params_insert, update_fields, params_update
):
    """Dynamic upsert for preferences with whitelisted fields."""
    cur = conn.cursor()
    query = f"""
        INSERT INTO user_preferences (user_id, {', '.join(insert_fields)}, updated_at)
        VALUES (%s, {', '.join(insert_placeholders)}, CURRENT_TIMESTAMP)
        ON CONFLICT (user_id) DO UPDATE SET
            {', '.join(update_fields)},
            updated_at = CURRENT_TIMESTAMP
    """
    cur.execute(query, params_insert + params_update)
    cur.close()


# ---------------------------------------------------------------------------
# Practice progress
# ---------------------------------------------------------------------------


def get_practice_progress_single(conn, user_id, exercise_id):
    """Return single exercise progress row or None."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT exercise_id, exercise_title, best_score, best_accuracy, best_time,
               total_attempts, last_attempt_score, completed, last_completed_at
        FROM practice_progress
        WHERE user_id = %s AND exercise_id = %s
        """,
        (user_id, exercise_id),
    )
    row = cur.fetchone()
    cur.close()
    return row


def get_practice_progress_all(conn, user_id):
    """Return all progress rows for user."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT exercise_id, exercise_title, best_score, best_accuracy,
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


def user_exists(conn, user_id):
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
    exists = cur.fetchone() is not None
    cur.close()
    return exists


def get_current_progress(conn, user_id, exercise_id):
    """Return (best_score, total_attempts) or None."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT best_score, total_attempts FROM practice_progress
        WHERE user_id = %s AND exercise_id = %s
        """,
        (user_id, exercise_id),
    )
    row = cur.fetchone()
    cur.close()
    return row


def upsert_practice_progress(
    conn,
    user_id,
    exercise_id,
    exercise_title,
    new_best_score,
    accuracy,
    time_spent_seconds,
    total_attempts,
    score,
    is_new_best,
    class_id,
    class_exercise_id,
):
    """Insert or update practice_progress row."""
    cur = conn.cursor()
    cur.execute(
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
            exercise_title,
            new_best_score,
            accuracy if is_new_best else None,
            time_spent_seconds if is_new_best else None,
            total_attempts,
            score,
            accuracy,
            time_spent_seconds,
            score >= 50,
            score,
            class_id,
            class_exercise_id,
        ),
    )
    cur.close()


def insert_exercise_attempt(
    conn, user_id, exercise_id, score, accuracy, time_spent, attempt_number
):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO exercise_attempts (user_id, exercise_id, score, accuracy, time_spent, attempt_number)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (user_id, exercise_id, score, accuracy, time_spent, attempt_number),
    )
    cur.close()
