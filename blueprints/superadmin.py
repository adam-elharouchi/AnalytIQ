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
from extensions import csrf_exempt

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
        cur.execute("""
            SELECT 
                t.tenant_id, t.name, t.lti_issuer, t.is_active, t.created_at,
                (SELECT COUNT(*) FROM users u WHERE u.tenant_id = t.tenant_id) as total_users,
                (SELECT COUNT(*) FROM classes c WHERE c.tenant_id = t.tenant_id) as total_classes
            FROM tenants t
            ORDER BY t.created_at DESC
        """)
        rows = cur.fetchall()
        cur.close()

        tenants = []
        for r in rows:
            tenants.append({
                "tenant_id": r[0],
                "name": r[1],
                "lti_issuer": r[2],
                "is_active": r[3],
                "created_at": r[4].isoformat() if r[4] else None,
                "total_users": r[5],
                "total_classes": r[6]
            })

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
                (name, lti_issuer)
            )
            row = cur.fetchone()
            
            audit(conn, "CREATE_TENANT", resource_type="tenant", resource_id=row[0], details={"name": name})
            conn.commit()
            
            tenant = {
                "tenant_id": row[0],
                "name": row[1],
                "lti_issuer": row[2],
                "is_active": row[3],
                "created_at": row[4].isoformat() if row[4] else None,
                "total_users": 0,
                "total_classes": 0
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
            
        # Count total filtered
        cur.execute(f"SELECT COUNT(*) {base_query}", params)
        total = cur.fetchone()[0]
        
        # Get Global Role Distribution (unfiltered)
        cur.execute("SELECT role, COUNT(*) FROM users GROUP BY role")
        distribution_rows = cur.fetchall()
        role_distribution = {"superadmin": 0, "professor": 0, "student": 0, "other": 0}
        for dr in distribution_rows:
            r_name = dr[0]
            if r_name in role_distribution:
                role_distribution[r_name] = dr[1]
            else:
                role_distribution["other"] += dr[1]
        query = f"""
            SELECT u.user_id, u.name, u.email, u.role, u.account_status, u.created_at,
                   t.name as tenant_name, t.tenant_id
            {base_query}
            ORDER BY u.created_at DESC
            LIMIT %s OFFSET %s
        """
        cur.execute(query, params + [limit, offset])
        rows = cur.fetchall()
        cur.close()

        users = []
        for r in rows:
            users.append({
                "user_id": r[0],
                "name": r[1],
                "email": r[2],
                "role": r[3],
                "is_super_admin": r[3] == "superadmin",
                "account_status": r[4] or "active",
                "created_at": r[5].isoformat() if r[5] else None,
                "tenant_name": r[6],
                "tenant_id": r[7]
            })

        return jsonify({
            "users": users,
            "total": total,
            "pages": (total + limit - 1) // limit,
            "current_page": page,
            "role_distribution": role_distribution
        }), 200
        
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
            (status, user_id)
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
def impersonate_user(user_id):
    """Generate a short-lived token to impersonate another user."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT user_id, name, email, role, is_super_admin FROM users WHERE user_id = %s", (user_id,))
        target_user = cur.fetchone()
        
        if not target_user:
            return jsonify({"error": "User not found"}), 404
            
        if target_user[4]: # is_super_admin
            return jsonify({"error": "Cannot impersonate another Super Admin"}), 403

        impersonator_id = getattr(g, "user_id", None)
        
        audit(conn, "IMPERSONATE_USER", resource_type="user", resource_id=user_id)
        conn.commit()
        cur.close()

        # Generate scoped token with impersonator_id baked in
        token = create_jwt_token(
            user_id=target_user[0], 
            role=target_user[3], 
            name=target_user[1], 
            email=target_user[2], 
            is_super_admin=False, # Impersonated tokens are NEVER super admin
            impersonator_id=impersonator_id
        )

        return jsonify({
            "success": True,
            "token": token,
            "message": f"You are now impersonating {target_user[1]}"
        }), 200

    except Exception as e:
        logger.error("Failed to assume impersonation: %s", e)
        return jsonify({"error": "An unexpected error occurred"}), 500

@bp.route("/api/superadmin/contact-submissions", methods=["GET"])
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
            SELECT id, name, email, subject, message, status, created_at, user_id
            FROM contact_submissions
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            (limit, offset)
        )

        submissions = []
        for r in cur.fetchall():
            submissions.append({
                "id": r[0],
                "name": r[1],
                "email": r[2],
                "subject": r[3],
                "message": r[4],
                "status": r[5],
                "created_at": r[6].isoformat() if r[6] else None,
                "user_id": r[7]
            })
            
        return jsonify({
            "submissions": submissions,
            "total": total_records,
            "page": page,
            "pages": total_pages,
            "success": True
        }), 200

    except Exception as e:
        logger.error(f"Error fetching contact submissions: {e}", exc_info=True)
        return jsonify({"error": "Failed to fetch contact submissions"}), 500
    finally:
        if conn:
            conn.close()
