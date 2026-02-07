"""
Tests for tasks.py email functionality - covering lines 197 and 203.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestSendEmailAsync:
    """Cover send_email_async paths in tasks.py"""

    def test_send_email_no_mail_configured(self):
        """Line 197: mail is None"""
        from tasks import send_email_async

        # The function does: from app import app, mail
        # So we need to patch what 'from app import ...' returns
        mock_app_module = MagicMock()
        mock_app_module.app = MagicMock()
        mock_app_module.mail = None

        import sys
        with patch.dict(sys.modules, {"app": mock_app_module}):
            result = send_email_async(
                recipient="test@test.com",
                subject="Test",
                body="<p>Hello</p>",
            )
            assert result["success"] == False
            assert "not configured" in result.get("error", "")

    def test_send_email_success(self):
        """Line 203: successful email send"""
        from tasks import send_email_async

        mock_mail = MagicMock()
        mock_flask_app = MagicMock()

        # Mock both the app module (for `from app import app, mail`) and Message
        mock_app_module = MagicMock()
        mock_app_module.app = mock_flask_app
        mock_app_module.mail = mock_mail

        mock_message = MagicMock()

        import sys
        import tasks as tasks_module
        original_message = getattr(tasks_module, "Message", None)

        try:
            tasks_module.Message = MagicMock(return_value=mock_message)
            with patch.dict(sys.modules, {"app": mock_app_module}):
                result = send_email_async(
                    recipient="test@test.com",
                    subject="Test Subject",
                    body="<p>Hello</p>",
                )
                assert result["success"] == True
                assert result["recipient"] == "test@test.com"
        finally:
            tasks_module.Message = original_message
