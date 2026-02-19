"""
E2E: Chapter upload flows.
Requires a running app: FLASK_ENV=testing python app.py
"""
import uuid
import pytest
import requests

from conftest import API_URL, auth_headers


pytestmark = pytest.mark.e2e


def _uid():
    return uuid.uuid4().hex[:8]


def _create_class(token: str) -> str:
    """Create a class and return its ID."""
    uid = _uid()
    r = requests.post(
        f"{API_URL}/classes",
        json={"name": f"Test Class {uid}", "class_code": f"TST{uid[:5].upper()}"},
        headers=auth_headers(token),
        timeout=10,
    )
    assert r.status_code == 201, f"Class creation failed: {r.text}"
    return str(r.json()["class"]["id"])


class TestChapterUpload:
    def test_upload_txt_chapter_returns_201(self, professor_token):
        class_id = _create_class(professor_token)
        content = b"Introduction to Python\n\nPython is a high-level programming language."
        r = requests.post(
            f"{API_URL}/classes/{class_id}/chapters",
            data={"title": "Intro to Python"},
            files={"pdf_file": ("intro.txt", content, "text/plain")},
            headers={"Authorization": f"Bearer {professor_token}"},
            timeout=30,
        )
        assert r.status_code == 201, f"Upload failed: {r.text}"
        body = r.json()
        assert "chapter" in body or "id" in body

    def test_uploaded_chapter_appears_in_list(self, professor_token):
        class_id = _create_class(professor_token)
        uid = _uid()
        content = b"Chapter content here."
        requests.post(
            f"{API_URL}/classes/{class_id}/chapters",
            data={"title": f"Chapter {uid}"},
            files={"pdf_file": ("notes.txt", content, "text/plain")},
            headers={"Authorization": f"Bearer {professor_token}"},
            timeout=30,
        )
        r = requests.get(
            f"{API_URL}/classes/{class_id}/chapters",
            headers=auth_headers(professor_token),
            timeout=10,
        )
        assert r.status_code == 200
        titles = [ch["title"] for ch in r.json().get("chapters", [])]
        assert f"Chapter {uid}" in titles

    def test_upload_unsupported_extension_returns_400(self, professor_token):
        class_id = _create_class(professor_token)
        r = requests.post(
            f"{API_URL}/classes/{class_id}/chapters",
            data={"title": "Bad File"},
            files={"pdf_file": ("bad.xyz", b"data", "application/octet-stream")},
            headers={"Authorization": f"Bearer {professor_token}"},
            timeout=10,
        )
        assert r.status_code == 400

    def test_upload_missing_title_returns_400(self, professor_token):
        class_id = _create_class(professor_token)
        r = requests.post(
            f"{API_URL}/classes/{class_id}/chapters",
            data={},
            files={"pdf_file": ("notes.txt", b"content", "text/plain")},
            headers={"Authorization": f"Bearer {professor_token}"},
            timeout=10,
        )
        assert r.status_code == 400

    def test_student_cannot_upload_chapter(self, student_token):
        """Students cannot create classes, so chapter upload is blocked at class level."""
        fake_class_id = "00000000-0000-0000-0000-000000000000"
        r = requests.post(
            f"{API_URL}/classes/{fake_class_id}/chapters",
            data={"title": "Hacked"},
            files={"pdf_file": ("hack.txt", b"data", "text/plain")},
            headers={"Authorization": f"Bearer {student_token}"},
            timeout=10,
        )
        assert r.status_code in (403, 404)

    def test_upload_without_auth_returns_401(self):
        r = requests.post(
            f"{API_URL}/classes/some-id/chapters",
            data={"title": "No Auth"},
            files={"pdf_file": ("x.txt", b"data", "text/plain")},
            timeout=10,
        )
        assert r.status_code == 401
