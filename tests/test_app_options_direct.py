"""
Tests that bypass @app.before_request to reach per-route OPTIONS handlers.
These handlers are normally intercepted by the global OPTIONS handler.
Strategy: Temporarily disable the before_request handler during these tests.
"""
import pytest
from unittest.mock import patch, MagicMock
from flask import Flask


class TestOptionsHandlersDirect:
    """Cover OPTIONS handlers by disabling the global handler"""

    def _disable_before_request(self, app_instance):
        """Remove the global OPTIONS handler temporarily"""
        # Flask stores before_request_funcs keyed by blueprint (None for app-level)
        original = app_instance.before_request_funcs.get(None, []).copy()
        app_instance.before_request_funcs[None] = [
            f for f in app_instance.before_request_funcs.get(None, [])
            if f.__name__ != "handle_options"
        ]
        return original

    def _restore_before_request(self, app_instance, original):
        """Restore the global OPTIONS handler"""
        app_instance.before_request_funcs[None] = original

    def test_signup_options(self, app, client, mock_db):
        """Lines 540-546: signup OPTIONS handler"""
        original = self._disable_before_request(app)
        try:
            response = client.options("/api/users/signup")
            assert response.status_code == 200
        finally:
            self._restore_before_request(app, original)

    def test_forgot_password_options(self, app, client, mock_db):
        """Lines 735-740: forgot-password OPTIONS handler"""
        original = self._disable_before_request(app)
        try:
            response = client.options("/api/users/forgot-password")
            assert response.status_code in [200, 429]
        finally:
            self._restore_before_request(app, original)

    def test_reset_password_options(self, app, client, mock_db):
        """Lines 823-828: reset-password OPTIONS handler"""
        original = self._disable_before_request(app)
        try:
            response = client.options("/api/users/reset-password")
            assert response.status_code == 200
        finally:
            self._restore_before_request(app, original)

    def test_create_class_options(self, app, client, mock_db):
        """Lines 2334-2339: create class OPTIONS handler"""
        original = self._disable_before_request(app)
        try:
            response = client.options("/api/classes")
            assert response.status_code == 200
        finally:
            self._restore_before_request(app, original)

    def test_upload_chapter_options(self, app, client, mock_db):
        """Lines 2999-3004: upload chapter OPTIONS handler"""
        original = self._disable_before_request(app)
        try:
            response = client.options("/api/classes/CLS1/chapters")
            assert response.status_code == 200
        finally:
            self._restore_before_request(app, original)

    def test_delete_chapter_options(self, app, client, mock_db):
        """Lines 3334-3339: chapter OPTIONS handler"""
        original = self._disable_before_request(app)
        try:
            response = client.options("/api/chapters/ch1")
            assert response.status_code == 200
        finally:
            self._restore_before_request(app, original)

    def test_ai_chat_options(self, app, client, mock_db):
        """Lines 3665-3669: AI chat OPTIONS handler"""
        original = self._disable_before_request(app)
        try:
            response = client.options("/api/ai/chat")
            assert response.status_code == 200
        finally:
            self._restore_before_request(app, original)

    def test_enroll_options(self, app, client, mock_db):
        """Lines 3858-3863: enroll OPTIONS handler"""
        original = self._disable_before_request(app)
        try:
            response = client.options("/api/classes/enroll")
            assert response.status_code == 200
        finally:
            self._restore_before_request(app, original)

    def test_add_resource_options(self, app, client, mock_db):
        """Lines 4794-4799: add resource OPTIONS handler"""
        original = self._disable_before_request(app)
        try:
            response = client.options("/api/classes/CLS1/resources")
            assert response.status_code == 200
        finally:
            self._restore_before_request(app, original)

    def test_delete_exercise_options(self, app, client, mock_db):
        """Lines 4918-4923: delete exercise OPTIONS handler"""
        original = self._disable_before_request(app)
        try:
            response = client.options("/api/exercises/ex1")
            assert response.status_code == 200
        finally:
            self._restore_before_request(app, original)

    def test_upload_resource_options(self, app, client, mock_db):
        """Lines 5028-5032: upload resource OPTIONS handler"""
        original = self._disable_before_request(app)
        try:
            response = client.options("/api/classes/CLS1/resources/upload")
            assert response.status_code == 200
        finally:
            self._restore_before_request(app, original)

    def test_manage_resource_options(self, app, client, mock_db):
        """Lines 5205-5210: manage resource OPTIONS handler"""
        original = self._disable_before_request(app)
        try:
            response = client.options("/api/classes/CLS1/resources/res1")
            assert response.status_code == 200
        finally:
            self._restore_before_request(app, original)

