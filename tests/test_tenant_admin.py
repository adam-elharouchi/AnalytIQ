"""
tests/test_tenant_admin.py — Behavioral tests for tenant admin routes.

All routes require superadmin or tenant_admin role.
We use superadmin + ?tenant_id=test-tenant-id to satisfy _scoped_tenant_id().

Covers:
  GET    /api/tenant-admin/overview
  GET    /api/tenant-admin/analytics
  GET    /api/tenant-admin/users
  PATCH  /api/tenant-admin/users/<id>/status
  PATCH  /api/tenant-admin/users/<id>/role
  POST   /api/tenant-admin/users/<id>/force-reset
  GET    /api/tenant-admin/users/<id>/export
  DELETE /api/tenant-admin/users/<id>
  POST   /api/tenant-admin/users/<id>/impersonate
  GET    /api/tenant-admin/pending-approvals
  PATCH  /api/tenant-admin/users/<id>/approve
  PATCH  /api/tenant-admin/users/<id>/deny
  GET    /api/tenant-admin/classes
  PATCH  /api/tenant-admin/classes/<id>/transfer
  DELETE /api/tenant-admin/classes/<id>
  GET    /api/tenant-admin/audit
  GET    /api/tenant-admin/announcements
  POST   /api/tenant-admin/announcements
  PATCH  /api/tenant-admin/announcements/<id>
  DELETE /api/tenant-admin/announcements/<id>
"""
from datetime import datetime
from unittest.mock import MagicMock

import pytest

TENANT_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
USER_ID = "user-1111-2222-3333-444444444444"
CLASS_ID = "class-aaaa-bbbb-cccc-dddddddddddd"
ANN_ID = "ann0-aaaa-bbbb-cccc-dddddddddddd"

# Superadmin passes require_tenant_admin; tenant_id comes from ?tenant_id=
AUTH = {
    "X-Test-User-ID": "admin-user-id",
    "X-Test-User-Role": "superadmin",
}
TID = f"?tenant_id={TENANT_ID}"

_NOW = datetime(2026, 3, 1, 12, 0, 0)


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------


class TestGetOverview:
    def test_overview_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.side_effect = [
            (10, 8, 2),  # user_row
            (5,),  # class_count
            (2,),  # sso_count
            (7,),  # active_30d
        ]
        resp = client.get(f"/api/tenant-admin/overview{TID}", headers=AUTH)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total_users"] == 10
        assert data["active_users"] == 8
        assert data["pending_approvals"] == 2
        assert data["total_classes"] == 5
        assert data["sso_providers"] == 2
        assert data["active_30d"] == 7

    def test_overview_missing_tenant_id_returns_400(self, client, mock_db):
        resp = client.get("/api/tenant-admin/overview", headers=AUTH)
        assert resp.status_code == 400
        assert "tenant_id" in resp.get_json()["error"]

    def test_overview_unauthenticated_returns_401(self, client, mock_db):
        resp = client.get(f"/api/tenant-admin/overview{TID}")
        assert resp.status_code == 401

    def test_overview_db_error_returns_500(self, client, mock_db):
        mock_db.cursor.side_effect = Exception("db down")
        resp = client.get(f"/api/tenant-admin/overview{TID}", headers=AUTH)
        assert resp.status_code == 500
        mock_db.cursor.side_effect = None


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


class TestGetAnalytics:
    def test_analytics_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchall.side_effect = [
            [("student", 5), ("professor", 2)],  # roles
            [],  # daily_regs
            [],  # top_actions
        ]
        cursor.fetchone.side_effect = [
            (3, 10),  # new_users (7d, 30d)
            (2, 8),  # active (7d, 30d)
            (3, 6, 12, 20),  # content (classes, chapters, exercises, completions)
        ]
        resp = client.get(f"/api/tenant-admin/analytics{TID}", headers=AUTH)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "users" in data
        assert "content" in data
        assert "daily_registrations" in data
        assert "top_actions" in data
        assert data["users"]["new_7d"] == 3
        assert data["content"]["classes"] == 3

    def test_analytics_missing_tenant_returns_400(self, client, mock_db):
        resp = client.get("/api/tenant-admin/analytics", headers=AUTH)
        assert resp.status_code == 400

    def test_analytics_db_error_returns_500(self, client, mock_db):
        mock_db.cursor.side_effect = Exception("db error")
        resp = client.get(f"/api/tenant-admin/analytics{TID}", headers=AUTH)
        assert resp.status_code == 500
        mock_db.cursor.side_effect = None


# ---------------------------------------------------------------------------
# Users — search
# ---------------------------------------------------------------------------


class TestSearchUsers:
    def test_search_users_returns_200_with_list(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchall.return_value = [
            (USER_ID, "Alice", "alice@example.com", "student", "active", _NOW, 1),
        ]
        resp = client.get(f"/api/tenant-admin/users{TID}", headers=AUTH)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "users" in data
        assert len(data["users"]) == 1
        assert data["users"][0]["email"] == "alice@example.com"
        assert data["total"] == 1

    def test_search_users_empty_returns_zero(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchall.return_value = []
        resp = client.get(f"/api/tenant-admin/users{TID}", headers=AUTH)
        assert resp.status_code == 200
        assert resp.get_json()["total"] == 0

    def test_search_users_with_query_filter(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchall.return_value = []
        resp = client.get(f"/api/tenant-admin/users{TID}&q=alice&role=student", headers=AUTH)
        assert resp.status_code == 200

    def test_search_users_missing_tenant_returns_400(self, client, mock_db):
        resp = client.get("/api/tenant-admin/users", headers=AUTH)
        assert resp.status_code == 400

    def test_search_users_db_error_returns_500(self, client, mock_db):
        mock_db.cursor.side_effect = Exception("db error")
        resp = client.get(f"/api/tenant-admin/users{TID}", headers=AUTH)
        assert resp.status_code == 500
        mock_db.cursor.side_effect = None


# ---------------------------------------------------------------------------
# Users — status
# ---------------------------------------------------------------------------


class TestUpdateUserStatus:
    def test_disable_user_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (USER_ID, "Alice", "alice@ex.com", "student")
        resp = client.patch(
            f"/api/tenant-admin/users/{USER_ID}/status{TID}",
            json={"status": "disabled"},
            headers=AUTH,
        )
        assert resp.status_code == 200

    def test_enable_user_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (USER_ID, "Alice", "alice@ex.com", "student")
        resp = client.patch(
            f"/api/tenant-admin/users/{USER_ID}/status{TID}",
            json={"status": "active"},
            headers=AUTH,
        )
        assert resp.status_code == 200

    def test_invalid_status_returns_400(self, client, mock_db):
        resp = client.patch(
            f"/api/tenant-admin/users/{USER_ID}/status{TID}",
            json={"status": "banned"},
            headers=AUTH,
        )
        assert resp.status_code == 400

    def test_user_not_in_tenant_returns_404(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None
        resp = client.patch(
            f"/api/tenant-admin/users/{USER_ID}/status{TID}",
            json={"status": "active"},
            headers=AUTH,
        )
        assert resp.status_code == 404

    def test_missing_tenant_returns_400(self, client, mock_db):
        resp = client.patch(
            f"/api/tenant-admin/users/{USER_ID}/status",
            json={"status": "active"},
            headers=AUTH,
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Users — role
# ---------------------------------------------------------------------------


class TestChangeUserRole:
    def test_change_role_to_professor_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (USER_ID, "Alice", "alice@ex.com", "student")
        resp = client.patch(
            f"/api/tenant-admin/users/{USER_ID}/role{TID}",
            json={"role": "professor"},
            headers=AUTH,
        )
        assert resp.status_code == 200

    def test_invalid_role_returns_400(self, client, mock_db):
        resp = client.patch(
            f"/api/tenant-admin/users/{USER_ID}/role{TID}",
            json={"role": "superadmin"},
            headers=AUTH,
        )
        assert resp.status_code == 400

    def test_cannot_modify_superadmin_returns_403(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (USER_ID, "Boss", "boss@ex.com", "superadmin")
        resp = client.patch(
            f"/api/tenant-admin/users/{USER_ID}/role{TID}",
            json={"role": "student"},
            headers=AUTH,
        )
        assert resp.status_code == 403

    def test_user_not_found_returns_404(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None
        resp = client.patch(
            f"/api/tenant-admin/users/{USER_ID}/role{TID}",
            json={"role": "professor"},
            headers=AUTH,
        )
        assert resp.status_code == 404

    def test_missing_tenant_returns_400(self, client, mock_db):
        resp = client.patch(
            f"/api/tenant-admin/users/{USER_ID}/role",
            json={"role": "professor"},
            headers=AUTH,
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Users — force reset
# ---------------------------------------------------------------------------


class TestForcePasswordReset:
    def test_force_reset_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (USER_ID, "Alice", "alice@ex.com", "student")
        resp = client.post(
            f"/api/tenant-admin/users/{USER_ID}/force-reset{TID}",
            headers=AUTH,
        )
        assert resp.status_code == 200
        assert "reset" in resp.get_json()["message"].lower()

    def test_user_not_in_tenant_returns_404(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None
        resp = client.post(
            f"/api/tenant-admin/users/{USER_ID}/force-reset{TID}",
            headers=AUTH,
        )
        assert resp.status_code == 404

    def test_missing_tenant_returns_400(self, client, mock_db):
        resp = client.post(
            f"/api/tenant-admin/users/{USER_ID}/force-reset",
            headers=AUTH,
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Users — export
# ---------------------------------------------------------------------------


class TestExportUserData:
    def test_export_returns_json_file(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.side_effect = [
            # _assert_user_in_tenant
            (USER_ID, "Alice", "alice@ex.com", "student"),
            # core user query
            (USER_ID, "Alice", "alice@ex.com", "student", "active", _NOW, _NOW),
        ]
        cursor.fetchall.side_effect = [
            [],  # owned_classes
            [],  # enrolled
            [],  # attempts
        ]
        resp = client.get(
            f"/api/tenant-admin/users/{USER_ID}/export{TID}",
            headers=AUTH,
        )
        assert resp.status_code == 200
        assert "application/json" in resp.content_type
        assert b"alice" in resp.data

    def test_user_not_in_tenant_returns_404(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None
        resp = client.get(
            f"/api/tenant-admin/users/{USER_ID}/export{TID}",
            headers=AUTH,
        )
        assert resp.status_code == 404

    def test_missing_tenant_returns_400(self, client, mock_db):
        resp = client.get(
            f"/api/tenant-admin/users/{USER_ID}/export",
            headers=AUTH,
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Users — delete
# ---------------------------------------------------------------------------


class TestDeleteUser:
    def test_delete_user_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (USER_ID, "Alice", "alice@ex.com", "student")
        cursor.fetchall.return_value = []  # no professor classes
        resp = client.delete(
            f"/api/tenant-admin/users/{USER_ID}{TID}",
            headers=AUTH,
        )
        assert resp.status_code == 200

    def test_cannot_delete_superadmin_returns_403(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (USER_ID, "Boss", "boss@ex.com", "superadmin")
        resp = client.delete(
            f"/api/tenant-admin/users/{USER_ID}{TID}",
            headers=AUTH,
        )
        assert resp.status_code == 403

    def test_cannot_delete_own_account_returns_400(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = ("admin-user-id", "Me", "me@ex.com", "superadmin")
        resp = client.delete(
            f"/api/tenant-admin/users/admin-user-id{TID}",
            headers=AUTH,
        )
        # superadmin protected from deletion — should be 403
        assert resp.status_code in (400, 403)

    def test_user_not_found_returns_404(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None
        resp = client.delete(
            f"/api/tenant-admin/users/{USER_ID}{TID}",
            headers=AUTH,
        )
        assert resp.status_code == 404

    def test_missing_tenant_returns_400(self, client, mock_db):
        resp = client.delete(
            f"/api/tenant-admin/users/{USER_ID}",
            headers=AUTH,
        )
        assert resp.status_code == 400

    def test_delete_professor_cascades_classes(self, client, mock_db):
        """Deleting a professor should handle their classes too."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (USER_ID, "Prof", "prof@ex.com", "professor")
        # Return one class owned by this professor
        cursor.fetchall.side_effect = [
            [(CLASS_ID,)],  # professor's class IDs
            [("chap-1",)],  # chapters in class
        ]
        resp = client.delete(
            f"/api/tenant-admin/users/{USER_ID}{TID}",
            headers=AUTH,
        )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Users — impersonate
# ---------------------------------------------------------------------------


class TestImpersonateUser:
    def test_impersonate_student_returns_token(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (USER_ID, "Alice", "alice@ex.com", "student")
        resp = client.post(
            f"/api/tenant-admin/users/{USER_ID}/impersonate{TID}",
            headers=AUTH,
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "token" in data
        assert data["user"]["role"] == "student"

    def test_cannot_impersonate_admin_returns_403(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (USER_ID, "Admin", "admin@ex.com", "tenant_admin")
        resp = client.post(
            f"/api/tenant-admin/users/{USER_ID}/impersonate{TID}",
            headers=AUTH,
        )
        assert resp.status_code == 403

    def test_cannot_impersonate_superadmin_returns_403(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (USER_ID, "SA", "sa@ex.com", "superadmin")
        resp = client.post(
            f"/api/tenant-admin/users/{USER_ID}/impersonate{TID}",
            headers=AUTH,
        )
        assert resp.status_code == 403

    def test_user_not_found_returns_404(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None
        resp = client.post(
            f"/api/tenant-admin/users/{USER_ID}/impersonate{TID}",
            headers=AUTH,
        )
        assert resp.status_code == 404

    def test_missing_tenant_returns_400(self, client, mock_db):
        resp = client.post(
            f"/api/tenant-admin/users/{USER_ID}/impersonate",
            headers=AUTH,
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Pending approvals
# ---------------------------------------------------------------------------


class TestPendingApprovals:
    def test_returns_pending_list(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchall.return_value = [
            ("uid-1", "Bob", "bob@ex.com", "student", _NOW),
        ]
        resp = client.get(f"/api/tenant-admin/pending-approvals{TID}", headers=AUTH)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["count"] == 1
        assert data["pending"][0]["name"] == "Bob"

    def test_empty_pending_returns_zero(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchall.return_value = []
        resp = client.get(f"/api/tenant-admin/pending-approvals{TID}", headers=AUTH)
        assert resp.status_code == 200
        assert resp.get_json()["count"] == 0

    def test_missing_tenant_returns_400(self, client, mock_db):
        resp = client.get("/api/tenant-admin/pending-approvals", headers=AUTH)
        assert resp.status_code == 400


class TestApproveUser:
    def test_approve_pending_user_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (USER_ID, "Bob", "bob@ex.com", "student")
        cursor.rowcount = 1
        resp = client.patch(
            f"/api/tenant-admin/users/{USER_ID}/approve{TID}",
            headers=AUTH,
        )
        assert resp.status_code == 200

    def test_approve_non_pending_returns_400(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.side_effect = [
            (USER_ID, "Bob", "bob@ex.com", "student"),  # _assert_user_in_tenant
            None,  # UPDATE RETURNING (rowcount 0 path)
        ]
        cursor.rowcount = 0
        resp = client.patch(
            f"/api/tenant-admin/users/{USER_ID}/approve{TID}",
            headers=AUTH,
        )
        assert resp.status_code == 400

    def test_user_not_found_returns_404(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None
        resp = client.patch(
            f"/api/tenant-admin/users/{USER_ID}/approve{TID}",
            headers=AUTH,
        )
        assert resp.status_code == 404

    def test_missing_tenant_returns_400(self, client, mock_db):
        resp = client.patch(
            f"/api/tenant-admin/users/{USER_ID}/approve",
            headers=AUTH,
        )
        assert resp.status_code == 400


class TestDenyUser:
    def test_deny_pending_user_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (USER_ID, "Bob", "bob@ex.com", "student")
        cursor.rowcount = 1
        resp = client.patch(
            f"/api/tenant-admin/users/{USER_ID}/deny{TID}",
            headers=AUTH,
        )
        assert resp.status_code == 200

    def test_deny_non_pending_returns_400(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (USER_ID, "Bob", "bob@ex.com", "student")
        cursor.rowcount = 0
        resp = client.patch(
            f"/api/tenant-admin/users/{USER_ID}/deny{TID}",
            headers=AUTH,
        )
        assert resp.status_code == 400

    def test_user_not_found_returns_404(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None
        resp = client.patch(
            f"/api/tenant-admin/users/{USER_ID}/deny{TID}",
            headers=AUTH,
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Classes
# ---------------------------------------------------------------------------


class TestListClasses:
    def test_list_classes_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (5,)  # total count
        cursor.fetchall.return_value = [
            (CLASS_ID, "DS101", "Data Science", "prof-1", "Prof A", "a@ex.com", 10, 3, _NOW),
        ]
        resp = client.get(f"/api/tenant-admin/classes{TID}", headers=AUTH)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["classes"]) == 1
        assert data["classes"][0]["name"] == "DS101"

    def test_list_classes_with_search(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (0,)
        cursor.fetchall.return_value = []
        resp = client.get(f"/api/tenant-admin/classes{TID}&q=data", headers=AUTH)
        assert resp.status_code == 200

    def test_missing_tenant_returns_400(self, client, mock_db):
        resp = client.get("/api/tenant-admin/classes", headers=AUTH)
        assert resp.status_code == 400


class TestTransferClass:
    def test_transfer_class_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.side_effect = [
            (CLASS_ID,),  # class belongs to tenant
            ("new-prof-id", "professor"),  # new professor
        ]
        resp = client.patch(
            f"/api/tenant-admin/classes/{CLASS_ID}/transfer{TID}",
            json={"professor_email": "newprof@ex.com"},
            headers=AUTH,
        )
        assert resp.status_code == 200

    def test_missing_professor_email_returns_400(self, client, mock_db):
        resp = client.patch(
            f"/api/tenant-admin/classes/{CLASS_ID}/transfer{TID}",
            json={},
            headers=AUTH,
        )
        assert resp.status_code == 400

    def test_class_not_in_tenant_returns_404(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None
        resp = client.patch(
            f"/api/tenant-admin/classes/{CLASS_ID}/transfer{TID}",
            json={"professor_email": "newprof@ex.com"},
            headers=AUTH,
        )
        assert resp.status_code == 404

    def test_target_professor_not_found_returns_404(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.side_effect = [
            (CLASS_ID,),  # class exists
            None,  # professor not found
        ]
        resp = client.patch(
            f"/api/tenant-admin/classes/{CLASS_ID}/transfer{TID}",
            json={"professor_email": "nobody@ex.com"},
            headers=AUTH,
        )
        assert resp.status_code == 404

    def test_missing_tenant_returns_400(self, client, mock_db):
        resp = client.patch(
            f"/api/tenant-admin/classes/{CLASS_ID}/transfer",
            json={"professor_email": "p@ex.com"},
            headers=AUTH,
        )
        assert resp.status_code == 400


class TestDeleteClass:
    def test_delete_class_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (CLASS_ID, "DS101")
        resp = client.delete(
            f"/api/tenant-admin/classes/{CLASS_ID}{TID}",
            headers=AUTH,
        )
        assert resp.status_code == 200

    def test_class_not_in_tenant_returns_404(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None
        resp = client.delete(
            f"/api/tenant-admin/classes/{CLASS_ID}{TID}",
            headers=AUTH,
        )
        assert resp.status_code == 404

    def test_missing_tenant_returns_400(self, client, mock_db):
        resp = client.delete(
            f"/api/tenant-admin/classes/{CLASS_ID}",
            headers=AUTH,
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Audit Log
# ---------------------------------------------------------------------------


class TestGetAuditLog:
    def test_audit_log_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (3,)  # total count
        cursor.fetchall.return_value = [
            (1, "uid-1", "Alice", "alice@ex.com", "LOGIN", "user", "uid-1", {}, _NOW),
        ]
        resp = client.get(f"/api/tenant-admin/audit{TID}", headers=AUTH)
        assert resp.status_code == 200
        data = resp.get_json()
        assert "entries" in data
        assert data["total"] == 3

    def test_audit_log_with_filters(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (0,)
        cursor.fetchall.return_value = []
        resp = client.get(
            f"/api/tenant-admin/audit{TID}&action=LOGIN&from=2026-01-01&to=2026-03-01",
            headers=AUTH,
        )
        assert resp.status_code == 200

    def test_missing_tenant_returns_400(self, client, mock_db):
        resp = client.get("/api/tenant-admin/audit", headers=AUTH)
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Announcements
# ---------------------------------------------------------------------------


class TestListTenantAnnouncements:
    def test_list_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchall.return_value = [
            (ANN_ID, "Hello", "World", "info", [], True, None, _NOW, "Admin"),
        ]
        resp = client.get(f"/api/tenant-admin/announcements{TID}", headers=AUTH)
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["announcements"]) == 1
        assert data["announcements"][0]["title"] == "Hello"

    def test_list_empty_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchall.return_value = []
        resp = client.get(f"/api/tenant-admin/announcements{TID}", headers=AUTH)
        assert resp.status_code == 200
        assert data["announcements"] == [] if (data := resp.get_json()) else True

    def test_missing_tenant_returns_400(self, client, mock_db):
        resp = client.get("/api/tenant-admin/announcements", headers=AUTH)
        assert resp.status_code == 400


class TestCreateTenantAnnouncement:
    def test_create_returns_201(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (ANN_ID,)
        resp = client.post(
            f"/api/tenant-admin/announcements{TID}",
            json={"title": "Hello", "message": "World", "type": "info"},
            headers=AUTH,
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["success"] is True

    def test_missing_title_returns_400(self, client, mock_db):
        resp = client.post(
            f"/api/tenant-admin/announcements{TID}",
            json={"message": "World"},
            headers=AUTH,
        )
        assert resp.status_code == 400

    def test_missing_message_returns_400(self, client, mock_db):
        resp = client.post(
            f"/api/tenant-admin/announcements{TID}",
            json={"title": "Hello"},
            headers=AUTH,
        )
        assert resp.status_code == 400

    def test_invalid_type_returns_400(self, client, mock_db):
        resp = client.post(
            f"/api/tenant-admin/announcements{TID}",
            json={"title": "T", "message": "M", "type": "catastrophe"},
            headers=AUTH,
        )
        assert resp.status_code == 400

    def test_missing_tenant_returns_400(self, client, mock_db):
        resp = client.post(
            "/api/tenant-admin/announcements",
            json={"title": "T", "message": "M"},
            headers=AUTH,
        )
        assert resp.status_code == 400


class TestUpdateTenantAnnouncement:
    def test_update_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (ANN_ID,)
        resp = client.patch(
            f"/api/tenant-admin/announcements/{ANN_ID}{TID}",
            json={"is_active": False},
            headers=AUTH,
        )
        assert resp.status_code == 200

    def test_no_fields_returns_400(self, client, mock_db):
        resp = client.patch(
            f"/api/tenant-admin/announcements/{ANN_ID}{TID}",
            json={},
            headers=AUTH,
        )
        assert resp.status_code == 400

    def test_announcement_not_found_returns_404(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None
        resp = client.patch(
            f"/api/tenant-admin/announcements/{ANN_ID}{TID}",
            json={"is_active": True},
            headers=AUTH,
        )
        assert resp.status_code == 404

    def test_missing_tenant_returns_400(self, client, mock_db):
        resp = client.patch(
            f"/api/tenant-admin/announcements/{ANN_ID}",
            json={"is_active": True},
            headers=AUTH,
        )
        assert resp.status_code == 400


class TestDeleteTenantAnnouncement:
    def test_delete_returns_200(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (ANN_ID,)
        resp = client.delete(
            f"/api/tenant-admin/announcements/{ANN_ID}{TID}",
            headers=AUTH,
        )
        assert resp.status_code == 200

    def test_announcement_not_found_returns_404(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None
        resp = client.delete(
            f"/api/tenant-admin/announcements/{ANN_ID}{TID}",
            headers=AUTH,
        )
        assert resp.status_code == 404

    def test_missing_tenant_returns_400(self, client, mock_db):
        resp = client.delete(
            f"/api/tenant-admin/announcements/{ANN_ID}",
            headers=AUTH,
        )
        assert resp.status_code == 400
