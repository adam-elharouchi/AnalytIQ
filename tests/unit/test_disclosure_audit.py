"""
tests/unit/test_disclosure_audit.py — FERPA read/disclosure audit logging.

Mutations were already audited; this covers the READ side: exporting a user's
data (self or admin) and a professor/admin viewing an individual student's
records now write an audit_log row via core.audit.audit_commit.
"""
from unittest.mock import MagicMock, patch

SUPER = {"X-Test-User-ID": "admin-1", "X-Test-User-Role": "superadmin"}
PROF = {"X-Test-User-ID": "prof-1", "X-Test-User-Role": "professor"}
SELF = {"X-Test-User-ID": "u1", "X-Test-User-Role": "student"}

# A 7-column user row that satisfies both the export endpoints' unpacking.
_USER_ROW = ("uid", "Name", "e@x.com", "student", "active", None, None)


class TestAuditCommitHelper:
    def test_commits_the_audit_row(self):
        from core.audit import audit_commit

        conn = MagicMock()
        audit_commit(conn, "EXPORT_USER_DATA", resource_type="user", resource_id="u1")
        assert conn.commit.called

    def test_commit_failure_is_swallowed_and_rolls_back(self):
        from core.audit import audit_commit

        conn = MagicMock()
        conn.commit.side_effect = Exception("commit boom")
        # Must not raise despite the commit error.
        audit_commit(conn, "EXPORT_USER_DATA", resource_type="user", resource_id="u1")
        assert conn.rollback.called


class TestSelfExportAudited:
    def test_self_export_writes_export_audit(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.description = [
            ("user_id",),
            ("name",),
            ("email",),
            ("role",),
            ("account_status",),
            ("created_at",),
            ("last_login",),
        ]
        cursor.fetchall.return_value = [("u1", "Alice", "a@b.com", "student", "active", None, None)]
        with patch("blueprints.users.audit_commit") as m:
            resp = client.get("/api/users/export", headers=SELF)
        assert resp.status_code == 200
        assert m.called
        assert m.call_args[0][1] == "EXPORT_USER_DATA"


class TestAdminExportAudited:
    def test_superadmin_export_writes_export_audit(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.description = [("c",)]
        cursor.fetchone.return_value = _USER_ROW
        cursor.fetchall.return_value = []
        with patch("blueprints.superadmin.audit_commit") as m:
            resp = client.get("/api/superadmin/users/target-9/export", headers=SUPER)
        assert resp.status_code == 200
        assert m.called
        assert m.call_args[0][1] == "EXPORT_USER_DATA"
        # The disclosure is recorded against the subject, not the actor.
        assert m.call_args.kwargs["resource_id"] == "target-9"

    def test_tenant_admin_export_writes_export_audit(self, client, mock_db):
        cursor = mock_db.cursor()
        cursor.description = [("c",)]
        cursor.fetchone.return_value = _USER_ROW
        cursor.fetchall.return_value = []
        with patch("blueprints.tenant_admin.audit_commit") as m:
            resp = client.get("/api/tenant-admin/users/target-9/export?tenant_id=t1", headers=SUPER)
        assert resp.status_code == 200
        assert m.called
        assert m.call_args[0][1] == "EXPORT_USER_DATA"


class TestViewStudentRecordAudited:
    def test_professor_view_student_progress_writes_audit(self, client, mock_db):
        cursor = mock_db.cursor()
        # class_repo.get_student_by_id -> (id, name, email); progress rows -> [].
        cursor.fetchone.return_value = ("stud-1", "Student", "s@e.com")
        cursor.fetchall.return_value = []
        with patch("blueprints.classes.audit_commit") as m:
            resp = client.get("/api/students/stud-1/progress", headers=PROF)
        assert resp.status_code == 200
        assert m.called
        assert m.call_args[0][1] == "VIEW_STUDENT_RECORD"
        assert m.call_args.kwargs["resource_id"] == "stud-1"

    def test_no_audit_when_viewing_own_record(self, client, mock_db):
        cursor = mock_db.cursor()
        # student_id in the URL equals the caller's own id.
        cursor.fetchone.return_value = ("prof-1", "Self", "self@e.com")
        cursor.fetchall.return_value = []
        with patch("blueprints.classes.audit_commit") as m:
            resp = client.get("/api/students/prof-1/progress", headers=PROF)
        assert resp.status_code == 200
        assert not m.called
