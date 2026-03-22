"""
Tests for tasks.py email functionality with Resend.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestSendEmailAsync:
    """Cover send_email_async paths in tasks.py"""

    def test_send_email_core_error_returns_failure(self):
        from workers.tasks import send_email_async
        from unittest.mock import patch
        from celery.exceptions import MaxRetriesExceededError

        with patch("core.email.send_email", side_effect=RuntimeError("RESEND_API_KEY is missing")):
            with patch.object(send_email_async, "retry", side_effect=MaxRetriesExceededError()):
                result = send_email_async(
                    recipient="test@test.com",
                    subject="Test",
                    body="<p>Hello</p>",
                )
                assert result["success"] == False
                assert "error" in result

    def test_send_email_no_api_key(self):
        from workers.tasks import send_email_async
        import workers.tasks as tasks_module

        original_resend = getattr(tasks_module, "resend", None)
        if not original_resend:
            pytest.skip("Resend not installed")

        with patch.dict("os.environ", {}, clear=True):
            with patch.object(original_resend, "api_key", None):
                result = send_email_async(
                    recipient="test@test.com",
                    subject="Test",
                    body="<p>Hello</p>",
                )
                assert result["success"] == False
                assert "missing" in result.get("error", "").lower()

    def test_send_email_success(self):
        from workers.tasks import send_email_async
        import workers.tasks as tasks_module

        original_resend = getattr(tasks_module, "resend", None)
        if not original_resend:
            pytest.skip("Resend not installed")

        with patch.dict(
            "os.environ",
            {"RESEND_API_KEY": "re_test_123", "MAIL_DEFAULT_SENDER": "test@test.com"},
        ):
            with patch.object(
                original_resend.Emails, "send", return_value={"id": "evt_123"}
            ) as mock_send:
                result = send_email_async(
                    recipient="user@test.com",
                    subject="Test Subject",
                    body="<p>Hello</p>",
                )
                assert result["success"] == True
                assert result["recipient"] == "user@test.com"
                mock_send.assert_called_once()
