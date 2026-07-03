"""
Lightweight SQL migration runner for AnalytIQ.

Reads every *.sql file in the migrations/ directory (sorted by filename) and
applies any that have not yet been recorded in the ``schema_migrations`` table.

All migration SQL files must be idempotent (IF NOT EXISTS / ON CONFLICT DO NOTHING)
so that re-running them on an already-migrated database is harmless.

Usage (called automatically at app startup in app.py)::

    from db_migrate import run_migrations
    from core.database import get_db_connection
    run_migrations(get_db_connection())
"""

import glob
import logging
import os

logger = logging.getLogger(__name__)

_MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")

_CREATE_TRACKING_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    filename   VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMPTZ DEFAULT NOW()
);
"""


_MIGRATION_LOCK_KEY = 728194  # constant advisory-lock id for the migration runner


def run_migrations(conn):
    """Apply pending migrations under a Postgres advisory lock.

    The lock serialises concurrent workers/dynos so migrations run once; others
    block until it releases, then find them already recorded and skip. This
    removes the boot-time race where multiple gunicorn/Celery workers applied the
    same DDL simultaneously. Best-effort: if the lock cannot be taken the
    migrations still run (original behaviour). Never crashes the app.

    Args:
        conn: a psycopg2 connection from ``get_db_connection()``.
    """
    locked = False
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_lock(%s)", (_MIGRATION_LOCK_KEY,))
        conn.commit()
        locked = True
    except Exception as exc:
        logger.warning("db_migrate: advisory lock unavailable (continuing): %s", exc)
        try:
            conn.rollback()
        except Exception:
            pass
    try:
        _apply_pending_migrations(conn)
    finally:
        if locked:
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT pg_advisory_unlock(%s)", (_MIGRATION_LOCK_KEY,))
                conn.commit()
            except Exception:
                pass


def _apply_pending_migrations(conn):
    """Apply any pending SQL migrations (already-applied ones are skipped)."""
    try:
        # Ensure tracking table exists
        with conn.cursor() as cur:
            cur.execute(_CREATE_TRACKING_TABLE)
        conn.commit()
    except Exception as exc:
        logger.warning("db_migrate: failed to create tracking table: %s", exc)
        try:
            conn.rollback()
        except Exception:
            pass
        return

    # Collect migration files in deterministic order
    pattern = os.path.join(_MIGRATIONS_DIR, "*.sql")
    sql_files = sorted(glob.glob(pattern))

    if not sql_files:
        logger.debug("db_migrate: no migration files found in %s", _MIGRATIONS_DIR)
        return

    for sql_path in sql_files:
        filename = os.path.basename(sql_path)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM schema_migrations WHERE filename = %s", (filename,))
                if cur.fetchone():
                    continue  # already applied

            # Read and execute the migration
            with open(sql_path, "r", encoding="utf-8") as fh:
                sql = fh.read()

            with conn.cursor() as cur:
                cur.execute(sql)
                cur.execute(
                    "INSERT INTO schema_migrations (filename) VALUES (%s) ON CONFLICT DO NOTHING",
                    (filename,),
                )
            conn.commit()
            logger.info("db_migrate: applied %s", filename)

        except Exception as exc:
            logger.warning("db_migrate: failed to apply %s: %s", filename, exc)
            try:
                conn.rollback()
            except Exception:
                pass
            # Continue trying remaining migrations
