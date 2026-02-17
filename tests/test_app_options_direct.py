"""
Tests for OPTIONS preflight handling.
Per-route OPTIONS handlers have been removed — all preflight is now handled
by the global @app.before_request handle_options() hook.  These tests verify
that behaviour.
"""
import pytest


class TestOptionsHandlersViaBeforeRequest:
    """Verify that the global before_request hook handles OPTIONS for every route."""

    def test_signup_options(self, app, client):
        """Global handler must respond to OPTIONS /api/users/signup"""
        response = client.options("/api/users/signup")
        assert response.status_code == 200

    def test_signin_options(self, app, client):
        """Global handler must respond to OPTIONS /api/users/signin"""
        response = client.options("/api/users/signin")
        assert response.status_code == 200

    def test_forgot_password_options(self, app, client):
        """Global handler must respond to OPTIONS /api/users/forgot-password"""
        response = client.options("/api/users/forgot-password")
        assert response.status_code == 200

    def test_reset_password_options(self, app, client):
        """Global handler must respond to OPTIONS /api/users/reset-password"""
        response = client.options("/api/users/reset-password")
        assert response.status_code == 200

    def test_create_class_options(self, app, client):
        """Global handler must respond to OPTIONS /api/classes"""
        response = client.options("/api/classes")
        assert response.status_code == 200

    def test_upload_chapter_options(self, app, client):
        """Global handler must respond to OPTIONS /api/classes/<id>/chapters"""
        response = client.options("/api/classes/CLS1/chapters")
        assert response.status_code == 200

    def test_delete_chapter_options(self, app, client):
        """Global handler must respond to OPTIONS /api/chapters/<id>"""
        response = client.options("/api/chapters/ch1")
        assert response.status_code == 200

    def test_ai_chat_options(self, app, client):
        """Global handler must respond to OPTIONS /api/ai/chat"""
        response = client.options("/api/ai/chat")
        assert response.status_code == 200

    def test_enroll_options(self, app, client):
        """Global handler must respond to OPTIONS /api/classes/enroll"""
        response = client.options("/api/classes/enroll")
        assert response.status_code == 200

    def test_add_resource_options(self, app, client):
        """Global handler must respond to OPTIONS /api/classes/<id>/resources"""
        response = client.options("/api/classes/CLS1/resources")
        assert response.status_code == 200

    def test_delete_exercise_options(self, app, client):
        """Global handler must respond to OPTIONS /api/exercises/<id>"""
        response = client.options("/api/exercises/ex1")
        assert response.status_code == 200

    def test_upload_resource_options(self, app, client):
        """Global handler must respond to OPTIONS /api/classes/<id>/resources/upload"""
        response = client.options("/api/classes/CLS1/resources/upload")
        assert response.status_code == 200

    def test_manage_resource_options(self, app, client):
        """Global handler must respond to OPTIONS /api/classes/<id>/resources/<res_id>"""
        response = client.options("/api/classes/CLS1/resources/res1")
        assert response.status_code == 200
