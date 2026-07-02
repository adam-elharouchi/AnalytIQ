"""
Auth blueprint — signup, signin, password reset.

Routes:
  POST /api/users/signup
  POST /api/users/signin
  POST /api/users/forgot-password
  POST /api/users/reset-password
"""

import logging
import uuid
from datetime import datetime

import config
from flask import Blueprint, jsonify, request

from core.audit import audit
from core.auth import (
    create_jwt_token,
    detect_role_from_email,
    get_user_token_version,
    hash_password,
    validate_email,
    verify_password,
)
from core.database import get_db_connection
from core.extensions import csrf_exempt, limiter
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

        # Auto-assign tenant based on email domain
        email_domain = email.split("@", 1)[-1].lower() if "@" in email else None
        tenant_id = (
            auth_repo.find_tenant_by_email_domain(conn, email_domain) if email_domain else None
        )

        user = auth_repo.insert_user(
            conn, user_id, name, email, password_hash, role, tenant_id=tenant_id
        )
        if not user:
            return jsonify({"error": "Failed to create user"}), 500

        created_user_id = user[0]

        # New superadmin accounts (myanalytiq.org domain) require manual approval
        # by aelharouchi@myanalytiq.org before they can access the platform.
        pending_approval = False
        if role == "superadmin":
            try:
                cur = conn.cursor()
                cur.execute(
                    "UPDATE users SET account_status = 'pending_approval' WHERE user_id = %s",
                    (created_user_id,),
                )
                cur.close()
                pending_approval = True
            except Exception as e:
                logger.warning("Failed to set pending_approval status: %s", e)

        try:
            auth_repo.create_default_profile(conn, created_user_id)
        except Exception:
            logger.warning("Failed to create user_profiles", exc_info=True)

        try:
            auth_repo.create_default_settings(conn, created_user_id)
        except Exception:
            logger.warning("Failed to create user_settings", exc_info=True)

        try:
            auth_repo.create_default_preferences(conn, created_user_id)
        except Exception:
            logger.warning("Failed to create user_preferences", exc_info=True)

        try:
            auth_repo.create_default_ai_digest(conn, created_user_id)
        except Exception:
            logger.warning("Failed to create ai_agent_digest", exc_info=True)

        audit(
            conn,
            "CREATE_USER",
            resource_type="user",
            resource_id=created_user_id,
            details={"role": role},
        )
        conn.commit()

        user_role = user[3] if len(user) > 3 else role
        token = create_jwt_token(created_user_id, role=user_role, name=user[1], email=user[2])

        resp = {
            "id": created_user_id,
            "user_id": created_user_id,
            "name": user[1],
            "email": user[2],
            "role": user_role,
            "token": token,
            "success": True,
        }
        if pending_approval:
            resp["pending_approval"] = True
            resp["message"] = (
                "Your account has been created and is pending approval by an administrator. "
                "You will be able to access the platform once approved."
            )
            # Notify aelharouchi@myanalytiq.org so they can approve from the dashboard
            try:
                from core.email import send_email

                send_email(
                    to_email="aelharouchi@myanalytiq.org",
                    subject="[AnalytIQ] New Admin Account Pending Approval",
                    html_content=(
                        f"<p>A new superadmin account requires your approval.</p>"
                        f"<ul>"
                        f"<li><strong>Name:</strong> {user[1]}</li>"
                        f"<li><strong>Email:</strong> {user[2]}</li>"
                        f"<li><strong>Role:</strong> {user_role}</li>"
                        f"</ul>"
                        f"<p>Log in to the <a href='https://myanalytiq.org/superadmin-dashboard.html'>"
                        f"Superadmin Dashboard</a> → Pending Approvals to review.</p>"
                    ),
                )
            except Exception as email_err:
                logger.warning("Failed to send admin approval notification: %s", email_err)

        return jsonify(resp), 201

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

        user_id, name, user_email, stored_hash, role, tenant_id = user

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
            except Exception:
                logger.warning("Password migration failed for %s", email, exc_info=True)
                conn.rollback()

        # Check account status before issuing a token.
        # Gracefully fall back if new columns don't exist yet (pre-migration).
        status_row = None
        try:
            cur2 = conn.cursor()
            cur2.execute(
                "SELECT account_status, requires_password_reset FROM users WHERE user_id = %s",
                (user_id,),
            )
            status_row = cur2.fetchone()
            cur2.close()
        except Exception:
            conn.rollback()
            # columns not yet added — fetch only account_status
            try:
                cur2b = conn.cursor()
                cur2b.execute("SELECT account_status FROM users WHERE user_id = %s", (user_id,))
                row = cur2b.fetchone()
                cur2b.close()
                status_row = (row[0], False) if row else None
            except Exception:
                conn.rollback()

        if status_row:
            if status_row[0] == "disabled":
                return jsonify({"error": "Account is disabled. Contact support."}), 403
            if status_row[0] == "pending_approval":
                return jsonify({"error": "Account pending approval by an administrator."}), 403
            if status_row[0] == "denied":
                return jsonify({"error": "Account registration was denied. Contact support."}), 403

        requires_reset = bool(status_row and status_row[1])

        # Record last login timestamp
        try:
            cur3 = conn.cursor()
            cur3.execute("UPDATE users SET last_login = NOW() WHERE user_id = %s", (user_id,))
            cur3.close()
            conn.commit()
        except Exception:
            conn.rollback()

        token = create_jwt_token(
            user_id,
            role=role,
            name=name,
            email=user_email,
            tenant_id=tenant_id,
            token_version=get_user_token_version(conn, user_id),
        )
        resp = {
            "id": user_id,
            "user_id": user_id,
            "name": name,
            "email": user_email,
            "role": role,
            "token": token,
        }
        if requires_reset:
            resp["requires_password_reset"] = True
        return jsonify(resp), 200

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error("Unexpected error: %s", e, exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500


def _send_reset_email(to_email, user_name, reset_link):
    """Send password reset email synchronously."""
    from core.email import send_email

    try:
        subject = "Password Reset Request"
        body = (
            f"Hello {user_name},<br><br>"
            f"Someone requested a password reset for your AnalytIQ account.<br><br>"
            f"Click here to reset your password: <a href='{reset_link}'>{reset_link}</a><br><br>"
            f"This link expires in 1 hour. If you did not request this, please ignore this email."
        )
        send_email(to_email=to_email, subject=subject, html_content=body)
        logger.info("Sent password reset email synchronously.")
    except Exception as e:
        logger.warning("Failed to queue password reset email: %s", e)


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

        if user_row:
            import secrets
            from datetime import timedelta

            token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + timedelta(hours=1)
            auth_repo.insert_password_reset_token(conn, email, token, expires_at)
            conn.commit()

            frontend_url = config.FRONTEND_URL
            if not frontend_url and request.host_url and "onrender.com" in request.host_url:
                frontend_url = "https://www.myanalytiq.org"
            base_url = (frontend_url or request.host_url).rstrip("/") + "/"
            reset_link = f"{base_url}reset-password.html?token={token}&email={email}"
            _send_reset_email(email, user_row[1], reset_link)

        return (
            jsonify(
                {
                    "success": True,
                    "message": "If an account exists with this email, you will receive password reset instructions.",
                }
            ),
            200,
        )

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
        # Revoke all outstanding JWTs for this account (password changed).
        _revcur = conn.cursor()
        _revcur.execute(
            "UPDATE users SET token_version = COALESCE(token_version, 0) + 1 WHERE email = %s",
            (email,),
        )
        _revcur.close()
        audit(conn, "RESET_PASSWORD", resource_type="user", resource_id=email)
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
