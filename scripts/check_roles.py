import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

db_url = os.environ.get("DATABASE_URL")
if not db_url:
    print("No DATABASE_URL found in .env file.")
    exit(1)

try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute("SELECT email, role FROM users LIMIT 15;")
    rows = cur.fetchall()
    print("Here are the users in the remote DB:")
    for row in rows:
        print(row)
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
