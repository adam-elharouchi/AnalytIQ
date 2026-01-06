from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
import psycopg2
from dotenv import load_dotenv
import os
import hashlib
import json
from datetime import datetime

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure CORS to allow ALL origins including file:// protocol (null origin)
# This allows the site to work when opening HTML files directly AND on domains
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = jsonify({})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add('Access-Control-Allow-Headers', "Content-Type, Authorization")
        response.headers.add('Access-Control-Allow-Methods', "GET, POST, PUT, DELETE, OPTIONS")
        return response

@app.after_request
def after_request(response):
    # Allow all origins, including null (file:// protocol)
    origin = request.headers.get('Origin')
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Allow-Credentials'] = 'false'
    return response

# Also configure CORS with flask-cors as backup
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": False
    }
})

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(DATABASE_URL)

def hash_password(password):
    """Simple hash function (same as frontend for compatibility)"""
    hash_val = 0
    for char in password:
        hash_val = ((hash_val << 5) - hash_val) + ord(char)
        hash_val = hash_val & hash_val  # Convert to 32bit integer
    return str(hash_val)

@app.route('/api/users/signup', methods=['POST'])
def signup():
    """Sign up a new user"""
    try:
        data = request.json
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        
        if not name or not email or not password:
            return jsonify({'error': 'Missing required fields'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if user already exists
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'error': 'Email already registered'}), 400
        
        # Create user
        user_id = str(int(datetime.now().timestamp() * 1000))
        password_hash = hash_password(password)
        
        cursor.execute(
            "INSERT INTO users (user_id, name, email, password_hash) VALUES (%s, %s, %s, %s) RETURNING user_id, name, email",
            (user_id, name, email, password_hash)
        )
        user = cursor.fetchone()
        
        # Create default profile
        cursor.execute(
            "INSERT INTO user_profiles (user_id) VALUES (%s)",
            (user_id,)
        )
        
        # Create default settings
        cursor.execute(
            "INSERT INTO user_settings (user_id) VALUES (%s)",
            (user_id,)
        )
        
        # Create default preferences
        cursor.execute(
            "INSERT INTO user_preferences (user_id) VALUES (%s)",
            (user_id,)
        )
        
        # Initialize empty AI agent digest
        cursor.execute(
            "INSERT INTO ai_agent_digest (user_id) VALUES (%s)",
            (user_id,)
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'id': user[0],
            'name': user[1],
            'email': user[2]
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/signin', methods=['POST'])
def signin():
    """Sign in a user"""
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Missing email or password'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        password_hash = hash_password(password)
        cursor.execute(
            "SELECT user_id, name, email FROM users WHERE email = %s AND password_hash = %s",
            (email, password_hash)
        )
        user = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not user:
            return jsonify({'error': 'Invalid email or password'}), 401
        
        return jsonify({
            'id': user[0],
            'name': user[1],
            'email': user[2]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/profile', methods=['GET'])
def get_profile():
    """Get user profile"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'Missing user_id'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT u.user_id, u.name, u.email, 
                   p.full_name, p.bio, p.profile_picture
            FROM users u
            LEFT JOIN user_profiles p ON u.user_id = p.user_id
            WHERE u.user_id = %s
        """, (user_id,))
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not result:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'id': result[0],
            'name': result[1],
            'email': result[2],
            'fullName': result[3],
            'bio': result[4],
            'profilePicture': result[5]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/profile', methods=['PUT'])
def update_profile():
    """Update user profile"""
    try:
        data = request.json
        user_id = data.get('user_id')
        full_name = data.get('fullName')
        email = data.get('email')
        bio = data.get('bio')
        profile_picture = data.get('profilePicture')
        
        if not user_id:
            return jsonify({'error': 'Missing user_id'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update users table if email/name changed
        if email or full_name:
            if email:
                cursor.execute("UPDATE users SET email = %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s", (email, user_id))
            if full_name:
                cursor.execute("UPDATE users SET name = %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s", (full_name, user_id))
        
        # Update profile
        cursor.execute("""
            INSERT INTO user_profiles (user_id, full_name, bio, profile_picture, updated_at)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) 
            DO UPDATE SET 
                full_name = EXCLUDED.full_name,
                bio = EXCLUDED.bio,
                profile_picture = EXCLUDED.profile_picture,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, full_name, bio, profile_picture))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/settings', methods=['GET'])
def get_settings():
    """Get user settings"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'Missing user_id'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT email_notifications, dark_mode FROM user_settings WHERE user_id = %s",
            (user_id,)
        )
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not result:
            return jsonify({'emailNotifications': False, 'darkMode': False}), 200
        
        return jsonify({
            'emailNotifications': result[0],
            'darkMode': result[1]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/settings', methods=['PUT'])
def update_settings():
    """Update user settings"""
    try:
        data = request.json
        user_id = data.get('user_id')
        email_notifications = data.get('emailNotifications')
        dark_mode = data.get('darkMode')
        
        if not user_id:
            return jsonify({'error': 'Missing user_id'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO user_settings (user_id, email_notifications, dark_mode, updated_at)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id)
            DO UPDATE SET
                email_notifications = EXCLUDED.email_notifications,
                dark_mode = EXCLUDED.dark_mode,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, email_notifications, dark_mode))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/password', methods=['PUT'])
def update_password():
    """Update user password"""
    try:
        data = request.json
        user_id = data.get('user_id')
        current_password = data.get('currentPassword')
        new_password = data.get('newPassword')
        
        if not user_id or not current_password or not new_password:
            return jsonify({'error': 'Missing required fields'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verify current password
        current_hash = hash_password(current_password)
        cursor.execute(
            "SELECT id FROM users WHERE user_id = %s AND password_hash = %s",
            (user_id, current_hash)
        )
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        # Update password
        new_hash = hash_password(new_password)
        cursor.execute(
            "UPDATE users SET password_hash = %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s",
            (new_hash, user_id)
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/delete', methods=['DELETE'])
def delete_user():
    """Delete user account"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'Missing user_id'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Delete user (cascade will delete profile and settings)
        cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/conversations', methods=['GET'])
def get_conversations():
    """Get all conversations for a user"""
    try:
        user_id = request.args.get('user_id')
        archived = request.args.get('archived', 'false').lower() == 'true'
        
        if not user_id:
            return jsonify({'error': 'Missing user_id'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT conversation_id, title, archived, created_at, updated_at
            FROM conversations
            WHERE user_id = %s AND deleted = false AND archived = %s
            ORDER BY updated_at DESC
        """, (user_id, archived))
        
        conversations = []
        for row in cursor.fetchall():
            conversations.append({
                'id': row[0],
                'title': row[1],
                'archived': row[2],
                'date': row[4].isoformat() if row[4] else row[3].isoformat()
            })
        
        cursor.close()
        conn.close()
        
        return jsonify(conversations), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/conversations', methods=['POST'])
def create_conversation():
    """Create a new conversation"""
    try:
        data = request.json
        user_id = data.get('user_id')
        conversation_id = data.get('conversation_id') or str(int(datetime.now().timestamp() * 1000))
        title = data.get('title', 'New Conversation')
        
        if not user_id:
            return jsonify({'error': 'Missing user_id'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO conversations (conversation_id, user_id, title)
            VALUES (%s, %s, %s)
            ON CONFLICT (conversation_id) DO UPDATE SET
                title = EXCLUDED.title,
                updated_at = CURRENT_TIMESTAMP
            RETURNING conversation_id
        """, (conversation_id, user_id, title))
        
        conv_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'conversation_id': conv_id}), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """Get a specific conversation with messages"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'Missing user_id'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get conversation
        cursor.execute("""
            SELECT conversation_id, title, archived, created_at, updated_at
            FROM conversations
            WHERE conversation_id = %s AND user_id = %s AND deleted = false
        """, (conversation_id, user_id))
        
        conv = cursor.fetchone()
        if not conv:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Conversation not found'}), 404
        
        # Get messages
        cursor.execute("""
            SELECT role, content, message_order, created_at
            FROM conversation_messages
            WHERE conversation_id = %s
            ORDER BY message_order ASC
        """, (conversation_id,))
        
        messages = []
        for row in cursor.fetchall():
            messages.append({
                'role': row[0],
                'content': row[1],
                'order': row[2]
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'id': conv[0],
            'title': conv[1],
            'archived': conv[2],
            'date': conv[4].isoformat() if conv[4] else conv[3].isoformat(),
            'messages': messages
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/conversations/<conversation_id>', methods=['PUT'])
def update_conversation(conversation_id):
    """Update conversation (title, archive status, etc)"""
    try:
        data = request.json
        user_id = data.get('user_id')
        title = data.get('title')
        archived = data.get('archived')
        messages = data.get('messages', [])
        
        if not user_id:
            return jsonify({'error': 'Missing user_id'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update conversation
        updates = []
        params = []
        if title is not None:
            updates.append("title = %s")
            params.append(title)
        if archived is not None:
            updates.append("archived = %s")
            params.append(archived)
        
        if updates:
            params.append(conversation_id)
            params.append(user_id)
            cursor.execute(f"""
                UPDATE conversations
                SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP
                WHERE conversation_id = %s AND user_id = %s
            """, params)
        
        # Update messages if provided
        if messages:
            # Delete existing messages
            cursor.execute("DELETE FROM conversation_messages WHERE conversation_id = %s", (conversation_id,))
            
            # Insert new messages
            for idx, msg in enumerate(messages):
                cursor.execute("""
                    INSERT INTO conversation_messages (conversation_id, role, content, message_order)
                    VALUES (%s, %s, %s, %s)
                """, (conversation_id, msg.get('role'), msg.get('content'), idx))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    """Delete (soft delete) a conversation"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'Missing user_id'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE conversations
            SET deleted = true, updated_at = CURRENT_TIMESTAMP
            WHERE conversation_id = %s AND user_id = %s
        """, (conversation_id, user_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/ai-digest', methods=['GET'])
def get_ai_digest():
    """Get AI agent digest for user"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'Missing user_id'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT goal, constraints, decisions, current_state, open_questions
            FROM ai_agent_digest
            WHERE user_id = %s
        """, (user_id,))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not result:
            return jsonify({
                'goal': '',
                'constraints': [],
                'decisions': [],
                'current_state': [],
                'open_questions': []
            }), 200
        
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
        
        return jsonify({
            'goal': result[0] or '',
            'constraints': parse_array(result[1]),
            'decisions': parse_array(result[2]),
            'current_state': parse_array(result[3]),
            'open_questions': parse_array(result[4])
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/ai-digest', methods=['PUT'])
def update_ai_digest():
    """Update AI agent digest"""
    try:
        data = request.json
        user_id = data.get('user_id')
        digest = data.get('digest', {})
        
        if not user_id:
            return jsonify({'error': 'Missing user_id'}), 400
        
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
        
        cursor.execute("""
            INSERT INTO ai_agent_digest (user_id, goal, constraints, decisions, current_state, open_questions, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) DO UPDATE SET
                goal = EXCLUDED.goal,
                constraints = EXCLUDED.constraints,
                decisions = EXCLUDED.decisions,
                current_state = EXCLUDED.current_state,
                open_questions = EXCLUDED.open_questions,
                updated_at = CURRENT_TIMESTAMP
        """, (
            user_id,
            digest.get('goal', ''),
            serialize_array(digest.get('constraints', [])),
            serialize_array(digest.get('decisions', [])),
            serialize_array(digest.get('current_state', [])),
            serialize_array(digest.get('open_questions', []))
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/ai-memory', methods=['GET'])
def get_ai_memory():
    """Get AI agent memory for user"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'Missing user_id'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT memory_item
            FROM ai_agent_memory
            WHERE user_id = %s
            ORDER BY created_at ASC
        """, (user_id,))
        
        memory = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        
        return jsonify({'memory': memory}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/ai-memory', methods=['PUT'])
def update_ai_memory():
    """Update AI agent memory (replaces all)"""
    try:
        data = request.json
        user_id = data.get('user_id')
        memory_items = data.get('memory', [])
        
        if not user_id:
            return jsonify({'error': 'Missing user_id'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Delete existing memory
        cursor.execute("DELETE FROM ai_agent_memory WHERE user_id = %s", (user_id,))
        
        # Insert new memory items
        for item in memory_items:
            if item:
                cursor.execute("""
                    INSERT INTO ai_agent_memory (user_id, memory_item)
                    VALUES (%s, %s)
                """, (user_id, item))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/preferences', methods=['GET'])
def get_preferences():
    """Get user preferences"""
    try:
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'Missing user_id'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT current_language, gemini_model, ai_provider
            FROM user_preferences
            WHERE user_id = %s
        """, (user_id,))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not result:
            return jsonify({
                'currentLanguage': 'python',
                'geminiModel': 'gemini-2.5-flash',
                'aiProvider': 'gemini'
            }), 200
        
        return jsonify({
            'currentLanguage': result[0] or 'python',
            'geminiModel': result[1] or 'gemini-2.5-flash',
            'aiProvider': result[2] or 'gemini'
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/preferences', methods=['PUT'])
def update_preferences():
    """Update user preferences"""
    try:
        data = request.json
        user_id = data.get('user_id')
        current_language = data.get('currentLanguage')
        gemini_model = data.get('geminiModel')
        ai_provider = data.get('aiProvider')
        
        if not user_id:
            return jsonify({'error': 'Missing user_id'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        updates = []
        params = []
        if current_language is not None:
            updates.append("current_language = %s")
            params.append(current_language)
        if gemini_model is not None:
            updates.append("gemini_model = %s")
            params.append(gemini_model)
        if ai_provider is not None:
            updates.append("ai_provider = %s")
            params.append(ai_provider)
        
        if updates:
            params.append(user_id)
            cursor.execute(f"""
                INSERT INTO user_preferences (user_id, {', '.join([u.split(' = ')[0] for u in updates])}, updated_at)
                VALUES (%s, {', '.join(['%s'] * len(updates))}, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id) DO UPDATE SET
                    {', '.join(updates)},
                    updated_at = CURRENT_TIMESTAMP
            """, params)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/practice-progress', methods=['GET'])
def get_practice_progress():
    """Get practice progress for user"""
    try:
        user_id = request.args.get('user_id')
        exercise_id = request.args.get('exercise_id')
        
        if not user_id:
            return jsonify({'error': 'Missing user_id'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if exercise_id:
            cursor.execute("""
                SELECT exercise_id, exercise_type, status, score, time_spent, attempts, completed_at, progress_data
                FROM practice_progress
                WHERE user_id = %s AND exercise_id = %s
            """, (user_id, exercise_id))
            result = cursor.fetchone()
            if result:
                return jsonify({
                    'exercise_id': result[0],
                    'exercise_type': result[1],
                    'status': result[2],
                    'score': result[3],
                    'time_spent': result[4],
                    'attempts': result[5],
                    'completed_at': result[6].isoformat() if result[6] else None,
                    'progress_data': result[7]
                }), 200
            else:
                return jsonify({}), 200
        else:
            cursor.execute("""
                SELECT exercise_id, exercise_type, status, score, time_spent, attempts, completed_at
                FROM practice_progress
                WHERE user_id = %s
                ORDER BY updated_at DESC
            """, (user_id,))
            
            progress = []
            for row in cursor.fetchall():
                progress.append({
                    'exercise_id': row[0],
                    'exercise_type': row[1],
                    'status': row[2],
                    'score': row[3],
                    'time_spent': row[4],
                    'attempts': row[5],
                    'completed_at': row[6].isoformat() if row[6] else None
                })
            
            cursor.close()
            conn.close()
            return jsonify(progress), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/practice-progress', methods=['PUT'])
def update_practice_progress():
    """Update practice progress"""
    try:
        data = request.json
        user_id = data.get('user_id')
        exercise_id = data.get('exercise_id')
        exercise_type = data.get('exercise_type')
        status = data.get('status')
        score = data.get('score')
        time_spent = data.get('time_spent')
        attempts = data.get('attempts')
        progress_data = data.get('progress_data')
        
        if not user_id or not exercise_id:
            return jsonify({'error': 'Missing user_id or exercise_id'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        import json as json_lib
        progress_json = json_lib.dumps(progress_data) if progress_data else None
        
        cursor.execute("""
            INSERT INTO practice_progress 
                (user_id, exercise_id, exercise_type, status, score, time_spent, attempts, progress_data, completed_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, 
                    CASE WHEN %s = 'completed' THEN CURRENT_TIMESTAMP ELSE NULL END,
                    CURRENT_TIMESTAMP)
            ON CONFLICT (user_id, exercise_id) DO UPDATE SET
                exercise_type = EXCLUDED.exercise_type,
                status = EXCLUDED.status,
                score = EXCLUDED.score,
                time_spent = EXCLUDED.time_spent,
                attempts = EXCLUDED.attempts,
                progress_data = EXCLUDED.progress_data,
                completed_at = CASE WHEN EXCLUDED.status = 'completed' THEN COALESCE(practice_progress.completed_at, CURRENT_TIMESTAMP) ELSE practice_progress.completed_at END,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, exercise_id, exercise_type, status, score, time_spent, attempts, progress_json, status))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    import sys
    port = 5001  # Changed from 5000 to avoid macOS AirPlay conflict
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    print(f"Starting Flask server on port {port}...")
    print(f"API base URL: http://localhost:{port}/api")
    app.run(debug=True, port=port, host='127.0.0.1')

