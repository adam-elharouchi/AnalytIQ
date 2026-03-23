"""
Behavioral tests: role-based access control on HTTP endpoints.

Verifies that @require_role decorators enforce access at the route level —
not relying on inline checks inside the handler body.
"""
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client(app):
    return app.test_client()


def _auth_headers(user_id, role):
    """Headers for the TESTING auth bypass (FLASK_ENV=testing + TESTING=True)."""
    return {
        "X-Test-User-ID": user_id,
        "X-Test-User-Role": role,
    }


# ---------------------------------------------------------------------------
# enroll_in_class — students allowed, professors blocked
# ---------------------------------------------------------------------------


class TestEnrollRoleGuard:
    def test_professor_cannot_enroll(self, client, mock_db):
        """Professors get 403 from the @require_role decorator before any DB work."""
        resp = client.post(
            "/api/classes/enroll",
            json={"class_id": "SOME123"},
            headers=_auth_headers("prof-1", "professor"),
        )
        assert resp.status_code == 403

    def test_student_enroll_proceeds_to_handler(self, client, mock_db):
        """Students pass the role guard; the handler returns 404 (class not found)
        which means the role check was bypassed and real logic ran."""
        mock_db.cursor.return_value.fetchone.return_value = None  # class not found
        resp = client.post(
            "/api/classes/enroll",
            json={"class_id": "NOCLASS"},
            headers=_auth_headers("student-1", "student"),
        )
        # 404 = passed role guard, hit the "class not found" branch
        assert resp.status_code == 404

    def test_superadmin_enroll_proceeds_to_handler(self, client, mock_db):
        """Superadmins also pass the role guard."""
        mock_db.cursor.return_value.fetchone.return_value = None
        resp = client.post(
            "/api/classes/enroll",
            json={"class_id": "NOCLASS"},
            headers=_auth_headers("sa-1", "superadmin"),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# get_student_progress — professors allowed, students blocked
# ---------------------------------------------------------------------------


class TestStudentProgressRoleGuard:
    def test_student_cannot_view_progress(self, client, mock_db):
        """Students get 403 from the @require_role decorator."""
        resp = client.get(
            "/api/students/other-student/progress",
            headers=_auth_headers("student-1", "student"),
        )
        assert resp.status_code == 403

    def test_professor_can_view_progress(self, client, mock_db):
        """Professors pass the role guard; handler returns 404 (student not found)."""
        mock_db.cursor.return_value.fetchone.return_value = None  # student not found
        resp = client.get(
            "/api/students/unknown-student/progress",
            headers=_auth_headers("prof-1", "professor"),
        )
        # 404 = passed role guard, real handler ran
        assert resp.status_code == 404

    def test_tenant_admin_can_view_progress(self, client, mock_db):
        """tenant_admin also passes the role guard."""
        mock_db.cursor.return_value.fetchone.return_value = None
        resp = client.get(
            "/api/students/unknown-student/progress",
            headers=_auth_headers("ta-1", "tenant_admin"),
        )
        assert resp.status_code == 404

    def test_superadmin_can_view_progress(self, client, mock_db):
        """superadmin also passes the role guard."""
        mock_db.cursor.return_value.fetchone.return_value = None
        resp = client.get(
            "/api/students/unknown-student/progress",
            headers=_auth_headers("sa-1", "superadmin"),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# create_class — professors allowed, students blocked
# ---------------------------------------------------------------------------


class TestCreateClassRoleGuard:
    def test_student_cannot_create_class(self, client, mock_db):
        resp = client.post(
            "/api/classes",
            json={"class_name": "Intro to Python", "class_id": "PYTHON101"},
            headers=_auth_headers("student-1", "student"),
        )
        assert resp.status_code == 403

    def test_professor_can_create_class(self, client, mock_db):
        """Professor passes the role guard; 200/201 or 400 from real handler."""
        mock_db.cursor.return_value.fetchone.return_value = None
        resp = client.post(
            "/api/classes",
            json={"class_name": "Intro to Python", "class_id": "PYTHON101"},
            headers=_auth_headers("prof-1", "professor"),
        )
        # Anything but 403 means the role guard was passed
        assert resp.status_code != 403


# ---------------------------------------------------------------------------
# Unauthenticated requests
# ---------------------------------------------------------------------------


class TestUnauthenticatedRequests:
    def test_no_token_returns_401(self, client):
        resp = client.get("/api/classes")
        assert resp.status_code == 401

    def test_no_token_on_post_returns_401(self, client):
        resp = client.post("/api/classes/enroll", json={"class_id": "X"})
        assert resp.status_code == 401
