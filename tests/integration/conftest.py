"""
Shared fixtures for integration tests.

Integration tests connect to a *real* Postgres database.  They are
automatically skipped when DATABASE_URL is absent or unreachable, so
the regular mock-based unit test suite is never interrupted.

The session-scoped ``db_conn`` fixture:
  1. Opens a psycopg2 connection to DATABASE_URL.
  2. Runs CREATE TABLE IF NOT EXISTS for every table touched by the tests.
  3. Yields the connection.
  4. Deletes all rows whose IDs start with ``inttest_`` so the DB stays
     clean across runs.

Each individual test wraps its mutations in a savepoint and rolls back
on teardown (via the ``tx`` fixture) so tests are fully isolated.
"""

import os
import uuid

import psycopg2
import pytest

# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS users (
    id            SERIAL       PRIMARY KEY,
    user_id       VARCHAR(255) UNIQUE NOT NULL,
    name          VARCHAR(255) NOT NULL,
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    role          VARCHAR(50),
    lti_sub       VARCHAR(255),
    lti_issuer    VARCHAR(500),
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (lti_sub, lti_issuer)
);

CREATE TABLE IF NOT EXISTS user_profiles (
    id              SERIAL       PRIMARY KEY,
    user_id         VARCHAR(255) UNIQUE NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    full_name       VARCHAR(255),
    bio             TEXT,
    profile_picture TEXT,
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_settings (
    id                  SERIAL       PRIMARY KEY,
    user_id             VARCHAR(255) UNIQUE NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    email_notifications BOOLEAN      DEFAULT false,
    dark_mode           BOOLEAN      DEFAULT false,
    created_at          TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_preferences (
    id               SERIAL       PRIMARY KEY,
    user_id          VARCHAR(255) UNIQUE NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    current_language VARCHAR(50)  DEFAULT 'python',
    gemini_model     VARCHAR(100) DEFAULT 'gemini-2.5-flash',
    ai_provider      VARCHAR(50)  DEFAULT 'gemini',
    created_at       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_agent_digest (
    id             SERIAL       PRIMARY KEY,
    user_id        VARCHAR(255) UNIQUE NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    goal           TEXT,
    constraints    TEXT,
    decisions      TEXT,
    current_state  TEXT,
    open_questions TEXT,
    created_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS classes (
    class_id          VARCHAR(255) PRIMARY KEY,
    professor_id      VARCHAR(255) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    name              VARCHAR(255) NOT NULL,
    description       TEXT,
    lti_context_id    VARCHAR(500),
    lti_issuer        VARCHAR(500),
    nrps_context_url  TEXT,
    ags_enabled       BOOLEAN      DEFAULT FALSE,
    ags_lineitems_url TEXT,
    created_at        TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS class_enrollments (
    id          SERIAL       PRIMARY KEY,
    class_id    VARCHAR(255) NOT NULL REFERENCES classes(class_id) ON DELETE CASCADE,
    student_id  VARCHAR(255) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    enrolled_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (class_id, student_id)
);

CREATE TABLE IF NOT EXISTS class_chapters (
    chapter_id     VARCHAR(255) PRIMARY KEY,
    class_id       VARCHAR(255) NOT NULL REFERENCES classes(class_id) ON DELETE CASCADE,
    title          VARCHAR(255) NOT NULL,
    description    TEXT,
    chapter_number INTEGER,
    pdf_url        TEXT,
    pdf_filename   VARCHAR(255),
    pdf_data       BYTEA,
    created_at     TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS class_exercises (
    exercise_id     VARCHAR(255) PRIMARY KEY,
    chapter_id      VARCHAR(255) NOT NULL REFERENCES class_chapters(chapter_id) ON DELETE CASCADE,
    class_id        VARCHAR(255) NOT NULL REFERENCES classes(class_id) ON DELETE CASCADE,
    title           VARCHAR(500) NOT NULL,
    description     TEXT,
    difficulty      VARCHAR(50),
    solution_code   TEXT,
    exercise_number INTEGER,
    created_by      VARCHAR(255),
    function_name   VARCHAR(255) DEFAULT 'solution',
    language        VARCHAR(50)  DEFAULT 'Python',
    test_cases      JSONB,
    created_at      TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_log (
    id            BIGSERIAL    PRIMARY KEY,
    user_id       TEXT,
    action        TEXT         NOT NULL,
    resource_type TEXT,
    resource_id   TEXT,
    ip_address    TEXT,
    details       JSONB,
    created_at    TIMESTAMPTZ  DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id    ON audit_log (user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log (created_at DESC);

CREATE TABLE IF NOT EXISTS lti_configurations (
    config_id      VARCHAR(255) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    platform_name  VARCHAR(255) NOT NULL,
    issuer         VARCHAR(500) NOT NULL,
    client_id      VARCHAR(255) NOT NULL,
    auth_login_url TEXT        NOT NULL,
    auth_token_url TEXT        NOT NULL,
    key_set_url    TEXT        NOT NULL,
    deployment_ids TEXT[]      DEFAULT '{}',
    created_by     VARCHAR(255) REFERENCES users(user_id) ON DELETE SET NULL,
    created_at     TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (issuer, client_id)
);

CREATE TABLE IF NOT EXISTS lti_sessions (
    session_id       VARCHAR(255) PRIMARY KEY,
    user_id          VARCHAR(255) REFERENCES users(user_id) ON DELETE CASCADE,
    class_id         VARCHAR(255) REFERENCES classes(class_id) ON DELETE SET NULL,
    nrps_context_url TEXT,
    lti_context_id   TEXT,
    issuer           VARCHAR(500),
    client_id        VARCHAR(255),
    launch_data      JSONB,
    expires_at       TIMESTAMP   NOT NULL,
    created_at       TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
);
"""


def _ensure_schema(conn):
    with conn.cursor() as cur:
        cur.execute(_DDL)
    conn.commit()


def _cleanup(conn):
    """Delete all rows inserted by integration tests (prefixed ``inttest_``)."""
    with conn.cursor() as cur:
        # Exercises cascade from chapters/classes; delete top-level rows.
        cur.execute("DELETE FROM classes      WHERE class_id   LIKE 'inttest_%'")
        cur.execute("DELETE FROM users        WHERE user_id    LIKE 'inttest_%'")
        cur.execute("DELETE FROM audit_log    WHERE user_id    LIKE 'inttest_%' OR resource_id LIKE 'inttest_%'")
    conn.commit()


# ---------------------------------------------------------------------------
# Session-scoped DB connection
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def db_conn():
    """Real psycopg2 connection — skipped if DATABASE_URL is absent/unreachable."""
    # Read at fixture-call time so that env overrides applied by other fixtures
    # (e.g. unit-test setup_test_environment) are visible here.
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL not set — integration tests skipped")

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
    db_conn.execute("SAVEPOINT inttest_sp")
    yield db_conn
    db_conn.execute("ROLLBACK TO SAVEPOINT inttest_sp")
    db_conn.execute("RELEASE SAVEPOINT inttest_sp")


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
