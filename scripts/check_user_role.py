import os
import sys
import psycopg2

# Get DATABASE_URL
db_url = os.environ.get("DATABASE_URL")
if not db_url:
    # Try local default matching deployment config
    db_url = "postgresql://postgres:postgres@localhost:5432/analytiq"

try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute("SELECT email, role, is_super_admin FROM users LIMIT 10;")
    rows = cur.fetchall()
    print("Found users:")
    for row in rows:
        print(row)
        
    cur.close()
    conn.close()
except Exception as e:
    print(f"Failed to query database: {e}")
