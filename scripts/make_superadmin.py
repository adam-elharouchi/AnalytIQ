#!/usr/bin/env python3
import sys
import os

# Add parent directory to path to import db
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from core.database import get_db_connection

def make_superadmin(email):
    # Setup dummy user using auth_repo method so it uses test fixtures correctly
    with app.app_context():
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Check if user exists
            cur.execute("SELECT user_id, name, is_super_admin FROM users WHERE email = %s", (email,))
            user = cur.fetchone()
            
            if not user:
                print(f"Error: User with email '{email}' not found.")
                return

            if user[2]:
                print(f"User '{user[1]}' ({email}) is already a Super Admin.")
                return

            # Update user
            cur.execute("UPDATE users SET is_super_admin = TRUE, updated_at = CURRENT_TIMESTAMP WHERE email = %s", (email,))
            conn.commit()
            
            print(f"Success! User '{user[1]}' ({email}) is now a Super Admin.")
            
        except Exception as e:
            print(f"Database error: {e}")
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 make_superadmin.py <user_email>")
        sys.exit(1)
        
    email_arg = sys.argv[1]
    make_superadmin(email_arg)
