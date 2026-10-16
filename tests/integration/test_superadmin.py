"""
Integration tests — superadmin HTTP endpoints against a real Postgres database.

These drive the Flask test client, so unlike the repository-level tests they
cannot use the ``tx`` savepoint fixture: the application opens its own
connection from the pool and would not see uncommitted rows. Rows these tests
need are therefore committed by fixtures and deleted again on teardown, and
every id is prefixed ``inttest_`` so the session-level cleanup can sweep up
after an interrupted run.

require_auth re-checks account_status and token_version against the users table
on every request, so a token is only accepted for a user that actually exists —
which is why the acting users are seeded rather than invented in a JWT.
"""

import uuid

import pytest

from app import app as flask_app
from core.auth import create_jwt_token
from tests.integration.conftest import make_user_id

SUPERADMIN_ID = "inttest_superadmin"
STUDENT_ID = "inttest_student"


def _insert_user(conn, user_id, role, email):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (user_id, name, email, password_hash, role, token_version)
            VALUES (%s, %s, %s, %s, %s, 0)
            ON CONFLICT (user_id) DO NOTHING
            """,
            (user_id, f"Integration {role}", email, "x", role),
        )
    conn.commit()


def _delete_user(conn, user_id):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
    conn.commit()


@pytest.fixture(scope="module")
def acting_users(db_conn):
    """Seed (committed) the superadmin and plain student the tokens below belong to."""
    _insert_user(db_conn, SUPERADMIN_ID, "superadmin", f"{SUPERADMIN_ID}@myanalytiq.org")
    _insert_user(db_conn, STUDENT_ID, "student", f"{STUDENT_ID}@student.example.test")
    yield
    _delete_user(db_conn, SUPERADMIN_ID)
    _delete_user(db_conn, STUDENT_ID)


@pytest.fixture
def client(acting_users):
    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False
    return flask_app.test_client()


@pytest.fixture
def super_admin_headers():
    token = create_jwt_token(
        SUPERADMIN_ID,
        role="superadmin",
        name="Integration superadmin",
        email=f"{SUPERADMIN_ID}@myanalytiq.org",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def normal_headers():
    token = create_jwt_token(
        STUDENT_ID,
        role="student",
        name="Integration student",
        email=f"{STUDENT_ID}@student.example.test",
    )
    return {"Authorization": f"Bearer {token}"}


def test_tenant_api_access(client, super_admin_headers, normal_headers):
    # A standard user is rejected by role, not by authentication.
    res = client.get("/api/superadmin/tenants", headers=normal_headers)
    assert res.status_code == 403

    res = client.get("/api/superadmin/tenants", headers=super_admin_headers)
    assert res.status_code == 200
    assert "tenants" in res.json


def test_tenant_creation(client, super_admin_headers, db_conn):
    name = f"inttest_university_{make_user_id()}"
    res = client.post(
        "/api/superadmin/tenants",
        headers=super_admin_headers,
        json={"name": name, "lti_issuer": f"https://canvas.{name}.test"},
    )
    assert res.status_code == 201
    assert res.json["tenant"]["name"] == name
    tenant_id = res.json["tenant"]["tenant_id"]

    try:
        res = client.patch(
            f"/api/superadmin/tenants/{tenant_id}",
            headers=super_admin_headers,
            json={"is_active": False},
        )
        assert res.status_code == 200
    finally:
        # The endpoint committed this row on its own connection.
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM tenants WHERE tenant_id = %s", (tenant_id,))
        db_conn.commit()


def test_impersonation(client, super_admin_headers, db_conn):
    from core.auth import decode_jwt_token

    target = make_user_id()
    _insert_user(db_conn, target, "student", f"{target}@student.example.test")
    try:
        res = client.post(
            f"/api/superadmin/users/{target}/impersonate", headers=super_admin_headers
        )
        assert res.status_code == 200
        token = res.json["token"]
        assert token is not None

        payload = decode_jwt_token(token)
        assert payload["user_id"] == target
        assert payload["role"] == "student"
        assert payload["impersonator_id"] == SUPERADMIN_ID
    finally:
        _delete_user(db_conn, target)


def test_user_search(client, super_admin_headers):
    res = client.get("/api/superadmin/users?q=Integration", headers=super_admin_headers)
    assert res.status_code == 200
    assert "users" in res.json
    assert "total" in res.json


def test_delete_admin_who_authored_records_keeps_the_records(client, super_admin_headers, db_conn):
    """The superadmin delete path, like the tenant-admin one, must not trip over authorship.

    ``announcements.created_by`` and ``ip_blocklist.blocked_by`` are attribution,
    not ownership, and are ``ON DELETE SET NULL``: a platform announcement and a
    blocked address both outlive the admin who created them. If either were left
    on PostgreSQL's default ``NO ACTION`` this delete would raise
    ForeignKeyViolation, and the handler's ``except Exception`` would report it
    as a bare 500 -- so the assertion on the status code is the point.
    """
    author_id = make_user_id()
    announcement_id = f"inttest_{uuid.uuid4().hex[:12]}"
    blocked_ip = f"203.0.113.{uuid.uuid4().int % 200 + 1}"
    _insert_user(db_conn, author_id, "tenant_admin", f"{author_id}@tenant.example.test")

    with db_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO announcements (announcement_id, title, message, created_by)
            VALUES (%s, 'Platform notice', 'Read-only window tonight', %s)
            """,
            (announcement_id, author_id),
        )
        cur.execute(
            "INSERT INTO ip_blocklist (ip_address, reason, blocked_by) VALUES (%s, %s, %s)",
            (blocked_ip, "Integration test", author_id),
        )
    db_conn.commit()

    try:
        res = client.delete(f"/api/superadmin/users/{author_id}", headers=super_admin_headers)
        assert res.status_code == 200, res.json

        with db_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users WHERE user_id = %s", (author_id,))
            assert cur.fetchone()[0] == 0
            cur.execute(
                """
                SELECT COUNT(*) FROM announcements
                WHERE announcement_id = %s AND created_by IS NULL
                """,
                (announcement_id,),
            )
            assert cur.fetchone()[0] == 1, "the announcement did not survive its author's deletion"
            cur.execute(
                "SELECT COUNT(*) FROM ip_blocklist WHERE ip_address = %s AND blocked_by IS NULL",
                (blocked_ip,),
            )
            assert cur.fetchone()[0] == 1, "the blocklist entry did not survive the deletion"
    finally:
        with db_conn.cursor() as cur:
            cur.execute("DELETE FROM ip_blocklist WHERE ip_address = %s", (blocked_ip,))
            cur.execute("DELETE FROM announcements WHERE announcement_id = %s", (announcement_id,))
        db_conn.commit()
        _delete_user(db_conn, author_id)
