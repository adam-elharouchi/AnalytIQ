#!/usr/bin/env python3
"""Sends reports/ADAM_DAILY.md to Adam. Deterministic. Recipient is HARDCODED —
changing it requires Adam editing this file himself (guardrail #1 exception)."""
import os, smtplib, ssl, sys, datetime, pathlib
from email.mime.text import MIMEText

RECIPIENT = "adamelharouchi5@gmail.com"   # HARDCODED. Agents may not modify this line.

repo = pathlib.Path(__file__).resolve().parent.parent
digest = repo / "reports" / "ADAM_DAILY.md"
if not digest.exists():
    sys.exit("No ADAM_DAILY.md found — orchestrator run likely failed.")

# Freshness gate. Nothing ever deletes ADAM_DAILY.md, so without this check a
# failed orchestrator run would re-send YESTERDAY's brief under today's subject
# line — and daily_cycle.sh would read the success and stamp the day complete,
# suppressing its own 13:00/19:00 retries. Exiting non-zero here is what makes
# the catch-up schedule actually work.
today = datetime.date.today()
written = datetime.date.fromtimestamp(digest.stat().st_mtime)
if written != today:
    sys.exit(
        f"ADAM_DAILY.md is stale (written {written}, today is {today}) — refusing "
        "to send. The orchestrator run failed; the next trigger will retry."
    )

body = digest.read_text(encoding="utf-8")
try:
    user = os.environ["DIGEST_SMTP_USER"]
    pw = os.environ["DIGEST_SMTP_PASS"]
except KeyError as missing:
    sys.exit(f"{missing} not set — is ~/.analytiq_env present and sourced?")

msg = MIMEText(body, "plain", "utf-8")
msg["Subject"] = f"AnalytIQ Daily — {datetime.date.today():%b %d} — agents' work + YOUR tasks"
msg["From"] = user
msg["To"] = RECIPIENT

# timeout is required: a hung TLS handshake with no timeout blocks the launchd
# job forever, and later triggers then stack processes behind it.
ctx = ssl.create_default_context()
with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx, timeout=30) as s:
    s.login(user, pw)
    s.sendmail(user, [RECIPIENT], msg.as_string())
print("Digest sent.")
