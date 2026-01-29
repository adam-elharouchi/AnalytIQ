"""Quick script to check existing users in the database"""
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    
    cursor.execute("SELECT user_id, name, email, created_at FROM users ORDER BY created_at")
    users = cursor.fetchall()
    
    print(f"\nCurrent users in database: {count}\n")
    if users:
        print("Existing users:")
        for user in users:
            print(f"  - {user[1]} ({user[2]}) - ID: {user[0]}")
    else:
        print("No users found in database.\n")
    
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")

