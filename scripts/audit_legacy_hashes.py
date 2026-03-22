#!/usr/bin/env python3
"""
Audit: check whether any users still have a legacy (non-bcrypt) password hash.

Background
----------
The original sign-up flow used a JavaScript-style djb2 hash.  When bcrypt was
introduced, verify_password() was updated to fall back to the legacy check and
set needs_rehash=True so the hash is upgraded on next successful login.
hash_password_legacy() in core/auth.py can be deleted once this script
confirms zero legacy users remain.

Usage
-----
    python scripts/audit_legacy_hashes.py

Requires DATABASE_URL to be set (or a .env file in the project root).

Exit codes
----------
    0  — no legacy hashes found (safe to delete hash_password_legacy)
    1  — legacy hashes found (do NOT delete the function yet)
    2  — error connecting / querying
"""

import os
import sys

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL is not set.", file=sys.stderr)
    sys.exit(2)

try:
    import psycopg2
except ImportError:
    print("ERROR: psycopg2 is not installed. Run: pip install psycopg2-binary", file=sys.stderr)
    sys.exit(2)

try:
    conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
    cur = conn.cursor()

    # bcrypt hashes always start with $2b$ or $2a$.
    # Any password_hash that does NOT start with $2 is a legacy hash.
    cur.execute("""
        SELECT COUNT(*) AS legacy_count
        FROM users
        WHERE password_hash IS NOT NULL
          AND password_hash NOT LIKE '$2%'
    """)
    row = cur.fetchone()
    legacy_count = row[0] if row else 0

    cur.close()
    conn.close()

except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(2)

if legacy_count == 0:
    print("✅  No legacy password hashes found.")
    print()
    print("You can now safely remove hash_password_legacy() from core/auth.py")
    print("and the legacy fallback branch in verify_password().")
    sys.exit(0)
else:
    print(f"⚠️   {legacy_count} user(s) still have a legacy password hash.")
    print()
    print("These users will be upgraded to bcrypt on their next successful login.")
    print("Re-run this script after some time to check progress.")
    print()
    print("To see which accounts are affected:")
    print("  SELECT user_id, email, created_at")
    print("  FROM users")
    print("  WHERE password_hash IS NOT NULL")
    print("    AND password_hash NOT LIKE '$2%'")
    print("  ORDER BY created_at;")
    sys.exit(1)
