"""
Migration 007 runner — output-based grading schema additions.

Adds to class_exercises:
  - test_cases    JSONB        (array of test case objects)
  - function_name VARCHAR(255) (name of function students must define)
  - language      VARCHAR(50)  (exercise language for sandbox dispatch)

Safe to re-run (all DDL uses IF NOT EXISTS / ADD COLUMN IF NOT EXISTS).
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

MIGRATION_SQL = open(
    os.path.join(os.path.dirname(__file__), "..", "migrations", "007_exercise_test_cases.sql")
).read()


def get_db_connection():
    url = os.getenv("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL is not set.")
        return None
    try:
        return psycopg2.connect(url)
    except Exception as e:
        print(f"ERROR: Could not connect to database: {e}")
        return None


def run():
    conn = get_db_connection()
    if not conn:
        return False

    try:
        cur = conn.cursor()

        print("Running migration 007: exercise test_cases, function_name, language columns…")
        cur.execute(MIGRATION_SQL)
        conn.commit()
        print("Migration 007 applied successfully.")

        # Verify columns exist
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'class_exercises'
              AND column_name IN ('test_cases', 'function_name', 'language')
            ORDER BY column_name;
        """)
        cols = cur.fetchall()
        print(f"Verified columns: {cols}")

        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"ERROR running migration: {e}")
        conn.rollback()
        conn.close()
        return False


if __name__ == "__main__":
    success = run()
    exit(0 if success else 1)
