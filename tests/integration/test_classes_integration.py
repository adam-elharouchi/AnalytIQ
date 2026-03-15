"""
Integration tests — class, chapter, exercise, and enrollment flows
against a real Postgres database.

Tests exercise the repository layer (SQL) directly.
All tests roll back via the ``tx`` savepoint fixture.
"""

import bcrypt
import psycopg2
import pytest

from tests.integration.conftest import (
    make_chapter_id,
    make_class_id,
    make_exercise_id,
    make_user_id,
)
from repositories import auth_repository as auth_repo
from repositories import class_repository as class_repo
from repositories import chapter_repository as chapter_repo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(conn, role="student"):
    uid = make_user_id()
    email = f"{uid}@{'hult.edu' if role == 'professor' else 'student.hult.edu'}"
    pw_hash = bcrypt.hashpw(b"TestPass123!", bcrypt.gensalt()).decode()
    auth_repo.insert_user(conn, uid, "Test User", email, pw_hash, role)
    return uid


def _make_class(conn, professor_id):
    class_id = make_class_id()
    row = class_repo.insert_class(conn, class_id, professor_id, "Test Class", "A test class")
    return row[0]  # class_id returned by RETURNING


def _make_chapter(conn, class_id):
    chapter_id = make_chapter_id()
    chapter_repo.insert_chapter(
        conn, chapter_id, class_id,
        title="Test Chapter", description="Desc",
        chapter_number=1, pdf_url=None, pdf_filename=None, pdf_data=None,
    )
    return chapter_id


def _make_exercise(conn, chapter_id, class_id):
    exercise_id = make_exercise_id()
    chapter_repo.insert_exercise(
        conn, exercise_id, chapter_id, class_id,
        title="Test Exercise", description="Write some code",
        difficulty="easy", solution_code="print('hello')", exercise_number=1,
    )
    return exercise_id


# ---------------------------------------------------------------------------
# Class CRUD tests
# ---------------------------------------------------------------------------


class TestClassCRUD:
    def test_insert_class_persisted(self, tx):
        prof = _make_user(tx, "professor")
        class_id = _make_class(tx, prof)

        with tx.cursor() as cur:
            cur.execute("SELECT class_id, professor_id FROM classes WHERE class_id = %s", (class_id,))
            row = cur.fetchone()
        assert row is not None
        assert row[0] == class_id
        assert row[1] == prof

    def test_class_code_exists(self, tx):
        prof = _make_user(tx, "professor")
        class_id = _make_class(tx, prof)
        assert class_repo.class_code_exists(tx, class_id) is True

    def test_class_code_not_exists(self, tx):
        assert class_repo.class_code_exists(tx, "nonexistent_class_id_xyz") is False

    def test_get_class_owner(self, tx):
        prof = _make_user(tx, "professor")
        class_id = _make_class(tx, prof)
        owner = class_repo.get_class_owner(tx, class_id)
        assert owner == prof

    def test_delete_class(self, tx):
        prof = _make_user(tx, "professor")
        class_id = _make_class(tx, prof)
        class_repo.delete_class(tx, class_id)

        with tx.cursor() as cur:
            cur.execute("SELECT class_id FROM classes WHERE class_id = %s", (class_id,))
            row = cur.fetchone()
        assert row is None

    def test_delete_class_cascades_to_chapters(self, tx):
        prof = _make_user(tx, "professor")
        class_id = _make_class(tx, prof)
        chapter_id = _make_chapter(tx, class_id)

        class_repo.delete_class(tx, class_id)

        with tx.cursor() as cur:
            cur.execute(
                "SELECT chapter_id FROM class_chapters WHERE chapter_id = %s", (chapter_id,)
            )
            row = cur.fetchone()
        assert row is None

    def test_delete_class_cascades_to_exercises(self, tx):
        prof = _make_user(tx, "professor")
        class_id = _make_class(tx, prof)
        chapter_id = _make_chapter(tx, class_id)
        exercise_id = _make_exercise(tx, chapter_id, class_id)

        class_repo.delete_class(tx, class_id)

        with tx.cursor() as cur:
            cur.execute(
                "SELECT exercise_id FROM class_exercises WHERE exercise_id = %s", (exercise_id,)
            )
            row = cur.fetchone()
        assert row is None

    def test_delete_class_cascades_to_enrollments(self, tx):
        prof = _make_user(tx, "professor")
        student = _make_user(tx, "student")
        class_id = _make_class(tx, prof)
        class_repo.enroll_student(tx, class_id, student)

        class_repo.delete_class(tx, class_id)

        with tx.cursor() as cur:
            cur.execute(
                "SELECT id FROM class_enrollments WHERE class_id = %s", (class_id,)
            )
            row = cur.fetchone()
        assert row is None


# ---------------------------------------------------------------------------
# Enrollment tests
# ---------------------------------------------------------------------------


class TestEnrollment:
    def test_enroll_student(self, tx):
        prof = _make_user(tx, "professor")
        student = _make_user(tx, "student")
        class_id = _make_class(tx, prof)

        class_repo.enroll_student(tx, class_id, student)

        assert class_repo.check_enrollment(tx, class_id, student) is True

    def test_check_enrollment_false_for_unenrolled(self, tx):
        prof = _make_user(tx, "professor")
        student = _make_user(tx, "student")
        class_id = _make_class(tx, prof)

        assert class_repo.check_enrollment(tx, class_id, student) is False

    def test_duplicate_enrollment_rejected(self, tx):
        prof = _make_user(tx, "professor")
        student = _make_user(tx, "student")
        class_id = _make_class(tx, prof)
        class_repo.enroll_student(tx, class_id, student)

        with pytest.raises(psycopg2.IntegrityError):
            class_repo.enroll_student(tx, class_id, student)

    def test_enrolled_classes_list(self, tx):
        prof = _make_user(tx, "professor")
        student = _make_user(tx, "student")
        class_id = _make_class(tx, prof)
        class_repo.enroll_student(tx, class_id, student)

        classes = class_repo.get_enrolled_classes(tx, student)
        class_ids = [r[0] for r in classes]
        assert class_id in class_ids


# ---------------------------------------------------------------------------
# Chapter and exercise tests
# ---------------------------------------------------------------------------


class TestChapters:
    def test_insert_chapter_persisted(self, tx):
        prof = _make_user(tx, "professor")
        class_id = _make_class(tx, prof)
        chapter_id = _make_chapter(tx, class_id)

        with tx.cursor() as cur:
            cur.execute(
                "SELECT chapter_id, class_id FROM class_chapters WHERE chapter_id = %s",
                (chapter_id,),
            )
            row = cur.fetchone()
        assert row is not None
        assert row[0] == chapter_id
        assert row[1] == class_id

    def test_delete_chapter_removes_exercises(self, tx):
        prof = _make_user(tx, "professor")
        class_id = _make_class(tx, prof)
        chapter_id = _make_chapter(tx, class_id)
        exercise_id = _make_exercise(tx, chapter_id, class_id)

        chapter_repo.delete_chapter_and_exercises(tx, chapter_id)

        with tx.cursor() as cur:
            cur.execute(
                "SELECT exercise_id FROM class_exercises WHERE exercise_id = %s", (exercise_id,)
            )
            row = cur.fetchone()
        assert row is None

    def test_get_exercises_for_chapter(self, tx):
        prof = _make_user(tx, "professor")
        class_id = _make_class(tx, prof)
        chapter_id = _make_chapter(tx, class_id)
        ex_id = _make_exercise(tx, chapter_id, class_id)

        exercises = chapter_repo.get_exercises_for_chapter(tx, chapter_id)
        ex_ids = [r[0] for r in exercises]
        assert ex_id in ex_ids

    def test_chapter_number_increments(self, tx):
        prof = _make_user(tx, "professor")
        class_id = _make_class(tx, prof)

        n1 = chapter_repo.get_next_chapter_number(tx, class_id)
        _make_chapter(tx, class_id)
        n2 = chapter_repo.get_next_chapter_number(tx, class_id)

        assert n2 == n1 + 1


# ---------------------------------------------------------------------------
# Audit log tests
# ---------------------------------------------------------------------------


class TestAuditLog:
    def test_audit_creates_row(self, tx):
        from core.audit import audit, _table_ready
        import audit as audit_module

        # Force table-creation check to run (in case it's cached as True already).
        old = audit_module._table_ready
        audit_module._table_ready = True  # table was created by conftest DDL

        uid = make_user_id()
        # Manually set g-like context isn't available outside Flask; audit() handles it.
        audit(tx, "CREATE_CLASS", resource_type="class", resource_id=uid)

        with tx.cursor() as cur:
            cur.execute(
                "SELECT action, resource_type, resource_id FROM audit_log WHERE resource_id = %s",
                (uid,),
            )
            row = cur.fetchone()

        audit_module._table_ready = old
        assert row is not None
        assert row[0] == "CREATE_CLASS"
        assert row[1] == "class"
        assert row[2] == uid

    def test_audit_never_raises_on_bad_details(self, tx):
        """audit() must not propagate exceptions — it only logs warnings."""
        from core.audit import audit

        # Pass an un-serializable object — audit() should swallow the error.
        class Unserializable:
            pass

        try:
            audit(tx, "DELETE_USER", resource_type="user", resource_id="inttest_x",
                  details={"obj": Unserializable()})
        except Exception as exc:
            pytest.fail(f"audit() raised unexpectedly: {exc}")
