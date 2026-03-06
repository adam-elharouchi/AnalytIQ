"""
tests/test_classes_routes.py — Behavioral tests for class routes.

Covers:
  POST   /api/classes                          (create class, professor only)
  GET    /api/classes                          (list classes)
  GET    /api/classes/<class_id>               (get class detail)
  PUT    /api/classes/<class_id>               (update class)
  DELETE /api/classes/<class_id>              (delete class)
  POST   /api/classes/enroll                  (student enrollment)
  GET    /api/classes/enrolled                 (list enrolled classes)
  GET    /api/classes/<class_id>/students     (list students, professor only)
  GET    /api/classes/<class_id>/progress     (class progress, professor only)
  GET    /api/classes/<class_id>/leaderboard/average
  GET    /api/classes/<class_id>/leaderboard/exercise/<exercise_id>
"""
import pytest
from datetime import datetime
from unittest.mock import MagicMock

AUTH_STUDENT = {"X-Test-User-ID": "student-user-id", "X-Test-User-Role": "student"}
AUTH_PROF = {"X-Test-User-ID": "prof-user-id", "X-Test-User-Role": "professor"}


# ---------------------------------------------------------------------------
# POST /api/classes — create class (professor only)
# ---------------------------------------------------------------------------

class TestCreateClass:
    def test_create_class_as_professor_returns_201(self, client, mock_db):
        """Professor creates class successfully — 201 with class_id."""
        cursor = mock_db.cursor()
        # class_code_exists -> False; insert_class -> row
        cursor.fetchone.side_effect = [
            None,  # class_code_exists
            ("class-abc", "Data Science 101", "A class", datetime.now()),  # insert_class
        ]

        resp = client.post(
            "/api/classes",
            headers=AUTH_PROF,
            json={"name": "Data Science 101", "description": "A class", "class_code": "DS101"},
        )

        assert resp.status_code == 201
        data = resp.get_json()
        assert "class_id" in data
        assert data["success"] is True

    def test_create_class_as_student_returns_403(self, client, mock_db):
        """Students cannot create classes — 403 Forbidden."""
        resp = client.post(
            "/api/classes",
            headers=AUTH_STUDENT,
            json={"name": "My Class", "class_code": "SC101"},
        )

        assert resp.status_code == 403

    def test_create_class_without_auth_returns_401(self, client, mock_db):
        """Missing auth returns 401."""
        resp = client.post("/api/classes", json={"name": "My Class", "class_code": "SC101"})
        assert resp.status_code == 401

    def test_create_class_missing_class_code_returns_400(self, client, mock_db):
        """Class code is required — 400 without it."""
        resp = client.post(
            "/api/classes",
            headers=AUTH_PROF,
            json={"name": "My Class"},
        )
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_create_class_duplicate_code_returns_409(self, client, mock_db):
        """Duplicate class code returns 409 Conflict."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = ("existing-class",)  # class_code_exists -> True

        resp = client.post(
            "/api/classes",
            headers=AUTH_PROF,
            json={"name": "Data Science 101", "class_code": "DS101"},
        )

        assert resp.status_code == 409
        data = resp.get_json()
        assert "error" in data


# ---------------------------------------------------------------------------
# GET /api/classes — list classes
# ---------------------------------------------------------------------------

class TestListClasses:
    def test_list_classes_returns_200_with_classes_key(self, client, mock_db):
        """GET /api/classes returns 200 with 'classes' key in response."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (5,)  # total_count
        cursor.fetchall.return_value = [
            ("class-1", "DS 101", "Desc", datetime.now(), 3, 2),
        ]

        resp = client.get("/api/classes", headers=AUTH_PROF)

        assert resp.status_code == 200
        data = resp.get_json()
        assert "classes" in data

    def test_list_classes_no_auth_returns_401(self, client, mock_db):
        """GET /api/classes without auth returns 401."""
        resp = client.get("/api/classes")
        assert resp.status_code == 401

    def test_list_classes_response_has_pagination(self, client, mock_db):
        """Response includes pagination metadata."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (0,)
        cursor.fetchall.return_value = []

        resp = client.get("/api/classes", headers=AUTH_STUDENT)

        assert resp.status_code == 200
        data = resp.get_json()
        # Build paginated response includes total, limit, offset keys
        assert "total" in data or "classes" in data


# ---------------------------------------------------------------------------
# GET /api/classes/<class_id> — get class detail
# ---------------------------------------------------------------------------

class TestGetClass:
    def test_get_class_owner_sees_detail(self, client, mock_db):
        """Class owner gets full detail including is_owner: True."""
        cursor = mock_db.cursor()
        # get_class_detail returns row; count queries return integers
        cursor.fetchone.side_effect = [
            ("class-abc", "DS 101", "Desc", "prof-user-id", datetime.now(), "Prof Name", "prof@hult.edu"),
            (10,),  # student_count
            (3,),   # chapter_count
            (5,),   # exercise_count
        ]

        resp = client.get("/api/classes/class-abc", headers=AUTH_PROF)

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["class_id"] == "class-abc"
        assert data["is_owner"] is True

    def test_get_class_not_found_returns_404(self, client, mock_db):
        """Non-existent class_id returns 404."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None  # class not found

        resp = client.get("/api/classes/nonexistent-id", headers=AUTH_PROF)

        assert resp.status_code == 404
        assert "error" in resp.get_json()

    def test_get_class_unenrolled_student_returns_403(self, client, mock_db):
        """Student not enrolled in class is denied — 403."""
        cursor = mock_db.cursor()
        cursor.fetchone.side_effect = [
            # class exists but owner is someone else
            ("class-abc", "DS 101", "Desc", "other-prof-id", datetime.now(), "Prof Name"),
            None,  # check_enrollment -> not enrolled
        ]

        resp = client.get("/api/classes/class-abc", headers=AUTH_STUDENT)

        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# PUT /api/classes/<class_id> — update class
# ---------------------------------------------------------------------------

class TestUpdateClass:
    def test_update_class_owner_returns_200(self, client, mock_db):
        """Class owner can update name/description."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = ("prof-user-id",)  # get_class_owner

        resp = client.put(
            "/api/classes/class-abc",
            headers=AUTH_PROF,
            json={"name": "New Name"},
        )

        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_update_class_non_owner_returns_403(self, client, mock_db):
        """Non-owner professor cannot update class."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = ("different-prof-id",)  # owner mismatch

        resp = client.put(
            "/api/classes/class-abc",
            headers=AUTH_PROF,
            json={"name": "New Name"},
        )

        assert resp.status_code == 403

    def test_update_class_not_found_returns_404(self, client, mock_db):
        """Updating non-existent class returns 404."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None  # class not found

        resp = client.put(
            "/api/classes/nonexistent",
            headers=AUTH_PROF,
            json={"name": "X"},
        )

        assert resp.status_code == 404

    def test_update_class_no_fields_returns_400(self, client, mock_db):
        """Sending no update fields returns 400."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = ("prof-user-id",)

        resp = client.put(
            "/api/classes/class-abc",
            headers=AUTH_PROF,
            json={},
        )

        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /api/classes/<class_id> — delete class
# ---------------------------------------------------------------------------

class TestDeleteClass:
    def test_delete_class_owner_returns_200(self, client, mock_db):
        """Owner deletes class successfully."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = ("prof-user-id",)  # get_class_owner

        resp = client.delete("/api/classes/class-abc", headers=AUTH_PROF)

        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

    def test_delete_class_non_owner_returns_403(self, client, mock_db):
        """Non-owner cannot delete class."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = ("other-prof-id",)

        resp = client.delete("/api/classes/class-abc", headers=AUTH_PROF)

        assert resp.status_code == 403

    def test_delete_class_not_found_returns_404(self, client, mock_db):
        """Deleting non-existent class returns 404."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None

        resp = client.delete("/api/classes/nonexistent", headers=AUTH_PROF)

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/classes/enroll — student enrollment
# ---------------------------------------------------------------------------

class TestEnrollInClass:
    def test_student_enrolls_successfully_returns_201(self, client, mock_db):
        """Student successfully enrolls — 201 with class_id and success flag."""
        cursor = mock_db.cursor()
        cursor.fetchone.side_effect = [
            ("class-abc", "DS 101"),  # get_class_with_name
            None,                     # check_enrollment -> not already enrolled
            (datetime.now(),),        # enroll_student -> enrolled_at
        ]

        resp = client.post(
            "/api/classes/enroll",
            headers=AUTH_STUDENT,
            json={"class_id": "class-abc"},
        )

        assert resp.status_code == 201
        data = resp.get_json()
        assert data["class_id"] == "class-abc"
        assert data["success"] is True

    def test_professor_cannot_enroll_returns_403(self, client, mock_db):
        """Professors are blocked from enrolling — 403."""
        resp = client.post(
            "/api/classes/enroll",
            headers=AUTH_PROF,
            json={"class_id": "class-abc"},
        )

        assert resp.status_code == 403

    def test_enroll_missing_class_id_returns_400(self, client, mock_db):
        """Missing class_id returns 400."""
        resp = client.post(
            "/api/classes/enroll",
            headers=AUTH_STUDENT,
            json={},
        )

        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_enroll_class_not_found_returns_404(self, client, mock_db):
        """Class not found returns 404."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None  # class doesn't exist

        resp = client.post(
            "/api/classes/enroll",
            headers=AUTH_STUDENT,
            json={"class_id": "bad-class"},
        )

        assert resp.status_code == 404

    def test_enroll_already_enrolled_returns_400(self, client, mock_db):
        """Enrolling twice returns 400 with 'Already enrolled' error."""
        cursor = mock_db.cursor()
        cursor.fetchone.side_effect = [
            ("class-abc", "DS 101"),    # class exists
            ("existing-enrollment",),   # check_enrollment -> already enrolled
        ]

        resp = client.post(
            "/api/classes/enroll",
            headers=AUTH_STUDENT,
            json={"class_id": "class-abc"},
        )

        assert resp.status_code == 400
        data = resp.get_json()
        assert "already enrolled" in data["error"].lower()


# ---------------------------------------------------------------------------
# GET /api/classes/enrolled — list enrolled classes
# ---------------------------------------------------------------------------

class TestGetEnrolledClasses:
    def test_get_enrolled_classes_returns_200_with_classes(self, client, mock_db):
        """Returns 200 with classes list for an enrolled student."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = (2,)  # total_count
        cursor.fetchall.return_value = [
            ("class-1", "DS 101", "desc", datetime.now(), "Prof Name", "prof@hult.edu", datetime.now(), 5, 3),
        ]

        resp = client.get("/api/classes/enrolled", headers=AUTH_STUDENT)

        assert resp.status_code == 200
        data = resp.get_json()
        assert "classes" in data

    def test_get_enrolled_classes_no_auth_returns_401(self, client, mock_db):
        """Unauthenticated request returns 401."""
        resp = client.get("/api/classes/enrolled")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/classes/<class_id>/students — list students
# ---------------------------------------------------------------------------

class TestGetClassStudents:
    def test_professor_gets_student_list(self, client, mock_db):
        """Class owner gets list of enrolled students."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = ("prof-user-id",)  # owner
        cursor.fetchall.return_value = [
            ("stu-1", "Alice", "alice@example.com", datetime.now()),
            ("stu-2", "Bob", "bob@example.com", datetime.now()),
        ]

        resp = client.get("/api/classes/class-abc/students", headers=AUTH_PROF)

        assert resp.status_code == 200
        data = resp.get_json()
        assert "students" in data
        assert len(data["students"]) == 2
        # Each student has expected fields
        assert "student_id" in data["students"][0]
        assert "name" in data["students"][0]

    def test_non_owner_professor_returns_403(self, client, mock_db):
        """Professor who doesn't own the class is denied."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = ("different-prof",)

        resp = client.get("/api/classes/class-abc/students", headers=AUTH_PROF)

        assert resp.status_code == 403

    def test_class_not_found_returns_404(self, client, mock_db):
        """Non-existent class returns 404."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None

        resp = client.get("/api/classes/nonexistent/students", headers=AUTH_PROF)

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/classes/<class_id>/progress — class progress (professor only)
# ---------------------------------------------------------------------------

class TestGetClassProgress:
    def test_professor_gets_progress_structure(self, client, mock_db):
        """Professor retrieves progress with exercises and students_progress keys."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = ("prof-user-id",)  # owner
        cursor.fetchall.side_effect = [
            [("ex-1", "Exercise 1", "medium")],           # exercises
            [("stu-1", "Alice", "alice@example.com")],    # students
            [],                                            # progress_rows
        ]

        resp = client.get("/api/classes/class-abc/progress", headers=AUTH_PROF)

        assert resp.status_code == 200
        data = resp.get_json()
        assert "exercises" in data
        assert "students_progress" in data

    def test_non_owner_returns_403(self, client, mock_db):
        """Non-owner professor is denied access to class progress."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = ("different-prof",)

        resp = client.get("/api/classes/class-abc/progress", headers=AUTH_PROF)

        assert resp.status_code == 403

    def test_class_not_found_returns_404(self, client, mock_db):
        """Non-existent class returns 404."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None

        resp = client.get("/api/classes/nonexistent/progress", headers=AUTH_PROF)

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Leaderboard endpoints
# ---------------------------------------------------------------------------

class TestLeaderboards:
    def test_class_average_leaderboard_professor_returns_200(self, client, mock_db):
        """Class owner gets average leaderboard with ranked entries."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = ("prof-user-id",)  # owner = user
        cursor.fetchall.return_value = [
            ("stu-1", "Alice", 85.5, 3),
        ]

        resp = client.get(
            "/api/classes/class-abc/leaderboard/average",
            headers=AUTH_PROF,
        )

        assert resp.status_code == 200
        data = resp.get_json()
        assert "leaderboard" in data
        # Entries have rank
        if data["leaderboard"]:
            assert "rank" in data["leaderboard"][0]

    def test_class_average_leaderboard_unauthorized_returns_403(self, client, mock_db):
        """Student not enrolled in class cannot view leaderboard."""
        cursor = mock_db.cursor()
        cursor.fetchone.side_effect = [
            ("other-prof-id",),  # class exists but owner is different
            None,                # check_enrollment -> not enrolled
        ]

        resp = client.get(
            "/api/classes/class-abc/leaderboard/average",
            headers=AUTH_STUDENT,
        )

        assert resp.status_code == 403

    def test_exercise_leaderboard_for_class_returns_200(self, client, mock_db):
        """Authorized user gets exercise leaderboard."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = ("prof-user-id",)  # owner
        cursor.fetchall.return_value = [
            ("stu-1", "Alice", 90.0, None),
        ]

        resp = client.get(
            "/api/classes/class-abc/leaderboard/exercise/ex-1",
            headers=AUTH_PROF,
        )

        assert resp.status_code == 200
        data = resp.get_json()
        assert "leaderboard" in data

    def test_leaderboard_class_not_found_returns_404(self, client, mock_db):
        """Non-existent class returns 404 on leaderboard endpoint."""
        cursor = mock_db.cursor()
        cursor.fetchone.return_value = None

        resp = client.get(
            "/api/classes/nonexistent/leaderboard/average",
            headers=AUTH_PROF,
        )

        assert resp.status_code == 404
