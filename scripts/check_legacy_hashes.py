"""
Check for users with legacy (non-bcrypt) password hashes.

Usage:
    python3 scripts/check_legacy_hashes.py

If the output shows 0 legacy-hash users it is safe to delete
hash_password_legacy() from auth_helpers.py and the corresponding
branch in verify_password().

Exit codes:
    0  — no legacy hashes found (safe to delete hash_password_legacy)
    1  — legacy hashes exist (migration still in progress)
    2  — error (missing env var, connection failure, etc.)
"""

import os
import sys

import psycopg2


def main():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable is not set.", file=sys.stderr)
        sys.exit(2)

    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()

        # Bcrypt hashes always start with $2a$ or $2b$.
        # Any row whose password_hash does NOT start with '$2' is a legacy hash.
        cur.execute(
            """
            SELECT COUNT(*) AS legacy_count
            FROM users
            WHERE password_hash IS NOT NULL
              AND password_hash NOT LIKE '$2%';
            """
        )
        (legacy_count,) = cur.fetchone()

        cur.execute("SELECT COUNT(*) FROM users;")
        (total_count,) = cur.fetchone()

        cur.close()
        conn.close()

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)

    print(f"Total users:           {total_count}")
    print(f"Legacy-hash users:     {legacy_count}")
    print(f"Bcrypt-hash users:     {total_count - legacy_count}")

    if legacy_count == 0:
        print("\n✅ No legacy hashes found.")
        print("   It is safe to delete hash_password_legacy() from auth_helpers.py")
        print("   and remove the legacy branch in verify_password().")
        sys.exit(0)
    else:
        print(f"\n⚠️  {legacy_count} user(s) still have legacy hashes.")
        print("   Do NOT delete hash_password_legacy() yet.")
        print("   These users will be automatically re-hashed to bcrypt on next login")
        print("   (verify_password returns needs_rehash=True for legacy hashes).")
        sys.exit(1)


if __name__ == "__main__":
    main()
