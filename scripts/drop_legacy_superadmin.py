#!/usr/bin/env python3
"""
scripts/drop_legacy_superadmin.py

This script permanently drops the 'is_super_admin' column from the 'users' table.
This should only be run after all users have been migrated to the new 'superadmin' role pattern.
"""
import sys
import os

# Add parent directory to path to import db
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from core.database import get_db_connection

def drop_legacy_column():
    print("Initiating DROP COLUMN operation for 'is_super_admin'...")
    
    with app.app_context():
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Check if column exists first
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='users' AND column_name='is_super_admin';
            """)
            
            if cur.fetchone() is None:
                print("The 'is_super_admin' column has already been removed from the 'users' table.")
                return
            
            # Drop the column
            print("Dropping column 'is_super_admin' from 'users' table...")
            cur.execute("ALTER TABLE users DROP COLUMN is_super_admin;")
            conn.commit()
            
            print("\nSuccess: The legacy 'is_super_admin' boolean has been permanently removed from the database schema.")
            
        except Exception as e:
            conn.rollback()
            print(f"\nDatabase error during column drop: {e}")
            sys.exit(1)
        finally:
            if 'cur' in locals():
                cur.close()
            if 'conn' in locals():
                conn.close()

if __name__ == "__main__":
    drop_legacy_column()
