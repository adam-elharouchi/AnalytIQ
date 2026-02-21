"""
Tests for tasks.py email functionality - covering lines 197 and 203.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestSendEmailAsync:
    """Cover send_email_async paths in tasks.py"""

    @patch("config.RESEND_API_KEY", None)
    def test_send_email_no_mail_configured(self):
        """Test sending email when Resend key is not configured"""
        from tasks import send_email_async

        result = send_email_async(
            recipient="test@test.com",
            subject="Test",
            body="<p>Hello</p>",
        )
        assert result["success"] == False
        assert "not configured" in result.get("error", "")

    @patch("config.RESEND_API_KEY", "test_key")
    @patch("config.MAIL_DEFAULT_SENDER", "test@test.com")
    def test_send_email_success(self):
        """Test successful email send"""
        from tasks import send_email_async
        import resend

        with patch.object(resend.Emails, 'send') as mock_send:
            result = send_email_async(
                recipient="test@test.com",
                subject="Test Subject",
                body="<p>Hello</p>",
            )
            assert result["success"] == True
            assert result["recipient"] == "test@test.com"
            mock_send.assert_called_once()
