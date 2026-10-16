"""
Shared fixtures for integration tests.

Integration tests connect to a *real* PostgreSQL database.

The schema is built by running the project's own migrations — the same
``db_migrate.run_migrations`` that ``python db_migrate.py`` and the Render
pre-deploy step call. This file used to carry its own copy of the DDL, which
was for a long time the only complete definition of the content tables; that
copy now lives in ``migrations/000_initial_schema.sql`` so the schema has one
home and the tests cannot drift from what gets deployed.

Pointing the tests at a database:

  * ``TEST_DATABASE_URL`` — an explicitly disposable database. Preferred.
  * ``DATABASE_URL`` — used only when it points at a local host, so that a
    developer whose DATABASE_URL is a remote/production database never has the
    test suite migrate and write to it.

With neither available the integration tests skip, leaving the mock-based unit
suite unaffected.

The session-scoped ``db_conn`` fixture:
  1. Opens a psycopg2 connection.
  2. Applies every pending migration (creating the schema from nothing if the
     database is empty).
  3. Yields the connection.
  4. Deletes all rows whose IDs start with ``inttest_`` so the DB stays clean
     across runs.

Each individual test wraps its mutations in a savepoint and rolls back on
teardown (via the ``tx`` fixture) so tests are fully isolated.
"""

import os
import sys
import uuid
from pathlib import Path
from urllib.parse import urlparse

import psycopg2
import pytest

# db_migrate lives at the repository root; make sure it is importable no matter
# which directory pytest was started from.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0", "db"}


# ---------------------------------------------------------------------------
# Choosing a database
# ---------------------------------------------------------------------------


def _is_local(url):
    """True when *url* points at a database on this machine / compose network."""
    try:
        host = urlparse(url.split("?")[0]).hostname
    except ValueError:
        return False
    return host in _LOCAL_HOSTS


def integration_database_url():
    """Return the URL to test against, or None when the tests should skip.

    Read at fixture-call time rather than at import, so env overrides applied by
    other fixtures (e.g. the unit suite's ``setup_test_environment``) are visible.
    """
    explicit = os.getenv("TEST_DATABASE_URL")
    if explicit:
        return explicit
    fallback = os.getenv("DATABASE_URL")
    if fallback and _is_local(fallback):
        return fallback
    return None


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def _ensure_schema(conn):
    """Build/patch the schema by applying migrations/*.sql in order."""
    from db_migrate import run_migrations

    failed = run_migrations(conn) or []
    if failed:
        pytest.fail("integration tests: these migrations failed to apply: " + ", ".join(failed))


def _cleanup(conn):
    """Delete all rows inserted by integration tests (prefixed ``inttest_``)."""
    with conn.cursor() as cur:
        # Chapters, exercises, enrollments and profiles cascade from
        # classes/users; delete the top-level rows only.
        cur.execute("DELETE FROM classes   WHERE class_id   LIKE 'inttest_%'")
        cur.execute("DELETE FROM users     WHERE user_id    LIKE 'inttest_%'")
        cur.execute(
            "DELETE FROM audit_log WHERE user_id LIKE 'inttest_%' OR resource_id LIKE 'inttest_%'"
        )
    conn.commit()


# ---------------------------------------------------------------------------
# Session-scoped DB connection
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def db_conn():
    """Real psycopg2 connection — skipped when no disposable database is given."""
    database_url = integration_database_url()
    if not database_url:
        pytest.skip(
            "TEST_DATABASE_URL not set (and DATABASE_URL is not local) "
            "— integration tests skipped"
        )

    try:
        conn = psycopg2.connect(database_url)
        conn.autocommit = False
    except Exception as exc:
        pytest.skip(f"Cannot connect to DB ({exc}) — integration tests skipped")

    _ensure_schema(conn)
    _cleanup(conn)  # remove any stale data from a previous interrupted run

    yield conn

    _cleanup(conn)
    conn.close()


# ---------------------------------------------------------------------------
# Per-test transaction isolation via savepoints
# ---------------------------------------------------------------------------


@pytest.fixture
def tx(db_conn):
    """Wrap each test in a savepoint; roll back on teardown for isolation."""
    with db_conn.cursor() as cur:
        cur.execute("SAVEPOINT inttest_sp")
    yield db_conn
    with db_conn.cursor() as cur:
        cur.execute("ROLLBACK TO SAVEPOINT inttest_sp")
        cur.execute("RELEASE SAVEPOINT inttest_sp")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_user_id():
    return f"inttest_{uuid.uuid4().hex[:12]}"


def make_class_id():
    return f"inttest_{uuid.uuid4().hex[:12]}"


def make_chapter_id():
    return f"inttest_{uuid.uuid4().hex[:12]}"


def make_exercise_id():
    return f"inttest_{uuid.uuid4().hex[:12]}"
