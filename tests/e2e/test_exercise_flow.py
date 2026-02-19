"""
E2E: Exercise generation and retrieval flows.
Requires a running app: FLASK_ENV=testing python app.py
"""
import uuid
import pytest
import requests

from conftest import API_URL, auth_headers


pytestmark = pytest.mark.e2e


def _uid():
    return uuid.uuid4().hex[:8]


def _create_class_and_chapter(token: str) -> tuple:
    """Return (class_id, chapter_id)."""
    uid = _uid()
    r = requests.post(
        f"{API_URL}/classes",
        json={"name": f"Exercise Class {uid}", "class_code": f"EX{uid[:6].upper()}"},
        headers=auth_headers(token),
        timeout=10,
    )
    assert r.status_code == 201
    class_id = str(r.json()["class"]["id"])

    content = b"Variables store values. A loop repeats code. A function groups reusable code blocks."
    r2 = requests.post(
        f"{API_URL}/classes/{class_id}/chapters",
        data={"title": f"Ch {uid}"},
        files={"pdf_file": ("ch.txt", content, "text/plain")},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    assert r2.status_code == 201, f"Chapter upload failed: {r2.text}"
    chapter = r2.json().get("chapter", r2.json())
    chapter_id = str(chapter.get("id") or chapter.get("chapter_id"))
    return class_id, chapter_id


class TestExerciseFlow:
    def test_get_exercises_empty_returns_200(self, professor_token):
        _, chapter_id = _create_class_and_chapter(professor_token)
        r = requests.get(
            f"{API_URL}/chapters/{chapter_id}/exercises",
            headers=auth_headers(professor_token),
            timeout=10,
        )
        assert r.status_code == 200
        assert "exercises" in r.json()

    def test_generate_exercises_triggers_200_or_202(self, professor_token):
        _, chapter_id = _create_class_and_chapter(professor_token)
        r = requests.post(
            f"{API_URL}/chapters/{chapter_id}/generate-exercises",
            headers=auth_headers(professor_token),
            timeout=60,
        )
        # 200 = sync result, 202 = async queued, 400 = no content to generate from
        assert r.status_code in (200, 202, 400), f"Unexpected: {r.status_code} {r.text}"

    def test_generate_exercises_nonexistent_chapter_returns_404(self, professor_token):
        fake_id = "00000000-0000-0000-0000-000000000000"
        r = requests.post(
            f"{API_URL}/chapters/{fake_id}/generate-exercises",
            headers=auth_headers(professor_token),
            timeout=10,
        )
        assert r.status_code == 404

    def test_student_cannot_generate_exercises_for_other_professor(self, professor_token, student_token):
        _, chapter_id = _create_class_and_chapter(professor_token)
        r = requests.post(
            f"{API_URL}/chapters/{chapter_id}/generate-exercises",
            headers=auth_headers(student_token),
            timeout=10,
        )
        assert r.status_code in (403, 404)

    def test_generate_without_auth_returns_401(self):
        r = requests.post(f"{API_URL}/chapters/some-id/generate-exercises", timeout=10)
        assert r.status_code == 401

    def test_get_exercises_without_auth_returns_401(self):
        r = requests.get(f"{API_URL}/chapters/some-id/exercises", timeout=10)
        assert r.status_code == 401
