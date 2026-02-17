"""
Auth blueprint — signup, signin, password reset.

Routes:
  POST /api/users/signup
  POST /api/users/signin
  POST /api/users/forgot-password
  POST /api/users/reset-password
"""

import logging
import os
import uuid
from datetime import datetime

from flask import Blueprint, g, jsonify, request

import config
from auth_helpers import (
    create_jwt_token,
    decode_jwt_token,
    detect_role_from_email,
    hash_password,
    hash_password_legacy,
    validate_fields,
    verify_password,
)
from db import close_conn_safely, get_db_connection
from extensions import Message, csrf_exempt, limiter, mail

logger = logging.getLogger(__name__)
bp = Blueprint("auth", __name__)


def ensure_password_resets_table():
    """Ensure password_resets table exists for forgot-password flow."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS password_resets (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                token VARCHAR(255) NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_password_resets_token ON password_resets(token);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_password_resets_email ON password_resets(email);"
        )
        conn.commit()
        cursor.close()
        close_conn_safely(conn)
    except Exception as e:
        print(f"ensure_password_resets_table: {e}")


@bp.route("/api/users/signup", methods=["POST"])
@csrf_exempt
@limiter.limit("5 per hour")  # Prevent account creation spam
def signup():
    """Sign up a new user"""
    try:
        data = request.json
        name = data.get("name")
        email = data.get("email")
        password = data.get("password")

        if not name or not email or not password:
            return jsonify({"error": "Missing required fields"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if user already exists
        cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Email already registered"}), 400

        # Create user
        user_id = str(uuid.uuid4())
        password_hash = hash_password(password)
        role = detect_role_from_email(email)  # Detect role from email domain

        cursor.execute(
            "INSERT INTO users (user_id, name, email, password_hash, role) VALUES (%s, %s, %s, %s, %s) RETURNING user_id, name, email, COALESCE(role, 'student')",
            (user_id, name, email, password_hash, role),
        )
        user = cursor.fetchone()

        if not user:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Failed to create user"}), 500

        created_user_id = user[0]

        # Create default profile (with error handling)
        try:
            cursor.execute(
                "INSERT INTO user_profiles (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
                (created_user_id,),
            )
        except Exception as e:
            logger.warning("Failed to create user_profiles", extra={"error": str(e)})

        # Create default settings (with error handling)
        try:
            cursor.execute(
                "INSERT INTO user_settings (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
                (created_user_id,),
            )
        except Exception as e:
            logger.warning("Failed to create user_settings", extra={"error": str(e)})

        # Create default preferences (with error handling)
        try:
            cursor.execute(
                "INSERT INTO user_preferences (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
                (created_user_id,),
            )
        except Exception as e:
            logger.warning("Failed to create user_preferences", extra={"error": str(e)})

        # Initialize empty AI agent digest (with error handling)
        try:
            cursor.execute(
                "INSERT INTO ai_agent_digest (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
                (created_user_id,),
            )
        except Exception as e:
            logger.warning("Failed to create ai_agent_digest", extra={"error": str(e)})

        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        # Return user data with JWT token
        user_role = user[3] if len(user) > 3 else role
        token = create_jwt_token(
            created_user_id, role=user_role, name=user[1], email=user[2]
        )
        return (
            jsonify(
                {
                    "id": created_user_id,
                    "user_id": created_user_id,
                    "name": user[1],
                    "email": user[2],
                    "role": user_role,
                    "token": token,
                    "success": True,
                }
            ),
            201,
        )

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/users/signin", methods=["POST"])
@csrf_exempt
@limiter.limit("10 per minute")  # Prevent brute-force login attacks
def signin():
    """Sign in a user"""
    conn = None
    try:
        data = request.json
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"error": "Missing email or password"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch user with password hash
        cursor.execute(
            "SELECT user_id, name, email, password_hash, COALESCE(role, 'student') FROM users WHERE email = %s",
            (email,),
        )
        user = cursor.fetchone()

        if not user:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Invalid email or password"}), 401

        user_id, name, user_email, stored_hash, role = user

        # Verify password (supports both bcrypt and legacy hashes)
        is_valid, needs_rehash = verify_password(password, stored_hash)

        if not is_valid:
            cursor.close()
            close_conn_safely(conn)
            return jsonify({"error": "Invalid email or password"}), 401

        # If using legacy hash, automatically migrate to bcrypt
        if needs_rehash:
            try:
                new_hash = hash_password(password)
                cursor.execute(
                    "UPDATE users SET password_hash = %s WHERE user_id = %s", (new_hash, user_id)
                )
                conn.commit()
                logger.info(
                    "Password migrated to bcrypt",
                    extra={"user_email": email, "migration": "legacy_to_bcrypt"},
                )
            except Exception as e:
                logger.warning(
                    "Password migration failed", extra={"user_email": email, "error": str(e)}
                )
                # Don't fail login if migration fails
                conn.rollback()

        cursor.close()
        close_conn_safely(conn)

        # Return user data with JWT token
        token = create_jwt_token(user_id, role=role, name=name, email=user_email)
        return (
            jsonify(
                {
                    "id": user_id,
                    "user_id": user_id,
                    "name": name,
                    "email": user_email,
                    "role": role,
                    "token": token,
                }
            ),
            200,
        )

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/users/forgot-password", methods=["POST"])
@csrf_exempt
@limiter.limit("3 per hour")  # Prevent password reset abuse
def forgot_password():
    """Handle forgot password request"""
    try:
        data = request.json or {}
        email = data.get("email")

        if not email:
            return jsonify({"error": "Email is required"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if user exists
        cursor.execute("SELECT user_id, name FROM users WHERE email = %s", (email,))
        user_row = cursor.fetchone()

        cursor.close()
        close_conn_safely(conn)

        # Always return success to prevent email enumeration (User Feedback)
        response = jsonify(
            {
                "success": True,
                "message": "If an account exists with this email, you will receive password reset instructions.",
            }
        )

        if user_row:
            import secrets
            from datetime import timedelta

            token = secrets.token_urlsafe(32)
            ensure_password_resets_table()
            conn = get_db_connection()
            cursor = conn.cursor()
            expires_at = datetime.utcnow() + timedelta(hours=1)
            cursor.execute(
                "INSERT INTO password_resets (email, token, expires_at) VALUES (%s, %s, %s)",
                (email, token, expires_at),
            )
            conn.commit()
            cursor.close()
            close_conn_safely(conn)
            # Reset link must open the frontend (where reset-password.html is hosted), not the API
            frontend_url = os.getenv("FRONTEND_URL")
            if not frontend_url and request.host_url and "onrender.com" in request.host_url:
                frontend_url = "https://www.myanalytiq.org"
            base_url = (frontend_url or request.host_url).rstrip("/") + "/"
            reset_link = f"{base_url}reset-password.html?token={token}&email={email}"
            if mail:
                try:
                    # Sender: use MAIL_SENDER_NAME + MAIL_DEFAULT_SENDER so recipient sees e.g. "AnalytIQ Services <services.analytiq@gmail.com>"
                    sender = os.getenv("MAIL_DEFAULT_SENDER") or app.config.get(
                        "MAIL_DEFAULT_SENDER"
                    )
                    sender_name = os.getenv("MAIL_SENDER_NAME")
                    if sender_name and sender:
                        msg = Message(
                            "Password Reset Request",
                            recipients=[email],
                            sender=(sender_name, sender),
                        )
                    else:
                        msg = Message("Password Reset Request", recipients=[email])
                    msg.body = f"Hello {user_row[1]},\n\nSomeone requested a password reset for your AnalytIQ account.\n\nClick here to reset your password: {reset_link}\n\nThis link expires in 1 hour. If you did not request this, please ignore this email."
                    mail.send(msg)
                    print(f"Email sent to {email}")
                except Exception as mail_err:
                    print(f"Failed to send email: {mail_err}")
            else:
                print("Mail not configured. Skipping email.")

        return response, 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/users/reset-password", methods=["POST"])
@csrf_exempt
@limiter.limit("5 per hour")  # Prevent password reset token abuse
def reset_password():
    """Reset password using token from email link."""
    conn = None
    try:
        data = request.json or {}
        token = data.get("token")
        email = data.get("email")
        new_password = data.get("newPassword")

        if not token or not email or not new_password:
            return jsonify({"error": "Token, email, and new password are required"}), 400

        if len(new_password) < 6:
            return jsonify({"error": "Password must be at least 6 characters"}), 400

        ensure_password_resets_table()
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM password_resets WHERE email = %s AND token = %s AND expires_at > %s",
            (email, token, datetime.utcnow()),
        )
        row = cursor.fetchone()
        if not row:
            cursor.close()
            close_conn_safely(conn)
            return (
                jsonify(
                    {"error": "Invalid or expired reset link. Please request a new password reset."}
                ),
                400,
            )

        # Hash new password with bcrypt
        new_hash = hash_password(new_password)
        cursor.execute(
            "UPDATE users SET password_hash = %s, updated_at = CURRENT_TIMESTAMP WHERE email = %s",
            (new_hash, email),
        )
        cursor.execute(
            "DELETE FROM password_resets WHERE email = %s AND token = %s", (email, token)
        )
        conn.commit()
        cursor.close()
        close_conn_safely(conn)

        return (
            jsonify({"success": True, "message": "Password has been reset. You can now sign in."}),
            200,
        )

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500
