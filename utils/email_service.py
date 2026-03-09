import logging
import os

import resend

logger = logging.getLogger(__name__)

# Initialize Resend API key
resend.api_key = os.getenv("RESEND_API_KEY")

# Default sender (MUST match verified domain in Resend)
FROM_EMAIL = os.getenv("MAIL_DEFAULT_SENDER", "techsupport@myanalytiq.org")


def send_email(to_email: str, subject: str, html_content: str):
    """Send email using Resend API."""
    # Fallback initialization check in case env vars were loaded later
    if not resend.api_key:
        resend.api_key = os.getenv("RESEND_API_KEY")

    if not resend.api_key:
        raise RuntimeError("RESEND_API_KEY is missing from environment variables")

    from_email = os.getenv("MAIL_DEFAULT_SENDER", FROM_EMAIL)
    logger.info("Sending email FROM: %s TO: %s", from_email, to_email)

    response = resend.Emails.send(
        {
            "from": f"AnalytIQ Support <{from_email}>",
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        }
    )

    logger.info("Resend success: %s", response)
    return response
