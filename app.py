from flask import Flask, request, jsonify
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv
import os
import socket
from urllib.parse import urlparse
import hashlib
import json
from datetime import datetime

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Disable automatic OPTIONS handling so we can handle CORS manually
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Manual CORS handling - works with file:// protocol and all domains
@app.before_request
def handle_options():
    if request.method == 'OPTIONS':
        # Create response for OPTIONS preflight
        response = app.response_class()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        response.headers.add('Access-Control-Max-Age', '3600')
        response.status_code = 200
        return response

@app.after_request
def after_request(response):
    # Add CORS headers to all API responses
    if request.path.startswith('/api'):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Allow-Credentials'] = 'false'
    return response

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    """Get database connection with IPv4 fallback"""
    if not DATABASE_URL:
        raise Exception("DATABASE_URL environment variable is not set")
    
    # Debug: Check DATABASE_URL format (don't log the full password)
    if DATABASE_URL:
        url_preview = DATABASE_URL.split('@')[0] + '@' + (DATABASE_URL.split('@')[1].split('/')[0] if '@' in DATABASE_URL else 'HOST')
        print(f"DATABASE_URL format check: {url_preview[:60]}...")
    
    # Clean up the database URL - remove invalid query parameters like pgbouncer
    def clean_db_url(url):
        """Remove invalid query parameters from database URL"""
        if '?' not in url:
            return url.split('?')[0]
        return url.split('?')[0]
    
    def parse_connection_string(url):
        """Parse PostgreSQL connection URL into components"""
        try:
            # Handle both postgresql:// and postgres:// schemes
            if not url.startswith(('postgresql://', 'postgres://')):
                # If no scheme, try adding postgresql://
                if '://' not in url:
                    url = 'postgresql://' + url
                else:
                    raise ValueError(f"Unsupported connection string scheme: {url.split('://')[0]}")
            
            # Use urllib.parse.unquote to handle URL-encoded characters
            from urllib.parse import unquote
            parsed = urlparse(url)
            
            if not parsed.hostname:
                raise ValueError("Hostname is missing from connection string")
            
            # Decode URL-encoded username and password
            username = unquote(parsed.username) if parsed.username else 'postgres'
            password = unquote(parsed.password) if parsed.password else ''
            
            # Get database name (remove leading slash)
            database = parsed.path[1:] if parsed.path and len(parsed.path) > 1 else 'postgres'
            
            result = {
                'host': parsed.hostname,
                'port': parsed.port or 5432,
                'database': database,
                'user': username,
                'password': password
            }
            
            print(f"Parsed connection: host={result['host']}, port={result['port']}, database={result['database']}, user={result['user'][:20]}...")
            return result
            
        except Exception as e:
            print(f"Error parsing connection string: {e}")
            print(f"URL preview (first 80 chars): {str(url)[:80]}...")
            import traceback
            traceback.print_exc()
            return None
    
    def resolve_hostname_to_ipv4(hostname):
        """Resolve hostname to IPv4 address, avoiding IPv6"""
        try:
            # Get all addresses
            addrinfo = socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM)
            # Return first IPv4 address
            if addrinfo:
                return addrinfo[0][4][0]
        except Exception as e:
            print(f"Error resolving {hostname} to IPv4: {e}")
        return hostname  # Fallback to original hostname
    
    def connect_with_ipv4(params):
        """Connect using connection parameters, forcing IPv4"""
        try:
            # Resolve hostname to IPv4
            ipv4_host = resolve_hostname_to_ipv4(params['host'])
            # Use direct connection with IPv4 host
            conn = psycopg2.connect(
                host=ipv4_host,
                port=params['port'],
                database=params['database'],
                user=params['user'],
                password=params['password'],
                connect_timeout=10,
                sslmode='require'
            )
            return conn
        except Exception as e:
            print(f"IPv4 connection failed: {e}")
            # Try with original hostname as fallback
            try:
                conn = psycopg2.connect(
                    host=params['host'],
                    port=params['port'],
                    database=params['database'],
                    user=params['user'],
                    password=params['password'],
                    connect_timeout=10,
                    sslmode='require'
                )
                return conn
            except:
                raise
    
    # Clean the URL first
    clean_url = clean_db_url(DATABASE_URL)
    
    # Parse connection parameters
    conn_params = parse_connection_string(clean_url)
    if not conn_params:
        raise Exception(f"Failed to parse DATABASE_URL. Please check the format. URL preview: {DATABASE_URL[:30]}... (password hidden)")
    
    # For Supabase, try multiple connection methods
    if "supabase.co" in conn_params['host']:
        # Check if we're using the old direct connection format (db.PROJECT_REF.supabase.co)
        # If so, we need to use the pooler format for IPv4 compatibility
        if conn_params['host'].startswith('db.'):
            # This is a direct connection format - try to convert to pooler format
            # Extract project ref from hostname (db.omjttmkczfpnwyzrdzqi.supabase.co -> omjttmkczfpnwyzrdzqi)
            project_ref = conn_params['host'].split('.')[1]
            
            # Try Session Pooler first (port 5432, IPv4 compatible, best for persistent connections)
            # Session pooler uses: aws-0-REGION.pooler.supabase.com format
            # We'll try common regions, or use a default
            pooler_hosts = [
                f"aws-0-us-west-2.pooler.supabase.com",  # Most common
                f"aws-0-us-east-1.pooler.supabase.com",
                f"aws-0-eu-west-1.pooler.supabase.com"
            ]
            
            for pooler_host in pooler_hosts:
                try:
                    session_params = {
                        'host': pooler_host,
                        'port': 5432,
                        'database': conn_params['database'],
                        'user': f"{conn_params['user']}.{project_ref}",  # Session pooler uses user.PROJECT_REF format
                        'password': conn_params['password']
                    }
                    conn = connect_with_ipv4(session_params)
                    print(f"Connected using Supabase Session Pooler (port 5432, IPv4) via {pooler_host}")
                    return conn
                except Exception as e:
                    print(f"Session pooler {pooler_host} failed: {e}")
                    continue
            
            # If session pooler failed, try transaction pooler (port 6543)
            for pooler_host in pooler_hosts:
                try:
                    trans_params = {
                        'host': pooler_host,
                        'port': 6543,
                        'database': conn_params['database'],
                        'user': f"{conn_params['user']}.{project_ref}",
                        'password': conn_params['password']
                    }
                    conn = connect_with_ipv4(trans_params)
                    print(f"Connected using Supabase Transaction Pooler (port 6543, IPv4) via {pooler_host}")
                    return conn
                except Exception as e:
                    print(f"Transaction pooler {pooler_host} failed: {e}")
                    continue
        
        # If hostname already contains 'pooler', use it as-is
        if 'pooler' in conn_params['host']:
            try:
                conn = connect_with_ipv4(conn_params)
                print(f"Connected using existing pooler configuration")
                return conn
            except Exception as pooler_error:
                print(f"Existing pooler configuration failed: {pooler_error}")
        
        # Last resort: try direct connection (may fail on IPv4-only networks)
        try:
            direct_params = conn_params.copy()
            direct_params['port'] = 5432
            conn = connect_with_ipv4(direct_params)
            print("Connected using Supabase direct connection (port 5432, IPv4)")
            return conn
        except Exception as direct_error:
            # Provide helpful error message with instructions
            project_ref = conn_params['host'].split('.')[1] if '.' in conn_params['host'] else 'PROJECT_REF'
            raise Exception(
                f"Database connection failed. Your current DATABASE_URL uses direct connection which requires IPv6. "
                f"Render requires IPv4. Please update DATABASE_URL in Render Environment Variables to use Session Pooler (IPv4 compatible):\n"
                f"postgresql://postgres.{project_ref}:[YOUR-PASSWORD]@aws-0-us-west-2.pooler.supabase.com:5432/postgres\n"
                f"Get the exact connection string from: https://supabase.com/dashboard/project/{project_ref}/settings/database\n"
                f"Select 'Connection Pooling' → 'Session mode' → Copy the connection string.\n"
                f"Original error: {direct_error}"
            )
    
    # For non-Supabase databases, use direct connection
    try:
        conn = connect_with_ipv4(conn_params)
        print(f"Connected to database at {conn_params['host']}")
        return conn
    except Exception as e:
        raise Exception(f"Database connection failed: {e}")

def hash_password(password):
    """Simple hash function (same as frontend for compatibility)"""
    hash_val = 0
    for char in password:
        hash_val = ((hash_val << 5) - hash_val) + ord(char)
        hash_val = hash_val & hash_val  # Convert to 32bit integer
    return str(hash_val)

@app.route('/api/users/signup', methods=['OPTIONS'])
def signup_options():
    """Handle OPTIONS preflight for signup"""
    response = app.response_class()
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    response.headers['Access-Control-Max-Age'] = '3600'
    response.status_code = 200
    return response

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
        cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
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
        
        if not user:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Failed to create user'}), 500
        
        created_user_id = user[0]
        
        # Create default profile (with error handling)
        try:
            cursor.execute(
                "INSERT INTO user_profiles (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
                (created_user_id,)
            )
        except Exception as e:
            print(f"Warning: Could not create user_profiles: {e}")
        
        # Create default settings (with error handling)
        try:
            cursor.execute(
                "INSERT INTO user_settings (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
                (created_user_id,)
            )
        except Exception as e:
            print(f"Warning: Could not create user_settings: {e}")
        
        # Create default preferences (with error handling)
        try:
            cursor.execute(
                "INSERT INTO user_preferences (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
                (created_user_id,)
            )
        except Exception as e:
            print(f"Warning: Could not create user_preferences: {e}")
        
        # Initialize empty AI agent digest (with error handling)
        try:
            cursor.execute(
                "INSERT INTO ai_agent_digest (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
                (created_user_id,)
            )
        except Exception as e:
            print(f"Warning: Could not create ai_agent_digest: {e}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Return user data - include user_id for clarity
        return jsonify({
            'id': created_user_id,  # This is the user_id from database
            'user_id': created_user_id,  # Also return as user_id for compatibility
            'name': user[1],
            'email': user[2],
            'success': True
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/signin', methods=['POST', 'OPTIONS'])
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
        
        # Return user data - include user_id for clarity
        return jsonify({
            'id': user[0],  # user_id
            'user_id': user[0],  # Also return as user_id for compatibility
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
                SELECT exercise_id, exercise_title, best_score, best_accuracy, best_time, 
                       total_attempts, last_attempt_score, completed, last_completed_at
                FROM practice_progress
                WHERE user_id = %s AND exercise_id = %s
            """, (user_id, exercise_id))
            result = cursor.fetchone()
            if result:
                return jsonify({
                    'exercise_id': result[0],
                    'exercise_title': result[1],
                    'best_score': result[2] or 0,
                    'best_accuracy': float(result[3]) if result[3] else 0,
                    'best_time': result[4],
                    'total_attempts': result[5] or 0,
                    'last_attempt_score': result[6] or 0,
                    'completed': result[7] or False,
                    'last_completed_at': result[8].isoformat() if result[8] else None
                }), 200
            else:
                return jsonify({}), 200
        else:
            cursor.execute("""
                SELECT exercise_id, exercise_title, best_score, best_accuracy, 
                       total_attempts, completed, last_completed_at
                FROM practice_progress
                WHERE user_id = %s
                ORDER BY exercise_id
            """, (user_id,))
            
            progress = []
            for row in cursor.fetchall():
                progress.append({
                    'exercise_id': row[0],
                    'exercise_title': row[1],
                    'best_score': row[2] or 0,
                    'best_accuracy': float(row[3]) if row[3] else 0,
                    'total_attempts': row[4] or 0,
                    'completed': row[5] or False,
                    'last_completed_at': row[6].isoformat() if row[6] else None
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
        
        if not user_id or not exercise_id:
            return jsonify({'error': 'Missing user_id or exercise_id'}), 400
        
        # Ensure user_id is a string (in case it's passed as number)
        user_id = str(user_id)
        
        exercise_title = data.get('exercise_title', '')
        score = data.get('score', 0)
        accuracy = data.get('accuracy', 0)
        time_spent = data.get('time_spent', 0)
        progress_data = data.get('progress_data', {})
        
        if progress_data:
            exercise_title = progress_data.get('exercise_title', exercise_title)
        
        # Verify user exists in database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'error': 'User not found in database. Please sign up first.'}), 404
        
        # Get current best score if exists
        cursor.execute("""
            SELECT best_score, total_attempts FROM practice_progress 
            WHERE user_id = %s AND exercise_id = %s
        """, (user_id, exercise_id))
        
        existing = cursor.fetchone()
        current_best_score = existing[0] if existing and existing[0] else 0
        current_attempts = existing[1] if existing and existing[1] else 0
        
        # Determine if this is a new best
        is_new_best = score > current_best_score
        new_best_score = max(score, current_best_score)
        
        # Get accuracy and time from progress_data if provided
        accuracy = progress_data.get('accuracy', 0) if progress_data else 0
        time_spent_seconds = time_spent if time_spent else 0
        
        # Insert or update practice progress
        cursor.execute("""
            INSERT INTO practice_progress 
                (user_id, exercise_id, exercise_title, best_score, best_accuracy, best_time, 
                 total_attempts, last_attempt_score, last_attempt_accuracy, last_attempt_time,
                 completed, last_completed_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                    CASE WHEN %s >= 50 THEN CURRENT_TIMESTAMP ELSE NULL END,
                    CURRENT_TIMESTAMP)
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
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, exercise_id, progress_data.get('exercise_title', exercise_id) if progress_data else exercise_id,
              new_best_score, accuracy if is_new_best else None, time_spent_seconds if is_new_best else None,
              current_attempts + 1, score, accuracy, time_spent_seconds,
              score >= 50, score))
        
        # Record this attempt in exercise_attempts table
        cursor.execute("""
            INSERT INTO exercise_attempts (user_id, exercise_id, score, accuracy, time_spent, attempt_number)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user_id, exercise_id, score, accuracy, time_spent_seconds, current_attempts + 1))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'is_new_best': is_new_best,
            'best_score': new_best_score
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/exercises/progress', methods=['GET'])
def get_all_progress():
    """Get progress for all exercises for current user"""
    try:
        user_id = request.headers.get('X-User-Id') or request.args.get('user_id')
        if not user_id:
            return jsonify({'error': 'User ID required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT exercise_id, exercise_title, best_score, best_accuracy, 
                   total_attempts, completed, last_completed_at
            FROM practice_progress
            WHERE user_id = %s
            ORDER BY exercise_id
        """, (user_id,))
        
        results = cursor.fetchall()
        progress = []
        for row in results:
            progress.append({
                'exercise_id': row[0],
                'exercise_title': row[1],
                'best_score': row[2] or 0,
                'best_accuracy': float(row[3]) if row[3] else 0,
                'total_attempts': row[4] or 0,
                'completed': row[5] or False,
                'last_completed_at': row[6].isoformat() if row[6] else None
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({'progress': progress}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/exercises/<exercise_id>/leaderboard', methods=['GET'])
def get_exercise_leaderboard(exercise_id):
    """Get leaderboard for a specific exercise"""
    try:
        limit = int(request.args.get('limit', 10))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT u.name, u.email, pp.best_score, pp.best_accuracy, 
                   pp.best_time, pp.total_attempts, pp.last_completed_at
            FROM practice_progress pp
            JOIN users u ON pp.user_id = u.user_id
            WHERE pp.exercise_id = %s AND pp.best_score > 0
            ORDER BY pp.best_score DESC, pp.best_time ASC
            LIMIT %s
        """, (exercise_id, limit))
        
        results = cursor.fetchall()
        leaderboard = []
        rank = 1
        for row in results:
            leaderboard.append({
                'rank': rank,
                'name': row[0],
                'email': row[1],
                'best_score': row[2],
                'best_accuracy': float(row[3]) if row[3] else 0,
                'best_time': row[4],
                'total_attempts': row[5] or 0
            })
            rank += 1
        
        cursor.close()
        conn.close()
        
        return jsonify({'leaderboard': leaderboard}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/leaderboard/grand', methods=['GET'])
def get_grand_leaderboard():
    """Get grand leaderboard - ranked by average score across all exercises"""
    try:
        limit = int(request.args.get('limit', 10))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT u.user_id, u.name, u.email,
                   COUNT(DISTINCT pp.exercise_id) as exercises_completed,
                   AVG(pp.best_score) as average_score,
                   SUM(pp.best_score) as total_score,
                   MAX(pp.last_completed_at) as last_activity
            FROM users u
            JOIN practice_progress pp ON u.user_id = pp.user_id
            WHERE pp.completed = true AND pp.best_score >= 50
            GROUP BY u.user_id, u.name, u.email
            HAVING COUNT(DISTINCT pp.exercise_id) > 0
            ORDER BY average_score DESC, exercises_completed DESC
            LIMIT %s
        """, (limit,))
        
        results = cursor.fetchall()
        leaderboard = []
        rank = 1
        for row in results:
            leaderboard.append({
                'rank': rank,
                'user_id': row[0],
                'name': row[1],
                'email': row[2],
                'exercises_completed': row[3],
                'average_score': float(row[4]) if row[4] else 0,
                'total_score': int(row[5]) if row[5] else 0
            })
            rank += 1
        
        cursor.close()
        conn.close()
        
        return jsonify({'leaderboard': leaderboard}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    import sys
    import os
    port = int(os.getenv('PORT', 5001))  # Changed from 5000 to avoid macOS AirPlay conflict
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    
    # Only run in debug mode if explicitly set or running locally
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true' or \
                 (os.getenv('FLASK_ENV') == 'development' and 'localhost' in os.getenv('HOST', ''))
    
    print(f"Starting Flask server on port {port}...")
    print(f"Debug mode: {debug_mode}")
    print(f"API base URL: http://localhost:{port}/api")
    print(f"Health check: http://localhost:{port}/api/health")
    
    # For local development, use 127.0.0.1 (safer)
    # For production, use 0.0.0.0 (accessible from outside)
    host = '0.0.0.0' if os.getenv('FLASK_ENV') == 'production' else '127.0.0.1'
    
    try:
        app.run(debug=debug_mode, port=port, host=host)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"\n❌ Error: Port {port} is already in use!")
            print(f"   Either stop the other process or use a different port:")
            print(f"   python3 app.py 5002")
        else:
            raise

