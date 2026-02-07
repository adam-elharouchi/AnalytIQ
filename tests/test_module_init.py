"""
Tests for module-level initialization code using importlib.reload().
Covers ImportError handlers and exception fallbacks that only run at import time.

IMPORTANT: Each test saves and restores module state to avoid corrupting
other tests. Tests are isolated via careful save/restore patterns.
"""
import pytest
import sys
import os
import importlib
from unittest.mock import patch, MagicMock, call


# ========================================================================
# tasks.py ImportError handlers (lines 21-22, 26-27, 32-33)
# ========================================================================

class TestTasksImportErrors:
    """Cover ImportError fallbacks in tasks.py module init"""

    def test_pdf_processor_import_error(self):
        """Lines 21-22: pdf_processor import fails"""
        import tasks as tasks_module

        # Save original state
        orig_extract = tasks_module.extract_text_from_pdf_bytes
        orig_pdf_mod = sys.modules.get("pdf_processor")

        try:
            # Simulate ImportError by setting module to None in sys.modules
            sys.modules["pdf_processor"] = None
            importlib.reload(tasks_module)
            assert tasks_module.extract_text_from_pdf_bytes is None
        finally:
            # Restore
            if orig_pdf_mod is not None:
                sys.modules["pdf_processor"] = orig_pdf_mod
            else:
                sys.modules.pop("pdf_processor", None)
            importlib.reload(tasks_module)

    def test_exercise_generator_import_error(self):
        """Lines 26-27: exercise_generator import fails"""
        import tasks as tasks_module

        orig_gen = tasks_module.generate_exercises_from_pdf_content
        orig_gen_mod = sys.modules.get("exercise_generator")

        try:
            sys.modules["exercise_generator"] = None
            importlib.reload(tasks_module)
            assert tasks_module.generate_exercises_from_pdf_content is None
        finally:
            if orig_gen_mod is not None:
                sys.modules["exercise_generator"] = orig_gen_mod
            else:
                sys.modules.pop("exercise_generator", None)
            importlib.reload(tasks_module)

    def test_flask_mail_import_error(self):
        """Lines 32-33: flask_mail import fails"""
        import tasks as tasks_module

        orig_message = tasks_module.Message
        orig_mail_mod = sys.modules.get("flask_mail")

        try:
            sys.modules["flask_mail"] = None
            importlib.reload(tasks_module)
            assert tasks_module.Message is None
        finally:
            if orig_mail_mod is not None:
                sys.modules["flask_mail"] = orig_mail_mod
            else:
                sys.modules.pop("flask_mail", None)
            importlib.reload(tasks_module)


# ========================================================================
# cache.py Redis exception (lines 29-31)
# ========================================================================

class TestCacheRedisException:
    """Cover Redis connection failure in cache.py module init"""

    def test_redis_connection_fails(self):
        """Lines 29-31: redis.ping() raises, redis_client set to None"""
        import cache as cache_module

        orig_client = cache_module.redis_client
        orig_redis_mod = sys.modules.get("redis")

        try:
            # Create a mock redis module where from_url returns a client that fails ping
            mock_redis = MagicMock()
            mock_client = MagicMock()
            mock_client.ping.side_effect = Exception("Connection refused")
            mock_redis.from_url.return_value = mock_client

            sys.modules["redis"] = mock_redis
            importlib.reload(cache_module)
            assert cache_module.redis_client is None
        finally:
            if orig_redis_mod is not None:
                sys.modules["redis"] = orig_redis_mod
            else:
                sys.modules.pop("redis", None)
            importlib.reload(cache_module)


# ========================================================================
# supabase_storage.py no-credentials + ImportError (lines 25-29)
# ========================================================================

class TestSupabaseStorageInit:
    """Cover supabase_storage.py init paths"""

    def test_supabase_no_credentials(self):
        """Lines 25-26: SUPABASE_URL/KEY not set"""
        import supabase_storage as supa_module

        orig_supabase = supa_module.supabase
        orig_url = supa_module.SUPABASE_URL
        orig_key = supa_module.SUPABASE_KEY

        try:
            with patch.dict(os.environ, {"SUPABASE_URL": "", "SUPABASE_KEY": ""}, clear=False):
                importlib.reload(supa_module)
                assert supa_module.supabase is None
        finally:
            # Restore env and reload
            supa_module.SUPABASE_URL = orig_url
            supa_module.SUPABASE_KEY = orig_key
            importlib.reload(supa_module)

    def test_supabase_import_error(self):
        """Lines 27-29: supabase library not installed"""
        import supabase_storage as supa_module

        orig_supabase = supa_module.supabase
        orig_supa_mod = sys.modules.get("supabase")

        try:
            sys.modules["supabase"] = None
            importlib.reload(supa_module)
            assert supa_module.supabase is None
        finally:
            if orig_supa_mod is not None:
                sys.modules["supabase"] = orig_supa_mod
            else:
                sys.modules.pop("supabase", None)
            importlib.reload(supa_module)


# ========================================================================
# celery_app.py if __name__ == "__main__" (line 52)
# ========================================================================

class TestCeleryAppMain:
    """Cover celery_app.py line 52: celery_app.start()"""

    def test_celery_main_block(self):
        """Line 52: celery_app.start() when run as __main__"""
        import celery_app as celery_module

        # Read the source file and exec it with __name__ = "__main__"
        import types

        mock_celery = MagicMock()
        mock_celery_class = MagicMock(return_value=mock_celery)

        # Create a fake module namespace simulating __main__ execution
        fake_globals = {
            "__name__": "__main__",
            "__file__": celery_module.__file__,
        }

        # Patch Celery constructor to return our mock
        with patch("celery.Celery", mock_celery_class):
            with patch("dotenv.load_dotenv"):
                source_path = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)), "celery_app.py"
                )
                with open(source_path) as f:
                    code = f.read()
                exec(compile(code, source_path, "exec"), fake_globals)

        # The mock celery instance's start() should have been called
        mock_celery.start.assert_called_once()


# ========================================================================
# app.py v1 alias exception handlers (lines 5076-5081)
# ========================================================================

class TestAppV1AliasExceptions:
    """Cover register_api_v1_aliases exception handlers in app.py"""

    def test_v1_alias_assertion_error(self):
        """Lines 5076-5078: AssertionError when rule already exists"""
        from app import app as flask_app, register_api_v1_aliases

        # Mock add_url_rule to raise AssertionError (rule already exists)
        with patch.object(flask_app, "add_url_rule", side_effect=AssertionError("Rule exists")):
            with flask_app.app_context():
                # Should not raise - AssertionError is caught and ignored
                register_api_v1_aliases(flask_app)

    def test_v1_alias_generic_exception(self):
        """Lines 5079-5081: generic Exception during alias registration"""
        from app import app as flask_app, register_api_v1_aliases

        # Mock add_url_rule to raise a generic Exception
        with patch.object(flask_app, "add_url_rule", side_effect=Exception("Something broke")):
            with flask_app.app_context():
                # Should not raise - Exception is caught and ignored
                register_api_v1_aliases(flask_app)
