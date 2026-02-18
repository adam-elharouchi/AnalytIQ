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

import config
from flask import Blueprint, jsonify, request

from auth_helpers import (
    create_jwt_token,
    detect_role_from_email,
    hash_password,
    validate_email,
    verify_password,
)
from db import get_db_connection
from extensions import Message, csrf_exempt, limiter, mail
from repositories import auth_repository as auth_repo

logger = logging.getLogger(__name__)
bp = Blueprint("auth", __name__)


@bp.route("/api/users/signup", methods=["POST"])
@csrf_exempt
@limiter.limit("5 per hour")
def signup():
    """Sign up a new user"""
    try:
        data = request.json
        name = data.get("name")
        email = data.get("email")
        password = data.get("password")

        if not name or not email or not password:
            return jsonify({"error": "Missing required fields"}), 400

        if not validate_email(email):
            return jsonify({"error": "Invalid email address"}), 400

        if len(password) < config.MIN_PASSWORD_LENGTH:
            return (
                jsonify(
                    {"error": f"Password must be at least {config.MIN_PASSWORD_LENGTH} characters"}
                ),
                400,
            )
        if len(password) > config.MAX_PASSWORD_LENGTH:
            return (
                jsonify(
                    {"error": f"Password must be at most {config.MAX_PASSWORD_LENGTH} characters"}
                ),
                400,
            )

        conn = get_db_connection()

        if auth_repo.email_exists(conn, email):
            return jsonify({"error": "Email already registered"}), 400

        user_id = str(uuid.uuid4())
        password_hash = hash_password(password)
        role = detect_role_from_email(email)

        user = auth_repo.insert_user(conn, user_id, name, email, password_hash, role)
        if not user:
            return jsonify({"error": "Failed to create user"}), 500

        created_user_id = user[0]

        try:
            auth_repo.create_default_profile(conn, created_user_id)
        except Exception as e:
            logger.warning("Failed to create user_profiles", extra={"error": str(e)})

        try:
            auth_repo.create_default_settings(conn, created_user_id)
        except Exception as e:
            logger.warning("Failed to create user_settings", extra={"error": str(e)})

        try:
            auth_repo.create_default_preferences(conn, created_user_id)
        except Exception as e:
            logger.warning("Failed to create user_preferences", extra={"error": str(e)})

        try:
            auth_repo.create_default_ai_digest(conn, created_user_id)
        except Exception as e:
            logger.warning("Failed to create ai_agent_digest", extra={"error": str(e)})

        conn.commit()

        user_role = user[3] if len(user) > 3 else role
        token = create_jwt_token(created_user_id, role=user_role, name=user[1], email=user[2])
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
@limiter.limit("10 per minute")
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

        user = auth_repo.get_user_by_email(conn, email)
        if not user:
            return jsonify({"error": "Invalid email or password"}), 401

        user_id, name, user_email, stored_hash, role = user

        is_valid, needs_rehash = verify_password(password, stored_hash)
        if not is_valid:
            return jsonify({"error": "Invalid email or password"}), 401

        if needs_rehash:
            try:
                new_hash = hash_password(password)
                auth_repo.update_password_hash(conn, user_id, new_hash)
                conn.commit()
                logger.info(
                    "Password migrated to bcrypt",
                    extra={"user_email": email, "migration": "legacy_to_bcrypt"},
                )
            except Exception as e:
                logger.warning(
                    "Password migration failed", extra={"user_email": email, "error": str(e)}
                )
                conn.rollback()

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
@limiter.limit("3 per hour")
def forgot_password():
    """Handle forgot password request"""
    try:
        data = request.json or {}
        email = data.get("email")

        if not email:
            return jsonify({"error": "Email is required"}), 400

        if not validate_email(email):
            return jsonify({"error": "Invalid email address"}), 400

        conn = get_db_connection()
        user_row = auth_repo.get_user_name_by_email(conn, email)

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

            auth_repo.ensure_password_resets_table(conn)
            expires_at = datetime.utcnow() + timedelta(hours=1)
            auth_repo.insert_password_reset_token(conn, email, token, expires_at)
            conn.commit()

            frontend_url = os.getenv("FRONTEND_URL")
            if not frontend_url and request.host_url and "onrender.com" in request.host_url:
                frontend_url = "https://www.myanalytiq.org"
            base_url = (frontend_url or request.host_url).rstrip("/") + "/"
            reset_link = f"{base_url}reset-password.html?token={token}&email={email}"

            if mail:
                try:
                    sender = os.getenv("MAIL_DEFAULT_SENDER")
                    sender_name = os.getenv("MAIL_SENDER_NAME")
                    if sender_name and sender:
                        msg = Message(
                            "Password Reset Request",
                            recipients=[email],
                            sender=(sender_name, sender),
                        )
                    else:
                        msg = Message("Password Reset Request", recipients=[email])
                    msg.body = (
                        f"Hello {user_row[1]},\n\n"
                        f"Someone requested a password reset for your AnalytIQ account.\n\n"
                        f"Click here to reset your password: {reset_link}\n\n"
                        f"This link expires in 1 hour. If you did not request this, please ignore this email."
                    )
                    mail.send(msg)
                except Exception as mail_err:
                    logger.warning("Failed to send email: %s", mail_err)
            else:
                logger.info("Mail not configured. Skipping email.")

        return response, 200

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


@bp.route("/api/users/reset-password", methods=["POST"])
@csrf_exempt
@limiter.limit("5 per hour")
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

        if len(new_password) < config.MIN_PASSWORD_LENGTH:
            return (
                jsonify(
                    {"error": f"Password must be at least {config.MIN_PASSWORD_LENGTH} characters"}
                ),
                400,
            )
        if len(new_password) > config.MAX_PASSWORD_LENGTH:
            return (
                jsonify(
                    {"error": f"Password must be at most {config.MAX_PASSWORD_LENGTH} characters"}
                ),
                400,
            )

        conn = get_db_connection()

        auth_repo.ensure_password_resets_table(conn)

        row = auth_repo.validate_reset_token(conn, email, token, datetime.utcnow())
        if not row:
            return (
                jsonify(
                    {"error": "Invalid or expired reset link. Please request a new password reset."}
                ),
                400,
            )

        new_hash = hash_password(new_password)
        auth_repo.reset_password(conn, email, new_hash)
        auth_repo.delete_reset_token(conn, email, token)
        conn.commit()

        return (
            jsonify({"success": True, "message": "Password has been reset. You can now sign in."}),
            200,
        )

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500
