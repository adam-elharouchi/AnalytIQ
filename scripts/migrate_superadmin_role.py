#!/usr/bin/env python3
"""
scripts/migrate_superadmin_role.py

This script safely transitions users from the legacy 'is_super_admin' boolean column
to the new dedicated 'superadmin' role designation in the users table.
"""
import sys
import os

# Add parent directory to path to import db
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from db import get_db_connection

def migrate_superadmin_roles():
    print("Starting Superadmin role migration...")
    
    with app.app_context():
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Find users who are currently flagged as super admins
            cur.execute("SELECT user_id, email, name, role FROM users WHERE is_super_admin = TRUE;")
            super_admins = cur.fetchall()
            
            if not super_admins:
                print("No existing super admin accounts found to migrate.")
                return
            
            print(f"Found {len(super_admins)} account(s) to migrate.")
            
            success_count = 0
            for user in super_admins:
                user_id, email, name, existing_role = user
                
                # Only update if they aren't already a superadmin role
                if existing_role != 'superadmin':
                    print(f"Migrating: {name} ({email}) ...")
                    cur.execute(
                        "UPDATE users SET role = 'superadmin', updated_at = CURRENT_TIMESTAMP WHERE user_id = %s;",
                        (user_id,)
                    )
                    success_count += 1
                else:
                    print(f"Skipping: {name} ({email}) is already assigned the superadmin role.")
            
            conn.commit()
            print(f"\nMigration complete. Successfully updated {success_count} account(s).")
            
        except Exception as e:
            conn.rollback()
            print(f"\nDatabase error during migration: {e}")
            sys.exit(1)
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()

if __name__ == "__main__":
    migrate_superadmin_roles()
