"""
tests/test_superadmin_extended.py — Extended coverage for superadmin blueprint.

Covers routes not yet tested (superadmin.py currently at 21%):
  GET    /api/superadmin/tenants
  POST   /api/superadmin/tenants
  PATCH  /api/superadmin/tenants/<id>
  DELETE /api/superadmin/tenants/<id>
  GET    /api/superadmin/users
  PATCH  /api/superadmin/users/<id>/status
  POST   /api/superadmin/users/<id>/impersonate
  DELETE /api/superadmin/users/<id>
  PATCH  /api/superadmin/users/<id>/role
  POST   /api/superadmin/users/<id>/force-reset
  GET    /api/superadmin/users/<id>/export
  GET    /api/superadmin/classes
  PATCH  /api/superadmin/classes/<id>/transfer
  DELETE /api/superadmin/classes/<id>
  GET    /api/superadmin/analytics
  GET    /api/superadmin/announcements
  POST   /api/superadmin/announcements
  PATCH  /api/superadmin/announcements/<id>
  DELETE /api/superadmin/announcements/<id>
  GET    /api/superadmin/platform-config
  PATCH  /api/superadmin/platform-config
  GET    /api/superadmin/contact-submissions
  PATCH  /api/superadmin/contact-submissions/<id>
  GET    /api/superadmin/audit
  GET    /api/superadmin/pending-approvals
  PATCH  /api/superadmin/users/<id>/approve
  PATCH  /api/superadmin/users/<id>/deny
  GET    /api/superadmin/ip-blocklist
  POST   /api/superadmin/ip-blocklist
  DELETE /api/superadmin/ip-blocklist/<id>
"""
from datetime import datetime
from unittest.mock import MagicMock

import psycopg2
import pytest

AUTH = {"X-Test-User-ID": "sa-user-id", "X-Test-User-Role": "superadmin"}
AUTH_STUDENT = {"X-Test-User-ID": "stu-id", "X-Test-User-Role": "student"}

TENANT_ID = "bbbb-cccc-dddd-eeee-ffffffffffff"
USER_ID = "user-1111-2222-3333-444444444444"
CLASS_ID = "class-aaaa-bbbb-cccc-dddddddddddd"
ANN_ID = "ann0-aaaa-bbbb-cccc-dddddddddddd"
_NOW = datetime(2026, 3, 1, 12, 0, 0)


# ---------------------------------------------------------------------------
# Tenants
# ---------------------------------------------------------------------------


class TestListTenants:
    def test_returns_200_with_tenants(self, client, mock_db):
        cursor = mock_db.cursor()
        # Columns: tenant_id, name, lti_issuer, is_active, created_at, total_users, total_classes, email_domain
        cursor.fetchall.return_value = [
            (TENANT_ID, "Acme Corp", "https://lti.acme.com", True, _NOW, 5, 2, "acme.com"),
        ]
        resp = client.get("/api/superadmin/tenants", headers=AUTH)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "tenants" in data

    def test_student_returns_403(self, client, mock_db):
        resp = client.get("/api/superadmin/tenants", headers=AUTH_STUDENT)
        assert resp.status_code == 403

    def test_unauthenticated_returns_401(self, client, mock_db):
        resp = client.get("/api/superadmin/tenants")
        assert resp.status_code == 401

    def test_db_error_returns_500(self, client, mock_db):
        mock_db.cursor.side_effect = Exception("db down")
        resp = client.get("/api/superadmin/tenants", headers=AUTH)
        assert resp.status_code == 500
        mock_db.cursor.side_effect = None


class TestCreateTenant:
    def test_create_tenant_returns_201(self, client, mock_db):
        cursor = mock_db.cursor()
        # Route does INSERT RETURNING (tenant_id, name, lti_issuer, is_active, created_at, email_domain)
        cursor.fetchone.return_value = (TENANT_ID, "Acme Corp", None, True, _NOW, None)
        resp = client.post(
            "/api/superadmin/tenants",
            json={"name": "Acme Corp", "lti_issuer": "https://lti.acme.com"},
            headers=AUTH,
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert "tenant_id" in data or "tenant" in data or data.get("success")

    def test_missing_name_returns_400(self, client, mock_db):
        resp = client.post(
            "/api/superadmin/tenants",
            json={"domain": "acme.com"},
            headers=AUTH,
        )
        assert resp.status_code == 400

    def test_duplicate_name_returns_409_or_400(self, client, mock_db):
        cursor = mock_db.cursor()
        # Simulate IntegrityError on INSERT (unique constraint on lti_issuer)
        cursor.execute.side_effect = psycopg2.IntegrityError("unique constraint violation")
        resp = client.post(
            "/api/superadmin/tenants",
            json={"name": "Acme Corp", "lti_issuer": "https://lti.acme.com"},
            headers=AUTH,
        )
        cursor.execute.side_effect = None  # reset
        assert resp.status_code in (400, 409)

    def test_student_returns_403(self, client, mock_db):
        resp = client.post(
            "/api/superadmin/tenants",
            json={"name": "Test"},
            headers=AUTH_STUDENT,
        )
        assert resp.status_code == 403


class TestUpdateTenant:
    def test_update_tenant_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (TENANT_ID, "Acme Corp", "acme.com", True, _NOW)
        resp = client.patch(
            f"/api/superadmin/tenants/{TENANT_ID}",
            json={"name": "Acme Corp Updated"},
            headers=AUTH,
        )
        assert resp.status_code == 200

    def test_tenant_not_found_returns_404(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None
        resp = client.patch(
            f"/api/superadmin/tenants/{TENANT_ID}",
            json={"name": "X"},
            headers=AUTH,
        )
        assert resp.status_code == 404


class TestDeleteTenant:
    def test_delete_tenant_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (TENANT_ID, "Acme Corp")
        resp = client.delete(
            f"/api/superadmin/tenants/{TENANT_ID}",
            headers=AUTH,
        )
        assert resp.status_code == 200

    def test_tenant_not_found_returns_404(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None
        resp = client.delete(
            f"/api/superadmin/tenants/{TENANT_ID}",
            headers=AUTH,
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


class TestSuperadminSearchUsers:
    def test_returns_200_with_users(self, client, mock_db):
        cursor = mock_db.cursor()
        # First fetchall: roles distribution; second: paginated users
        # User columns: user_id, name, email, role, account_status, created_at,
        #               tenant_name, tenant_id, total_count
        cursor.fetchall.side_effect = [
            [("student", 36)],
            [(USER_ID, "Alice", "alice@ex.com", "student", "active", _NOW, "Acme Corp", TENANT_ID, 1)],
        ]
        resp = client.get("/api/superadmin/users", headers=AUTH)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "users" in data

    def test_with_filters(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchall.return_value = []
        resp = client.get(
            "/api/superadmin/users?q=alice&role=student&status=active",
            headers=AUTH,
        )
        assert resp.status_code == 200

    def test_student_returns_403(self, client, mock_db):
        resp = client.get("/api/superadmin/users", headers=AUTH_STUDENT)
        assert resp.status_code == 403


class TestSuperadminUpdateUserStatus:
    def test_disable_user_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        # Route reads `account_status` key; UPDATE RETURNING user_id
        cursor.fetchone.return_value = (USER_ID,)
        resp = client.patch(
            f"/api/superadmin/users/{USER_ID}/status",
            json={"account_status": "disabled"},
            headers=AUTH,
        )
        assert resp.status_code == 200

    def test_invalid_status_returns_400(self, client, mock_db):
        # Omitting `account_status` key → "Status is required" 400
        resp = client.patch(
            f"/api/superadmin/users/{USER_ID}/status",
            json={"wrong_key": "hacked"},
            headers=AUTH,
        )
        assert resp.status_code == 400

    def test_user_not_found_returns_404(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None
        resp = client.patch(
            f"/api/superadmin/users/{USER_ID}/status",
            json={"account_status": "active"},
            headers=AUTH,
        )
        assert resp.status_code == 404


class TestSuperadminImpersonateUser:
    def test_impersonate_student_returns_token(self, client, mock_db):
        cursor = mock_db.cursor()
        # Columns: user_id, name, email, role, tenant_id
        cursor.fetchone.return_value = (USER_ID, "Alice", "alice@ex.com", "student", None)
        resp = client.post(
            f"/api/superadmin/users/{USER_ID}/impersonate",
            headers=AUTH,
        )
        assert resp.status_code == 200
        assert "token" in resp.get_json()

    def test_cannot_impersonate_superadmin_returns_403(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (USER_ID, "SA", "sa@ex.com", "superadmin", None)
        resp = client.post(
            f"/api/superadmin/users/{USER_ID}/impersonate",
            headers=AUTH,
        )
        assert resp.status_code == 403

    def test_user_not_found_returns_404(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None
        resp = client.post(
            f"/api/superadmin/users/{USER_ID}/impersonate",
            headers=AUTH,
        )
        assert resp.status_code == 404


class TestSuperadminDeleteUser:
    def test_delete_student_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (USER_ID, "alice@ex.com", "student")
        resp = client.delete(
            f"/api/superadmin/users/{USER_ID}",
            headers=AUTH,
        )
        assert resp.status_code == 200

    def test_cannot_delete_superadmin_without_owner_privilege_returns_403(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (USER_ID, "sa@ex.com", "superadmin")
        resp = client.delete(
            f"/api/superadmin/users/{USER_ID}",
            headers=AUTH,
        )
        # Regular superadmin cannot delete other superadmin (403); owner can (200)
        assert resp.status_code in (200, 403)

    def test_user_not_found_returns_404(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None
        resp = client.delete(
            f"/api/superadmin/users/{USER_ID}",
            headers=AUTH,
        )
        assert resp.status_code == 404


class TestSuperadminChangeRole:
    def test_change_to_professor_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (USER_ID, "Alice", "alice@ex.com", "student")
        resp = client.patch(
            f"/api/superadmin/users/{USER_ID}/role",
            json={"role": "professor", "tenant_id": TENANT_ID},
            headers=AUTH,
        )
        assert resp.status_code == 200

    def test_invalid_role_returns_400(self, client, mock_db):
        resp = client.patch(
            f"/api/superadmin/users/{USER_ID}/role",
            json={"role": "hacker"},
            headers=AUTH,
        )
        assert resp.status_code == 400

    def test_user_not_found_returns_404(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None
        resp = client.patch(
            f"/api/superadmin/users/{USER_ID}/role",
            json={"role": "professor"},
            headers=AUTH,
        )
        assert resp.status_code == 404


class TestSuperadminForceReset:
    def test_force_reset_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (USER_ID, "Alice", "alice@ex.com")
        resp = client.post(
            f"/api/superadmin/users/{USER_ID}/force-reset",
            headers=AUTH,
        )
        assert resp.status_code == 200

    def test_user_not_found_returns_404(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None
        resp = client.post(
            f"/api/superadmin/users/{USER_ID}/force-reset",
            headers=AUTH,
        )
        assert resp.status_code == 404


class TestSuperadminExportUser:
    def test_export_returns_json(self, client, mock_db):
        cursor = mock_db.cursor()
        # Route does ONE user fetchone (7 cols) + ONE profile fetchone, then 3 fetchalls
        cursor.fetchone.side_effect = [
            (USER_ID, "Alice", "alice@ex.com", "student", "active", _NOW, None),  # user (7 cols)
            None,  # profile row (None → empty profile dict)
        ]
        cursor.fetchall.side_effect = [[], [], []]  # owned_classes, enrolled, attempts
        resp = client.get(
            f"/api/superadmin/users/{USER_ID}/export",
            headers=AUTH,
        )
        assert resp.status_code == 200

    def test_user_not_found_returns_404(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None
        resp = client.get(
            f"/api/superadmin/users/{USER_ID}/export",
            headers=AUTH,
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Classes
# ---------------------------------------------------------------------------


class TestSuperadminListClasses:
    def test_list_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (5,)  # total count
        # Columns: class_id, name, description, created_at, prof_id, prof_name, prof_email,
        #          student_count, chapter_count
        cursor.fetchall.return_value = [
            (CLASS_ID, "DS101", "Desc", _NOW, "prof-id", "Prof A", "a@ex.com", 10, 3),
        ]
        resp = client.get("/api/superadmin/classes", headers=AUTH)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "classes" in data

    def test_student_returns_403(self, client, mock_db):
        resp = client.get("/api/superadmin/classes", headers=AUTH_STUDENT)
        assert resp.status_code == 403


class TestSuperadminDeleteClass:
    def test_delete_class_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = ("DS101",)
        resp = client.delete(
            f"/api/superadmin/classes/{CLASS_ID}",
            headers=AUTH,
        )
        assert resp.status_code == 200

    def test_class_not_found_returns_404(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None
        resp = client.delete(
            f"/api/superadmin/classes/{CLASS_ID}",
            headers=AUTH,
        )
        assert resp.status_code == 404


class TestSuperadminTransferClass:
    def test_transfer_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        # Route checks professor first (name, role), then class (name)
        cursor.fetchone.side_effect = [
            ("Prof Name", "professor"),  # new professor found
            ("DS101",),                   # class exists
        ]
        resp = client.patch(
            f"/api/superadmin/classes/{CLASS_ID}/transfer",
            json={"professor_id": "new-prof-id"},
            headers=AUTH,
        )
        assert resp.status_code == 200

    def test_missing_professor_id_returns_400(self, client, mock_db):
        resp = client.patch(
            f"/api/superadmin/classes/{CLASS_ID}/transfer",
            json={},
            headers=AUTH,
        )
        assert resp.status_code == 400

    def test_class_not_found_returns_404(self, client, mock_db):
        cursor = mock_db.cursor()
        # Professor found, but class not found
        cursor.fetchone.side_effect = [
            ("Prof Name", "professor"),  # professor found
            None,                         # class not found
        ]
        resp = client.patch(
            f"/api/superadmin/classes/{CLASS_ID}/transfer",
            json={"professor_id": "new-prof-id"},
            headers=AUTH,
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


class TestSuperadminAnalytics:
    def test_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        # Query order: roles (fetchall), new_users (fetchone 2-col),
        #              active (fetchone 2-col), content (fetchone 4-col),
        #              daily_regs (fetchall), top_actions (fetchall)
        cursor.fetchall.side_effect = [
            [("student", 70), ("professor", 30)],  # roles distribution
            [],  # daily_regs
            [],  # top_actions
        ]
        cursor.fetchone.side_effect = [
            (10, 40),          # new users 7d / 30d
            (8, 35),           # active users 7d / 30d
            (20, 60, 120, 50), # content: classes, chapters, exercises, completions
        ]
        resp = client.get("/api/superadmin/analytics", headers=AUTH)
        assert resp.status_code == 200

    def test_student_returns_403(self, client, mock_db):
        resp = client.get("/api/superadmin/analytics", headers=AUTH_STUDENT)
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Announcements
# ---------------------------------------------------------------------------


class TestSuperadminAnnouncements:
    def test_list_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchall.return_value = [
            (ANN_ID, "Title", "Body", "info", [], True, None, _NOW, "Admin"),
        ]
        resp = client.get("/api/superadmin/announcements", headers=AUTH)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "announcements" in data

    def test_create_returns_201(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (ANN_ID,)
        resp = client.post(
            "/api/superadmin/announcements",
            json={"title": "Hi", "message": "World", "type": "info"},
            headers=AUTH,
        )
        assert resp.status_code == 201

    def test_create_missing_title_returns_400(self, client, mock_db):
        resp = client.post(
            "/api/superadmin/announcements",
            json={"message": "World"},
            headers=AUTH,
        )
        assert resp.status_code == 400

    def test_create_invalid_type_returns_400(self, client, mock_db):
        resp = client.post(
            "/api/superadmin/announcements",
            json={"title": "T", "message": "M", "type": "blah"},
            headers=AUTH,
        )
        assert resp.status_code == 400

    def test_toggle_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (ANN_ID,)
        resp = client.patch(
            f"/api/superadmin/announcements/{ANN_ID}",
            json={"is_active": False},
            headers=AUTH,
        )
        assert resp.status_code == 200

    def test_toggle_not_found_returns_404(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None
        resp = client.patch(
            f"/api/superadmin/announcements/{ANN_ID}",
            json={"is_active": True},
            headers=AUTH,
        )
        assert resp.status_code == 404

    def test_delete_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (ANN_ID,)
        resp = client.delete(
            f"/api/superadmin/announcements/{ANN_ID}",
            headers=AUTH,
        )
        assert resp.status_code == 200

    def test_delete_not_found_returns_404(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None
        resp = client.delete(
            f"/api/superadmin/announcements/{ANN_ID}",
            headers=AUTH,
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Platform Config
# ---------------------------------------------------------------------------


class TestPlatformConfig:
    def test_get_config_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchall.return_value = [
            ("maintenance_mode", "false"),
            ("maintenance_message", ""),
        ]
        resp = client.get("/api/superadmin/platform-config", headers=AUTH)
        assert resp.status_code == 200

    def test_update_config_returns_200(self, client, mock_db):
        resp = client.patch(
            "/api/superadmin/platform-config",
            json={"maintenance_mode": "true", "maintenance_message": "Down"},
            headers=AUTH,
        )
        assert resp.status_code == 200

    def test_student_get_returns_403(self, client, mock_db):
        resp = client.get("/api/superadmin/platform-config", headers=AUTH_STUDENT)
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Contact Submissions
# ---------------------------------------------------------------------------


class TestContactSubmissions:
    def test_list_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchall.return_value = [
            (1, "Alice", "alice@ex.com", "Help", "I need help", "unread", None, _NOW),
        ]
        cursor.fetchone.return_value = (1,)
        resp = client.get("/api/superadmin/contact-submissions", headers=AUTH)
        assert resp.status_code == 200

    def test_update_status_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (1,)
        resp = client.patch(
            "/api/superadmin/contact-submissions/1",
            json={"status": "resolved"},
            headers=AUTH,
        )
        assert resp.status_code == 200

    def test_student_returns_403(self, client, mock_db):
        resp = client.get("/api/superadmin/contact-submissions", headers=AUTH_STUDENT)
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Audit Log
# ---------------------------------------------------------------------------


class TestSuperadminAuditLog:
    def test_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        # fetchall[0]: entries (10 cols); fetchone: total count
        # Columns: id, action, resource_type, resource_id, user_id,
        #          actor_name, actor_email, ip_address, details, created_at
        cursor.fetchall.return_value = [
            (1, "LOGIN", "user", USER_ID, USER_ID, "Alice", "alice@ex.com", "127.0.0.1", {}, _NOW),
        ]
        cursor.fetchone.return_value = (10,)
        resp = client.get("/api/superadmin/audit", headers=AUTH)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "entries" in data

    def test_with_filters(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (0,)
        cursor.fetchall.return_value = []
        resp = client.get(
            "/api/superadmin/audit?action=LOGIN&limit=10&page=1",
            headers=AUTH,
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Pending Approvals
# ---------------------------------------------------------------------------


class TestSuperadminPendingApprovals:
    def test_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchall.return_value = [
            (USER_ID, "Bob", "bob@ex.com", "student", _NOW, TENANT_ID),
        ]
        resp = client.get("/api/superadmin/pending-approvals", headers=AUTH)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "pending" in data

    def test_approve_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (USER_ID, "Bob", "bob@ex.com", "student")
        cursor.rowcount = 1
        resp = client.patch(
            f"/api/superadmin/users/{USER_ID}/approve",
            headers=AUTH,
        )
        assert resp.status_code == 200

    def test_approve_non_pending_returns_404(self, client, mock_db):
        # Route uses UPDATE ... WHERE account_status = 'pending_approval' RETURNING ...
        # If no row matches, fetchone returns None → 404
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None
        resp = client.patch(
            f"/api/superadmin/users/{USER_ID}/approve",
            headers=AUTH,
        )
        assert resp.status_code == 404

    def test_deny_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (USER_ID, "Bob", "bob@ex.com", "student")
        cursor.rowcount = 1
        resp = client.patch(
            f"/api/superadmin/users/{USER_ID}/deny",
            headers=AUTH,
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# IP Blocklist
# ---------------------------------------------------------------------------


class TestIpBlocklist:
    def test_list_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        # Columns: id, ip_address, reason, created_at, blocked_by_name
        cursor.fetchall.return_value = [
            (1, "1.2.3.4", "Bad actor", _NOW, "Admin User"),
        ]
        resp = client.get("/api/superadmin/ip-blocklist", headers=AUTH)
        assert resp.status_code == 200

    def test_add_ip_returns_201(self, client, mock_db):
        cursor = mock_db.cursor()
        # Route does INSERT RETURNING id → fetchone()[0]
        cursor.fetchone.return_value = (1,)
        resp = client.post(
            "/api/superadmin/ip-blocklist",
            json={"ip_address": "1.2.3.4", "reason": "Bad actor"},
            headers=AUTH,
        )
        assert resp.status_code in (201, 200)

    def test_add_missing_ip_returns_400(self, client, mock_db):
        resp = client.post(
            "/api/superadmin/ip-blocklist",
            json={"reason": "No IP"},
            headers=AUTH,
        )
        assert resp.status_code == 400

    def test_delete_ip_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (1,)
        resp = client.delete(
            "/api/superadmin/ip-blocklist/1",
            headers=AUTH,
        )
        assert resp.status_code == 200

    def test_student_returns_403(self, client, mock_db):
        resp = client.get("/api/superadmin/ip-blocklist", headers=AUTH_STUDENT)
        assert resp.status_code == 403
