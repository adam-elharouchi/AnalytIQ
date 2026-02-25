"""
Super Admin blueprint — global oversight, tenant management, and impersonation.

Routes:
  GET    /api/superadmin/tenants
  POST   /api/superadmin/tenants
  PATCH  /api/superadmin/tenants/<tenant_id>
  GET    /api/superadmin/users
  PATCH  /api/superadmin/users/<user_id>/status
  POST   /api/superadmin/users/<user_id>/impersonate
"""

import logging
import psycopg2
from flask import Blueprint, jsonify, request, g

from auth_helpers import require_auth, require_super_admin, create_jwt_token
from audit import audit
from db import get_db_connection
from extensions import csrf_exempt, limiter


def _rate_limit(rate: str):
    """Apply a Flask-Limiter rate limit only when the limiter is available."""

    def decorator(f):
        if limiter is not None:
            return limiter.limit(rate)(f)
        return f

    return decorator


logger = logging.getLogger(__name__)
bp = Blueprint("superadmin", __name__)


# ---------------------------------------------------------------------------
# Tenants API
# ---------------------------------------------------------------------------


@bp.route("/api/superadmin/tenants", methods=["GET"])
@require_auth
@require_super_admin
def list_tenants():
    """List all tenants with aggregate statistics."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                t.tenant_id, t.name, t.lti_issuer, t.is_active, t.created_at,
                (SELECT COUNT(*) FROM users u WHERE u.tenant_id = t.tenant_id) as total_users,
                (SELECT COUNT(*) FROM classes c WHERE c.tenant_id = t.tenant_id) as total_classes
            FROM tenants t
            ORDER BY t.created_at DESC
        """
        )
        rows = cur.fetchall()
        cur.close()

        tenants = []
        for r in rows:
            tenants.append(
                {
                    "tenant_id": r[0],
                    "name": r[1],
                    "lti_issuer": r[2],
                    "is_active": r[3],
                    "created_at": r[4].isoformat() if r[4] else None,
                    "total_users": r[5],
                    "total_classes": r[6],
                }
            )

        return jsonify({"tenants": tenants}), 200
    except Exception as e:
        logger.error("Failed to list tenants: %s", e)
        return jsonify({"error": "Failed to retrieve tenants"}), 500


@bp.route("/api/superadmin/tenants", methods=["POST"])
@csrf_exempt
@require_auth
@require_super_admin
def create_tenant():
    """Create a new manual tenant."""
    try:
        data = request.json or {}
        name = data.get("name")
        lti_issuer = data.get("lti_issuer")

        if not name:
            return jsonify({"error": "Tenant name is required"}), 400

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO tenants (name, lti_issuer)
                VALUES (%s, %s)
                RETURNING tenant_id, name, lti_issuer, is_active, created_at
                """,
                (name, lti_issuer),
            )
            row = cur.fetchone()

            audit(
                conn,
                "CREATE_TENANT",
                resource_type="tenant",
                resource_id=row[0],
                details={"name": name},
            )
            conn.commit()

            tenant = {
                "tenant_id": row[0],
                "name": row[1],
                "lti_issuer": row[2],
                "is_active": row[3],
                "created_at": row[4].isoformat() if row[4] else None,
                "total_users": 0,
                "total_classes": 0,
            }
            cur.close()
            return jsonify({"tenant": tenant}), 201

        except psycopg2.IntegrityError:
            conn.rollback()
            return jsonify({"error": "Tenant with this LTI issuer already exists"}), 409

    except Exception as e:
        logger.error("Failed to create tenant: %s", e)
        return jsonify({"error": "An unexpected error occurred"}), 500


@bp.route("/api/superadmin/tenants/<tenant_id>", methods=["PATCH"])
@csrf_exempt
@require_auth
@require_super_admin
def update_tenant(tenant_id):
    """Update tenant (e.g. enable/disable)."""
    try:
        data = request.json or {}
        if "is_active" not in data and "name" not in data:
            return jsonify({"error": "No update fields provided"}), 400

        conn = get_db_connection()
        cur = conn.cursor()

        updates = []
        params = []
        if "is_active" in data:
            updates.append("is_active = %s")
            params.append(bool(data["is_active"]))
        if "name" in data:
            updates.append("name = %s")
            params.append(data["name"])

        params.append(tenant_id)

        query = f"UPDATE tenants SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE tenant_id = %s RETURNING tenant_id"
        cur.execute(query, params)
        if not cur.fetchone():
            return jsonify({"error": "Tenant not found"}), 404

        audit(conn, "UPDATE_TENANT", resource_type="tenant", resource_id=tenant_id, details=data)
        conn.commit()
        cur.close()

        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error("Failed to update tenant: %s", e)
        return jsonify({"error": "Failed to update tenant"}), 500


# ---------------------------------------------------------------------------
# Users API
# ---------------------------------------------------------------------------


@bp.route("/api/superadmin/users", methods=["GET"])
@require_auth
@require_super_admin
def search_users():
    """Global paginated user search."""
    try:
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 50))
        offset = (page - 1) * limit

        search_query = request.args.get("q", "")
        tenant_id = request.args.get("tenant_id")
        role_filter = request.args.get("role", "")
        status_filter = request.args.get("status", "")

        conn = get_db_connection()
        cur = conn.cursor()

        base_query = """
            FROM users u
            LEFT JOIN tenants t ON u.tenant_id = t.tenant_id
            WHERE 1=1
        """
        params = []

        if search_query:
            base_query += " AND (u.name ILIKE %s OR u.email ILIKE %s)"
            params.extend([f"%{search_query}%", f"%{search_query}%"])

        if tenant_id:
            base_query += " AND u.tenant_id = %s"
            params.append(tenant_id)

        if role_filter:
            base_query += " AND u.role = %s"
            params.append(role_filter)

        if status_filter:
            base_query += " AND u.account_status = %s"
            params.append(status_filter)

        # Global role distribution (unfiltered, always shows platform-wide counts)
        cur.execute("SELECT role, COUNT(*) FROM users GROUP BY role")
        distribution_rows = cur.fetchall()
        role_distribution = {"superadmin": 0, "professor": 0, "student": 0, "other": 0}
        for dr in distribution_rows:
            r_name = dr[0]
            if r_name in role_distribution:
                role_distribution[r_name] = dr[1]
            else:
                role_distribution["other"] += dr[1]

        # Single query: paginated rows + filtered total via window function (avoids 2 round-trips)
        query = f"""
            SELECT u.user_id, u.name, u.email, u.role, u.account_status, u.created_at,
                   t.name as tenant_name, t.tenant_id,
                   COUNT(*) OVER() AS total_count
            {base_query}
            ORDER BY u.created_at DESC
            LIMIT %s OFFSET %s
        """
        cur.execute(query, params + [limit, offset])
        rows = cur.fetchall()
        cur.close()

        total = rows[0][8] if rows else 0

        users = []
        for r in rows:
            users.append(
                {
                    "user_id": r[0],
                    "name": r[1],
                    "email": r[2],
                    "role": r[3],
                    "is_super_admin": r[3] == "superadmin",
                    "account_status": r[4] or "active",
                    "created_at": r[5].isoformat() if r[5] else None,
                    "tenant_name": r[6],
                    "tenant_id": r[7],
                }
            )

        return (
            jsonify(
                {
                    "users": users,
                    "total": total,
                    "pages": (total + limit - 1) // limit,
                    "current_page": page,
                    "role_distribution": role_distribution,
                }
            ),
            200,
        )

    except Exception as e:
        logger.error("Failed to search users: %s", e)
        return jsonify({"error": "Failed to search users"}), 500


@bp.route("/api/superadmin/users/<user_id>/status", methods=["PATCH"])
@csrf_exempt
@require_auth
@require_super_admin
def update_user_status(user_id):
    """Update user account status."""
    try:
        data = request.json or {}
        status = data.get("account_status")
        if not status:
            return jsonify({"error": "Status is required"}), 400

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "UPDATE users SET account_status = %s, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s RETURNING user_id",
            (status, user_id),
        )
        if not cur.fetchone():
            return jsonify({"error": "User not found"}), 404

        action = "DISABLE_USER" if status == "disabled" else "ENABLE_USER"
        audit(conn, action, resource_type="user", resource_id=user_id, details={"status": status})
        conn.commit()
        cur.close()

        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error("Failed to update user status: %s", e)
        return jsonify({"error": "Failed to update user status"}), 500


# ---------------------------------------------------------------------------
# Impersonation API
# ---------------------------------------------------------------------------


@bp.route("/api/superadmin/users/<user_id>/impersonate", methods=["POST"])
@csrf_exempt
@require_auth
@require_super_admin
@_rate_limit("10 per minute")
def impersonate_user(user_id):
    """Generate a short-lived token to impersonate another user."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT user_id, name, email, role FROM users WHERE user_id = %s",
            (user_id,),
        )
        target_user = cur.fetchone()

        if not target_user:
            return jsonify({"error": "User not found"}), 404

        if target_user[3] == "superadmin":  # role
            return jsonify({"error": "Cannot impersonate another Super Admin"}), 403

        impersonator_id = getattr(g, "user_id", None)
        audit(conn, "IMPERSONATE_USER", resource_type="user", resource_id=user_id)
        conn.commit()
        cur.close()

        # Generate scoped token with impersonator_id baked in.
        # Short 1-hour TTL so abandoned impersonation sessions expire promptly.
        token = create_jwt_token(
            user_id=target_user[0],
            role=target_user[3],
            name=target_user[1],
            email=target_user[2],
            impersonator_id=impersonator_id,
            expires_hours=1,
        )

        return (
            jsonify(
                {
                    "success": True,
                    "token": token,
                    "message": f"You are now impersonating {target_user[1]}",
                }
            ),
            200,
        )

    except Exception as e:
        logger.error("Failed to assume impersonation: %s", e)
        return jsonify({"error": "An unexpected error occurred"}), 500


@bp.route("/api/superadmin/contact-submissions", methods=["GET"])
@require_auth
@require_super_admin
def get_contact_submissions():
    """Get all contact form submissions, ordered by most recent."""
    conn = None
    try:
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 50, type=int)
        offset = (page - 1) * limit

        conn = get_db_connection()
        cur = conn.cursor()

        # Get total count
        cur.execute("SELECT COUNT(*) FROM contact_submissions")
        total_records = cur.fetchone()[0]
        total_pages = (total_records + limit - 1) // limit

        cur.execute(
            """
            SELECT submission_id, name, email, subject, message, status, created_at, user_id
            FROM contact_submissions
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        )

        submissions = []
        for r in cur.fetchall():
            submissions.append(
                {
                    "id": r[0],
                    "name": r[1],
                    "email": r[2],
                    "subject": r[3],
                    "message": r[4],
                    "status": r[5],
                    "created_at": r[6].isoformat() if r[6] else None,
                    "user_id": r[7],
                }
            )

        return (
            jsonify(
                {
                    "submissions": submissions,
                    "total": total_records,
                    "page": page,
                    "pages": total_pages,
                    "success": True,
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Error fetching contact submissions: {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch contact submissions"}), 500
    finally:
        if conn:
            conn.close()


@bp.route("/api/superadmin/contact-submissions/<submission_id>", methods=["PATCH"])
@csrf_exempt
@require_auth
@require_super_admin
def update_contact_submission(submission_id):
    """Update the status of a contact form submission."""
    data = request.json or {}
    status = data.get("status")
    _valid_statuses = {"new", "read", "resolved", "archived"}
    if status not in _valid_statuses:
        return (
            jsonify({"error": f"Status must be one of: {', '.join(sorted(_valid_statuses))}"}),
            400,
        )

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE contact_submissions SET status = %s WHERE submission_id = %s RETURNING submission_id",
            (status, submission_id),
        )
        if not cur.fetchone():
            return jsonify({"error": "Submission not found"}), 404
        conn.commit()
        cur.close()
        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error("Failed to update contact submission: %s", e)
        return jsonify({"error": "Failed to update submission"}), 500


# ---------------------------------------------------------------------------
# Audit Log API
# ---------------------------------------------------------------------------


@bp.route("/api/superadmin/audit", methods=["GET"])
@require_auth
@require_super_admin
def get_audit_log():
    """Paginated, filterable read of the audit_log table."""
    try:
        page = request.args.get("page", 1, type=int)
        limit = min(request.args.get("limit", 50, type=int), 100)
        offset = (page - 1) * limit
        action_filter = request.args.get("action", "")
        actor_id = request.args.get("actor_id", "")
        resource_type = request.args.get("resource_type", "")
        from_date = request.args.get("from", "")
        to_date = request.args.get("to", "")

        conn = get_db_connection()
        cur = conn.cursor()

        base = """
            FROM audit_log al
            LEFT JOIN users u ON al.user_id = u.user_id
            WHERE 1=1
        """
        params = []

        if action_filter:
            base += " AND al.action = %s"
            params.append(action_filter)
        if actor_id:
            base += " AND al.user_id = %s"
            params.append(actor_id)
        if resource_type:
            base += " AND al.resource_type = %s"
            params.append(resource_type)
        if from_date:
            base += " AND al.created_at >= %s"
            params.append(from_date)
        if to_date:
            base += " AND al.created_at <= %s"
            params.append(to_date)

        cur.execute(
            f"""
            SELECT al.id, al.action, al.resource_type, al.resource_id,
                   al.user_id, u.name AS actor_name, u.email AS actor_email,
                   al.ip_address, al.details, al.created_at
            {base}
            ORDER BY al.created_at DESC
            LIMIT %s OFFSET %s
            """,
            params + [limit, offset],
        )
        rows = cur.fetchall()

        cur.execute(f"SELECT COUNT(*) {base}", params)
        total = cur.fetchone()[0]
        cur.close()

        entries = [
            {
                "log_id": r[0],
                "action": r[1],
                "resource_type": r[2],
                "resource_id": r[3],
                "actor_id": r[4],
                "actor_name": r[5],
                "actor_email": r[6],
                "ip_address": r[7],
                "details": r[8],
                "created_at": r[9].isoformat() if r[9] else None,
            }
            for r in rows
        ]

        return (
            jsonify(
                {
                    "entries": entries,
                    "total": total,
                    "page": page,
                    "pages": (total + limit - 1) // limit,
                }
            ),
            200,
        )
    except Exception as e:
        logger.error("Failed to fetch audit log: %s", e)
        return jsonify({"error": "Failed to fetch audit log"}), 500


# ---------------------------------------------------------------------------
# Admin Account Approval API
# ---------------------------------------------------------------------------


@bp.route("/api/superadmin/pending-approvals", methods=["GET"])
@require_auth
@require_super_admin
def get_pending_approvals():
    """List accounts waiting for manual approval (account_status = 'pending_approval')."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT user_id, name, email, role, created_at
            FROM users
            WHERE account_status = 'pending_approval'
            ORDER BY created_at DESC
            """
        )
        rows = cur.fetchall()
        cur.close()

        return (
            jsonify(
                {
                    "pending": [
                        {
                            "user_id": r[0],
                            "name": r[1],
                            "email": r[2],
                            "role": r[3],
                            "created_at": r[4].isoformat() if r[4] else None,
                        }
                        for r in rows
                    ],
                    "count": len(rows),
                }
            ),
            200,
        )
    except Exception as e:
        logger.error("Failed to fetch pending approvals: %s", e)
        return jsonify({"error": "Failed to fetch pending approvals"}), 500


@bp.route("/api/superadmin/users/<user_id>/approve", methods=["PATCH"])
@csrf_exempt
@require_auth
@require_super_admin
def approve_admin(user_id):
    """Approve a pending admin/superadmin account (set account_status = 'active')."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE users
            SET account_status = 'active', updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s AND account_status = 'pending_approval'
            RETURNING user_id, name, email
            """,
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "User not found or not pending approval"}), 404

        audit(
            conn,
            "ENABLE_USER",
            resource_type="user",
            resource_id=user_id,
            details={"action": "approved_admin"},
        )
        conn.commit()
        cur.close()

        return (
            jsonify({"success": True, "message": f"Account for {row[1]} ({row[2]}) approved."}),
            200,
        )
    except Exception as e:
        logger.error("Failed to approve admin: %s", e)
        return jsonify({"error": "Failed to approve account"}), 500


@bp.route("/api/superadmin/users/<user_id>/deny", methods=["PATCH"])
@csrf_exempt
@require_auth
@require_super_admin
def deny_admin(user_id):
    """Deny a pending admin/superadmin account (set account_status = 'denied')."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE users
            SET account_status = 'denied', updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s AND account_status = 'pending_approval'
            RETURNING user_id, name, email
            """,
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "User not found or not pending approval"}), 404

        audit(
            conn,
            "DISABLE_USER",
            resource_type="user",
            resource_id=user_id,
            details={"action": "denied_admin"},
        )
        conn.commit()
        cur.close()

        return (
            jsonify({"success": True, "message": f"Account for {row[1]} ({row[2]}) denied."}),
            200,
        )
    except Exception as e:
        logger.error("Failed to deny admin: %s", e)
        return jsonify({"error": "Failed to deny account"}), 500


# ---------------------------------------------------------------------------
# Delete Operations
# ---------------------------------------------------------------------------


@bp.route("/api/superadmin/users/<user_id>", methods=["DELETE"])
@csrf_exempt
@require_auth
@require_super_admin
def delete_user(user_id):
    """Permanently delete a user account and all associated data."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Fetch basic info for audit log before deletion
        cur.execute("SELECT name, email, role FROM users WHERE user_id = %s", (user_id,))
        target = cur.fetchone()
        if not target:
            return jsonify({"error": "User not found"}), 404
        if target[2] == "superadmin":
            return jsonify({"error": "Cannot delete another superadmin account"}), 403

        # Cascade: remove enrollments, profile data, then the user
        cur.execute("DELETE FROM class_enrollments WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM user_profiles     WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM user_settings     WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM user_preferences  WHERE user_id = %s", (user_id,))
        cur.execute("DELETE FROM users             WHERE user_id = %s", (user_id,))

        audit(
            conn,
            "DELETE_USER",
            resource_type="user",
            resource_id=user_id,
            details={"name": target[0], "email": target[1]},
        )
        conn.commit()
        cur.close()

        return (
            jsonify({"success": True, "message": f"User {target[0]} ({target[1]}) deleted."}),
            200,
        )
    except Exception as e:
        logger.error("Failed to delete user: %s", e)
        return jsonify({"error": "Failed to delete user"}), 500


@bp.route("/api/superadmin/classes/<class_id>", methods=["DELETE"])
@csrf_exempt
@require_auth
@require_super_admin
def delete_class_admin(class_id):
    """Admin: permanently delete a class and all its chapters/exercises/enrollments."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT name FROM classes WHERE class_id = %s", (class_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "Class not found"}), 404

        # Cascade: exercises → chapters → enrollments → class
        cur.execute(
            """
            DELETE FROM class_exercises
            WHERE chapter_id IN (SELECT chapter_id FROM class_chapters WHERE class_id = %s)
            """,
            (class_id,),
        )
        cur.execute("DELETE FROM class_chapters    WHERE class_id = %s", (class_id,))
        cur.execute("DELETE FROM class_enrollments WHERE class_id = %s", (class_id,))
        cur.execute("DELETE FROM classes           WHERE class_id = %s", (class_id,))

        audit(
            conn,
            "DELETE_CLASS",
            resource_type="class",
            resource_id=class_id,
            details={"name": row[0]},
        )
        conn.commit()
        cur.close()

        return jsonify({"success": True, "message": f"Class '{row[0]}' deleted."}), 200
    except Exception as e:
        logger.error("Failed to delete class: %s", e)
        return jsonify({"error": "Failed to delete class"}), 500


@bp.route("/api/superadmin/tenants/<tenant_id>", methods=["DELETE"])
@csrf_exempt
@require_auth
@require_super_admin
def delete_tenant(tenant_id):
    """Delete a tenant. Nullifies tenant_id on associated users/classes (not cascade-delete)."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT name FROM tenants WHERE tenant_id = %s", (tenant_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "Tenant not found"}), 404

        # Detach users and classes rather than deleting them
        cur.execute("UPDATE users   SET tenant_id = NULL WHERE tenant_id = %s", (tenant_id,))
        cur.execute("UPDATE classes SET tenant_id = NULL WHERE tenant_id = %s", (tenant_id,))
        cur.execute("DELETE FROM tenants WHERE tenant_id = %s", (tenant_id,))

        audit(
            conn,
            "DELETE_TENANT",
            resource_type="tenant",
            resource_id=tenant_id,
            details={"name": row[0]},
        )
        conn.commit()
        cur.close()

        return jsonify({"success": True, "message": f"Tenant '{row[0]}' deleted."}), 200
    except Exception as e:
        logger.error("Failed to delete tenant: %s", e)
        return jsonify({"error": "Failed to delete tenant"}), 500


# ---------------------------------------------------------------------------
# Role Management
# ---------------------------------------------------------------------------


@bp.route("/api/superadmin/users/<user_id>/role", methods=["PATCH"])
@csrf_exempt
@require_auth
@require_super_admin
def change_user_role(user_id):
    """
    Change a user's role and optionally their tenant_id.

    Body:
      role (required): student | professor | tenant_admin | superadmin
      tenant_id (optional): required when promoting to tenant_admin
    """
    data = request.json or {}
    new_role = data.get("role")
    new_tenant_id = data.get("tenant_id")  # required for tenant_admin
    valid_roles = {"student", "professor", "tenant_admin", "superadmin"}
    if new_role not in valid_roles:
        return jsonify({"error": f"Role must be one of: {', '.join(sorted(valid_roles))}"}), 400

    if new_role == "tenant_admin" and not new_tenant_id:
        return jsonify({"error": "tenant_id is required when assigning the tenant_admin role"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE users
            SET role = %s,
                is_super_admin = %s,
                tenant_id = CASE WHEN %s IS NOT NULL THEN %s ELSE tenant_id END,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
            RETURNING user_id, name, email
            """,
            (new_role, new_role == "superadmin", new_tenant_id, new_tenant_id, user_id),
        )
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "User not found"}), 404

        audit(
            conn,
            "UPDATE_USER_ROLE",
            resource_type="user",
            resource_id=user_id,
            details={"new_role": new_role, "tenant_id": new_tenant_id},
        )
        conn.commit()
        cur.close()

        return (
            jsonify({"success": True, "message": f"Role updated to '{new_role}' for {row[1]}."}),
            200,
        )
    except Exception as e:
        logger.error("Failed to change user role: %s", e)
        return jsonify({"error": "Failed to update role"}), 500


# ---------------------------------------------------------------------------
# Force Password Reset
# ---------------------------------------------------------------------------


@bp.route("/api/superadmin/users/<user_id>/force-reset", methods=["POST"])
@csrf_exempt
@require_auth
@require_super_admin
def force_password_reset(user_id):
    """Flag a user so they must change their password on next sign-in."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE users
            SET requires_password_reset = TRUE, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
            RETURNING user_id, name, email
            """,
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "User not found"}), 404

        audit(conn, "FORCE_PASSWORD_RESET", resource_type="user", resource_id=user_id)
        conn.commit()
        cur.close()

        return jsonify({"success": True, "message": f"Password reset forced for {row[1]}."}), 200
    except Exception as e:
        logger.error("Failed to force password reset: %s", e)
        return jsonify({"error": "Failed to force password reset"}), 500


# ---------------------------------------------------------------------------
# User Data Export (GDPR)
# ---------------------------------------------------------------------------


@bp.route("/api/superadmin/users/<user_id>/export", methods=["GET"])
@require_auth
@require_super_admin
def export_user_data(user_id):
    """Export all data for a user as a JSON download (GDPR compliance)."""
    import json as _json
    from flask import Response

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Core user info
        cur.execute(
            "SELECT user_id, name, email, role, account_status, created_at, last_login FROM users WHERE user_id = %s",
            (user_id,),
        )
        u = cur.fetchone()
        if not u:
            return jsonify({"error": "User not found"}), 404

        user_data = {
            "user_id": u[0],
            "name": u[1],
            "email": u[2],
            "role": u[3],
            "account_status": u[4],
            "created_at": u[5].isoformat() if u[5] else None,
            "last_login": u[6].isoformat() if u[6] else None,
        }

        # Profile
        cur.execute("SELECT * FROM user_profiles WHERE user_id = %s", (user_id,))
        profile_row = cur.fetchone()
        profile_cols = [d[0] for d in cur.description] if profile_row else []
        user_data["profile"] = dict(zip(profile_cols, profile_row)) if profile_row else {}

        # Classes (owned)
        cur.execute(
            "SELECT class_id, name, description, created_at FROM classes WHERE professor_id = %s",
            (user_id,),
        )
        user_data["owned_classes"] = [
            {
                "class_id": r[0],
                "name": r[1],
                "description": r[2],
                "created_at": r[3].isoformat() if r[3] else None,
            }
            for r in cur.fetchall()
        ]

        # Enrollments
        cur.execute(
            """
            SELECT c.class_id, c.name
            FROM class_enrollments ce
            JOIN classes c ON c.class_id = ce.class_id
            WHERE ce.user_id = %s
            """,
            (user_id,),
        )
        user_data["enrolled_classes"] = [{"class_id": r[0], "name": r[1]} for r in cur.fetchall()]

        # Exercise attempts (last 200)
        cur.execute(
            """
            SELECT exercise_id, score, accuracy, time_spent, attempted_at
            FROM exercise_attempts
            WHERE user_id = %s
            ORDER BY attempted_at DESC
            LIMIT 200
            """,
            (user_id,),
        )
        user_data["exercise_attempts"] = [
            {
                "exercise_id": r[0],
                "score": r[1],
                "accuracy": r[2],
                "time_spent": r[3],
                "attempted_at": r[4].isoformat() if r[4] else None,
            }
            for r in cur.fetchall()
        ]

        cur.close()

        payload = _json.dumps(user_data, indent=2, default=str)
        safe_name = user_data["email"].replace("@", "_").replace(".", "_")
        return Response(
            payload,
            mimetype="application/json",
            headers={"Content-Disposition": f"attachment; filename=export_{safe_name}.json"},
        )
    except Exception as e:
        logger.error("Failed to export user data: %s", e)
        return jsonify({"error": "Export failed"}), 500


# ---------------------------------------------------------------------------
# Classes Admin API (view all + transfer ownership)
# ---------------------------------------------------------------------------


@bp.route("/api/superadmin/classes", methods=["GET"])
@require_auth
@require_super_admin
def list_all_classes():
    """List all classes across all professors with pagination."""
    try:
        page = request.args.get("page", 1, type=int)
        limit = request.args.get("limit", 50, type=int)
        q = request.args.get("q", "")
        offset = (page - 1) * limit

        conn = get_db_connection()
        cur = conn.cursor()

        where = "WHERE 1=1"
        params: list = []
        if q:
            where += " AND (c.name ILIKE %s OR u.name ILIKE %s OR u.email ILIKE %s)"
            params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])

        cur.execute(
            f"""
            SELECT c.class_id, c.name, c.description, c.created_at,
                   u.user_id AS prof_id, u.name AS prof_name, u.email AS prof_email,
                   COUNT(DISTINCT ce.student_id) AS student_count,
                   COUNT(DISTINCT cc.chapter_id) AS chapter_count,
                   COUNT(*) OVER() AS total_count
            FROM classes c
            LEFT JOIN users u ON u.user_id = c.professor_id
            LEFT JOIN class_enrollments ce ON ce.class_id = c.class_id
            LEFT JOIN class_chapters    cc ON cc.class_id = c.class_id
            {where}
            GROUP BY c.class_id, u.user_id
            ORDER BY c.created_at DESC
            LIMIT %s OFFSET %s
            """,
            params + [limit, offset],
        )
        rows = cur.fetchall()
        cur.close()

        total = rows[0][9] if rows else 0
        classes = [
            {
                "class_id": r[0],
                "name": r[1],
                "description": r[2],
                "created_at": r[3].isoformat() if r[3] else None,
                "professor_id": r[4],
                "professor_name": r[5],
                "professor_email": r[6],
                "student_count": r[7],
                "chapter_count": r[8],
            }
            for r in rows
        ]

        return (
            jsonify(
                {
                    "classes": classes,
                    "total": total,
                    "page": page,
                    "pages": max(1, (total + limit - 1) // limit),
                }
            ),
            200,
        )
    except Exception as e:
        logger.error("Failed to list classes: %s", e)
        return jsonify({"error": "Failed to list classes"}), 500


@bp.route("/api/superadmin/classes/<class_id>/transfer", methods=["PATCH"])
@csrf_exempt
@require_auth
@require_super_admin
def transfer_class(class_id):
    """Transfer a class to a different professor."""
    data = request.json or {}
    new_professor_id = data.get("professor_id")
    if not new_professor_id:
        return jsonify({"error": "professor_id is required"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Verify new owner exists and is a professor or superadmin
        cur.execute("SELECT name, role FROM users WHERE user_id = %s", (new_professor_id,))
        new_prof = cur.fetchone()
        if not new_prof:
            return jsonify({"error": "Target professor not found"}), 404
        if new_prof[1] not in ("professor", "superadmin"):
            return jsonify({"error": "Target user must be a professor or superadmin"}), 400

        cur.execute("SELECT name FROM classes WHERE class_id = %s", (class_id,))
        cls = cur.fetchone()
        if not cls:
            return jsonify({"error": "Class not found"}), 404

        cur.execute(
            """
            UPDATE classes
            SET professor_id = %s, updated_at = CURRENT_TIMESTAMP
            WHERE class_id = %s
            """,
            (new_professor_id, class_id),
        )
        audit(
            conn,
            "TRANSFER_CLASS",
            resource_type="class",
            resource_id=class_id,
            details={"new_professor": new_professor_id, "professor_name": new_prof[0]},
        )
        conn.commit()
        cur.close()

        return (
            jsonify(
                {"success": True, "message": f"Class '{cls[0]}' transferred to {new_prof[0]}."}
            ),
            200,
        )
    except Exception as e:
        logger.error("Failed to transfer class: %s", e)
        return jsonify({"error": "Failed to transfer class"}), 500


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


@bp.route("/api/superadmin/analytics", methods=["GET"])
@require_auth
@require_super_admin
def get_analytics():
    """Return platform-wide usage metrics."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Users by role
        cur.execute("SELECT role, COUNT(*) FROM users GROUP BY role")
        roles = {r[0]: r[1] for r in cur.fetchall()}

        # New users (last 7 / 30 days)
        cur.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '7 days')  AS new_7d,
                COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '30 days') AS new_30d
            FROM users
            """
        )
        new_users = cur.fetchone()

        # Active users from audit_log
        cur.execute(
            """
            SELECT
                COUNT(DISTINCT user_id) FILTER (WHERE created_at >= NOW() - INTERVAL '7 days')  AS active_7d,
                COUNT(DISTINCT user_id) FILTER (WHERE created_at >= NOW() - INTERVAL '30 days') AS active_30d
            FROM audit_log
            """
        )
        active = cur.fetchone()

        # Content totals
        cur.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM classes)          AS classes,
                (SELECT COUNT(*) FROM class_chapters)   AS chapters,
                (SELECT COUNT(*) FROM class_exercises)  AS exercises,
                (SELECT COUNT(*) FROM practice_progress WHERE completed = TRUE) AS completions
            """
        )
        content = cur.fetchone()

        # Daily registrations — last 14 days
        cur.execute(
            """
            SELECT DATE(created_at)::text, COUNT(*)
            FROM users
            WHERE created_at >= NOW() - INTERVAL '14 days'
            GROUP BY DATE(created_at)
            ORDER BY 1
            """
        )
        daily_regs = [{"date": r[0], "count": r[1]} for r in cur.fetchall()]

        # Top 5 most recent audit actions
        cur.execute(
            """
            SELECT action, COUNT(*) AS cnt
            FROM audit_log
            WHERE created_at >= NOW() - INTERVAL '7 days'
            GROUP BY action
            ORDER BY cnt DESC
            LIMIT 5
            """
        )
        top_actions = [{"action": r[0], "count": r[1]} for r in cur.fetchall()]

        cur.close()
        return (
            jsonify(
                {
                    "users": {
                        "total": sum(roles.values()),
                        "by_role": roles,
                        "new_7d": new_users[0] if new_users else 0,
                        "new_30d": new_users[1] if new_users else 0,
                        "active_7d": active[0] if active else 0,
                        "active_30d": active[1] if active else 0,
                    },
                    "content": {
                        "classes": content[0] if content else 0,
                        "chapters": content[1] if content else 0,
                        "exercises": content[2] if content else 0,
                        "completions": content[3] if content else 0,
                    },
                    "daily_registrations": daily_regs,
                    "top_actions": top_actions,
                }
            ),
            200,
        )
    except Exception as e:
        logger.error("Failed to fetch analytics: %s", e)
        return jsonify({"error": "Failed to fetch analytics"}), 500


# ---------------------------------------------------------------------------
# Announcements CRUD
# ---------------------------------------------------------------------------


@bp.route("/api/superadmin/announcements", methods=["GET"])
@require_auth
@require_super_admin
def list_announcements():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT a.announcement_id, a.title, a.message, a.type, a.target_roles,
                   a.is_active, a.expires_at, a.created_at, u.name AS created_by_name
            FROM announcements a
            LEFT JOIN users u ON u.user_id = a.created_by
            ORDER BY a.created_at DESC
            """
        )
        rows = cur.fetchall()
        cur.close()
        return (
            jsonify(
                {
                    "announcements": [
                        {
                            "id": r[0],
                            "title": r[1],
                            "message": r[2],
                            "type": r[3],
                            "target_roles": r[4] or [],
                            "is_active": r[5],
                            "expires_at": r[6].isoformat() if r[6] else None,
                            "created_at": r[7].isoformat() if r[7] else None,
                            "created_by_name": r[8],
                        }
                        for r in rows
                    ]
                }
            ),
            200,
        )
    except Exception as e:
        logger.error("Failed to list announcements: %s", e)
        return jsonify({"error": "Failed to list announcements"}), 500


@bp.route("/api/superadmin/announcements", methods=["POST"])
@csrf_exempt
@require_auth
@require_super_admin
def create_announcement():
    data = request.json or {}
    title = (data.get("title") or "").strip()
    message = (data.get("message") or "").strip()
    atype = data.get("type", "info")
    target = data.get("target_roles", [])
    expires = data.get("expires_at")

    if not title or not message:
        return jsonify({"error": "title and message are required"}), 400
    if atype not in ("info", "warning", "danger", "success"):
        return jsonify({"error": "type must be info, warning, danger, or success"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO announcements (title, message, type, target_roles, expires_at, created_by)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING announcement_id
            """,
            (title, message, atype, target or [], expires, g.user_id),
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        return jsonify({"success": True, "id": new_id}), 201
    except Exception as e:
        logger.error("Failed to create announcement: %s", e)
        return jsonify({"error": "Failed to create announcement"}), 500


@bp.route("/api/superadmin/announcements/<announcement_id>", methods=["PATCH"])
@csrf_exempt
@require_auth
@require_super_admin
def update_announcement(announcement_id):
    data = request.json or {}
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        updates, params = [], []
        for field in ("title", "message", "type", "is_active", "expires_at"):
            if field in data:
                updates.append(f"{field} = %s")
                params.append(data[field])
        if not updates:
            return jsonify({"error": "No fields to update"}), 400
        params.append(announcement_id)
        cur.execute(
            f"UPDATE announcements SET {', '.join(updates)}, updated_at = NOW() "
            f"WHERE announcement_id = %s RETURNING announcement_id",
            params,
        )
        if not cur.fetchone():
            return jsonify({"error": "Announcement not found"}), 404
        conn.commit()
        cur.close()
        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error("Failed to update announcement: %s", e)
        return jsonify({"error": "Failed to update announcement"}), 500


@bp.route("/api/superadmin/announcements/<announcement_id>", methods=["DELETE"])
@csrf_exempt
@require_auth
@require_super_admin
def delete_announcement(announcement_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM announcements WHERE announcement_id = %s RETURNING announcement_id",
            (announcement_id,),
        )
        if not cur.fetchone():
            return jsonify({"error": "Announcement not found"}), 404
        conn.commit()
        cur.close()
        return jsonify({"success": True}), 200
    except Exception as e:
        logger.error("Failed to delete announcement: %s", e)
        return jsonify({"error": "Failed to delete announcement"}), 500


# ---------------------------------------------------------------------------
# Platform Config (maintenance mode, registration gate)
# ---------------------------------------------------------------------------


@bp.route("/api/superadmin/platform-config", methods=["GET"])
@require_auth
@require_super_admin
def get_platform_config():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT key, value FROM platform_config ORDER BY key")
        config = {r[0]: r[1] for r in cur.fetchall()}
        cur.close()
        return jsonify({"config": config}), 200
    except Exception as e:
        logger.error("Failed to get platform config: %s", e)
        return jsonify({"error": "Failed to get config"}), 500


@bp.route("/api/superadmin/platform-config", methods=["PATCH"])
@csrf_exempt
@require_auth
@require_super_admin
def update_platform_config():
    data = request.json or {}
    allowed_keys = {"maintenance_mode", "maintenance_message", "registration_open"}
    updates = {k: v for k, v in data.items() if k in allowed_keys}
    if not updates:
        return jsonify({"error": "No valid config keys provided"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        for key, value in updates.items():
            cur.execute(
                """
                INSERT INTO platform_config (key, value, updated_by, updated_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (key) DO UPDATE
                    SET value = EXCLUDED.value,
                        updated_by = EXCLUDED.updated_by,
                        updated_at = NOW()
                """,
                (key, str(value), g.user_id),
            )
        conn.commit()
        cur.close()
        return jsonify({"success": True, "updated": list(updates.keys())}), 200
    except Exception as e:
        logger.error("Failed to update platform config: %s", e)
        return jsonify({"error": "Failed to update config"}), 500


# ---------------------------------------------------------------------------
# IP Blocklist
# ---------------------------------------------------------------------------


@bp.route("/api/superadmin/ip-blocklist", methods=["GET"])
@require_auth
@require_super_admin
def list_ip_blocklist():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT b.id, b.ip_address, b.reason, b.created_at, u.name AS blocked_by_name
            FROM ip_blocklist b
            LEFT JOIN users u ON u.user_id = b.blocked_by
            ORDER BY b.created_at DESC
            """
        )
        rows = cur.fetchall()
        cur.close()
        return (
            jsonify(
                {
                    "blocked": [
                        {
                            "id": r[0],
                            "ip_address": r[1],
                            "reason": r[2],
                            "created_at": r[3].isoformat() if r[3] else None,
                            "blocked_by_name": r[4],
                        }
                        for r in rows
                    ]
                }
            ),
            200,
        )
    except Exception as e:
        logger.error("Failed to list IP blocklist: %s", e)
        return jsonify({"error": "Failed to fetch IP blocklist"}), 500


@bp.route("/api/superadmin/ip-blocklist", methods=["POST"])
@csrf_exempt
@require_auth
@require_super_admin
def add_ip_to_blocklist():
    data = request.json or {}
    ip = (data.get("ip_address") or "").strip()
    reason = (data.get("reason") or "").strip()
    if not ip:
        return jsonify({"error": "ip_address is required"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO ip_blocklist (ip_address, reason, blocked_by) VALUES (%s, %s, %s) RETURNING id",
            (ip, reason, g.user_id),
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        return jsonify({"success": True, "id": new_id}), 201
    except Exception as e:
        if "unique" in str(e).lower():
            return jsonify({"error": "IP address is already blocked"}), 409
        logger.error("Failed to add IP to blocklist: %s", e)
        return jsonify({"error": "Failed to add IP"}), 500


@bp.route("/api/superadmin/ip-blocklist/<int:entry_id>", methods=["DELETE"])
@csrf_exempt
@require_auth
@require_super_admin
def remove_ip_from_blocklist(entry_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM ip_blocklist WHERE id = %s RETURNING ip_address", (entry_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "Entry not found"}), 404
        conn.commit()
        cur.close()
        return jsonify({"success": True, "message": f"Unblocked {row[0]}"}), 200
    except Exception as e:
        logger.error("Failed to remove IP from blocklist: %s", e)
        return jsonify({"error": "Failed to remove IP"}), 500
