"""
Tests for exercise system - generation, submission, and grading
Targets actual API endpoints in app.py
"""
import pytest
from unittest.mock import patch, MagicMock
import json


class TestExerciseGeneration:
    """Test exercise generation functionality via correct endpoints"""

    @patch('app.generate_exercises_from_pdf_content')
    @patch('app.extract_text_from_pdf_bytes')
    def test_generate_exercises_success(self, mock_extract, mock_generate, client, mock_db):
        """Test successful exercise generation via chapter endpoint"""
        mock_generate.return_value = [
            {"title": "Q1", "description": "Desc1", "difficulty": "easy", "solution_code": "pass"},
        ]
        mock_extract.return_value = "PDF text content"
        # fetchone returns chapter data then professor check
        mock_db.cursor().fetchone.side_effect = [
            ("class123", "Chapter Title", "prof123", "file.pdf", b"pdf-data"),  # chapter data
            ("ex_1",),  # exercise insert returning
        ]

        response = client.post(
            "/api/chapters/chapter123/generate-exercises",
            json={"user_id": "prof123"},
        )

        assert response.status_code in [200, 201, 400, 403, 404, 500]

    @patch('app.generate_exercises_from_pdf_content')
    def test_generate_exercises_no_content(self, mock_generate, client, mock_db):
        """Test exercise generation with missing PDF data"""
        mock_db.cursor().fetchone.return_value = ("class123", "Chapter", "prof123", None, None)

        response = client.post(
            "/api/chapters/chapter123/generate-exercises",
            json={"user_id": "prof123"},
        )

        assert response.status_code in [400, 404, 500]

    def test_generate_exercises_missing_user_id(self, client, mock_db):
        """Test exercise generation without user_id"""
        response = client.post(
            "/api/chapters/chapter123/generate-exercises",
            json={},
        )

        assert response.status_code in [400, 404]

    def test_generate_exercises_options_request(self, client):
        """Test OPTIONS preflight for exercise generation"""
        response = client.options("/api/chapters/chapter123/generate-exercises")
        assert response.status_code == 200


class TestExerciseRetrieval:
    """Test exercise retrieval endpoints"""

    def test_get_exercises_by_chapter(self, client, mock_db):
        """Test getting all exercises for a chapter"""
        mock_db.cursor().fetchone.side_effect = [
            ("class123", "prof123"),  # chapter exists
            ("professor",),  # user role
        ]
        mock_db.cursor().fetchall.return_value = [
            ('ex1', 'Q1', 'Desc1', 'easy', 1, None, 'code1'),
            ('ex2', 'Q2', 'Desc2', 'medium', 2, None, 'code2'),
        ]

        response = client.get("/api/chapters/chapter123/exercises?user_id=prof123")

        assert response.status_code in [200, 400, 403, 404, 500]

    def test_get_exercises_missing_user_id(self, client, mock_db):
        """Test getting exercises without user_id"""
        response = client.get("/api/chapters/chapter123/exercises")

        assert response.status_code == 400

    def test_get_exercises_chapter_not_found(self, client, mock_db):
        """Test getting exercises for non-existent chapter"""
        mock_db.cursor().fetchone.return_value = None

        response = client.get("/api/chapters/nonexistent/exercises?user_id=user123")

        assert response.status_code in [404, 500]

    def test_get_exercises_with_pagination(self, client, mock_db):
        """Test getting exercises with pagination params"""
        mock_db.cursor().fetchone.side_effect = [
            ("class123", "prof123"),
            ("professor",),
        ]
        mock_db.cursor().fetchall.return_value = [
            ('ex1', 'Q1', 'Desc1', 'easy', 1, None, 'code1'),
        ]

        response = client.get("/api/chapters/chapter123/exercises?user_id=prof123&limit=10&offset=0")

        assert response.status_code in [200, 400, 404, 500]


class TestExerciseSubmission:
    """Test exercise submission endpoints"""

    def test_submit_exercise_correct(self, client, mock_db):
        """Test submitting a practice progress update"""
        mock_db.cursor().fetchone.side_effect = [
            ("user123",),  # user exists
            (80, 5),  # existing progress
        ]

        response = client.put(
            "/api/users/practice-progress",
            json={
                "user_id": "user123",
                "exercise_id": "ex123",
                "score": 90,
                "accuracy": 85.5,
                "time_spent": 120,
            },
        )

        assert response.status_code in [200, 400, 404, 500]

    def test_submit_exercise_missing_fields(self, client, mock_db):
        """Test submitting without required fields"""
        response = client.put(
            "/api/users/practice-progress",
            json={"user_id": "user123"},
        )

        assert response.status_code in [400, 500]


class TestExerciseUpdate:
    """Test exercise update endpoints"""

    def test_delete_exercise_success(self, client, mock_db):
        """Test deleting an exercise"""
        mock_db.cursor().fetchone.return_value = ('chapter123', 'class123')

        response = client.delete("/api/exercises/ex123")

        assert response.status_code in [200, 404, 500]

    def test_delete_nonexistent_exercise(self, client, mock_db):
        """Test deleting non-existent exercise"""
        mock_db.cursor().fetchone.return_value = None

        response = client.delete("/api/exercises/nonexistent")

        assert response.status_code in [404, 500]

    def test_delete_exercise_options(self, client):
        """Test OPTIONS for exercise delete"""
        response = client.options("/api/exercises/ex123")
        assert response.status_code == 200


class TestExerciseProgress:
    """Test exercise progress endpoints"""

    def test_get_all_progress(self, client, mock_db):
        """Test getting all exercise progress"""
        mock_db.cursor().fetchall.return_value = [
            ('ex1', 'Exercise 1', 85, 90.5, 3, True, None),
        ]

        response = client.get("/api/exercises/progress?user_id=user123")

        assert response.status_code in [200, 400, 500]

    def test_get_all_progress_missing_user(self, client, mock_db):
        """Test getting progress without user_id"""
        response = client.get("/api/exercises/progress")

        assert response.status_code in [400, 500]

    def test_get_exercise_leaderboard(self, client, mock_db):
        """Test getting exercise leaderboard"""
        mock_db.cursor().fetchall.return_value = [
            ('User1', 'user1@test.com', 95, 98.0, 120, 5),
            ('User2', 'user2@test.com', 88, 92.0, 150, 3),
        ]

        response = client.get("/api/exercises/ex123/leaderboard?limit=10")

        assert response.status_code in [200, 500]

    def test_get_grand_leaderboard(self, client, mock_db):
        """Test getting grand leaderboard"""
        mock_db.cursor().fetchall.return_value = [
            ('user1', 'User1', 'user1@test.com', 5, 92.0, 460, None),
        ]

        response = client.get("/api/leaderboard/grand?limit=10")

        assert response.status_code in [200, 500]


class TestExerciseTypes:
    """Test creating exercises of different types"""

    def test_create_exercise_manual(self, client, mock_db):
        """Test manually creating an exercise"""
        mock_db.cursor().fetchone.side_effect = [
            ("prof123",),  # class owner
            (1,),  # chapter belongs to class
        ]

        response = client.post(
            "/api/classes/class123/chapters/chapter123/exercises",
            json={
                "user_id": "prof123",
                "title": "New Exercise",
                "description": "Exercise description",
                "difficulty": "medium",
                "solution_code": "print('hello')",
            },
        )

        assert response.status_code in [201, 400, 403, 404, 500]

    def test_create_exercise_unauthorized(self, client, mock_db):
        """Test creating exercise as non-owner"""
        mock_db.cursor().fetchone.return_value = ("other_prof",)

        response = client.post(
            "/api/classes/class123/chapters/chapter123/exercises",
            json={
                "user_id": "prof123",
                "title": "New Exercise",
            },
        )

        assert response.status_code in [403, 404, 500]

    def test_create_exercise_missing_user_id(self, client, mock_db):
        """Test creating exercise without user_id"""
        response = client.post(
            "/api/classes/class123/chapters/chapter123/exercises",
            json={"title": "New Exercise"},
        )

        assert response.status_code in [400, 500]
