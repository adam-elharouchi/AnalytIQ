import os
import sys

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add python directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from workers.tasks import send_email_async

def test():
    # Retrieve test email from arg
    if len(sys.argv) < 2:
        print("Usage: python test_email.py <your-email>")
        return

    recipient = sys.argv[1]
    print(f"Testing Resend email to: {recipient}")
    
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        print("❌ RESEND_API_KEY is not set in environment or .env file.")
        return
    else:
        print(f"✅ Found RESEND_API_KEY: {api_key[:5]}...{api_key[-4:] if len(api_key)>4 else ''}")

    sender = os.getenv("MAIL_DEFAULT_SENDER", "techsupport@myanalytiq.org")
    print(f"✅ Sender configured as: {sender}")

    try:
        result = send_email_async(
            recipient=recipient,
            subject="Test Email from AnalytIQ (Resend)",
            body="<h1>Hello!</h1><p>This is a test email to verify Resend is working correctly.</p>"
        )
        print("Task Result:", result)
        if result.get("success"):
            print("✅ Email sent successfully via the task.")
        else:
            print("❌ Failed to send email via the task.")
            
    except Exception as e:
        print("❌ Exception occurred during sending:", str(e))

if __name__ == "__main__":
    test()
