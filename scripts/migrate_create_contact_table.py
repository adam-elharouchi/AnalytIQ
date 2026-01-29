
import os
import psycopg2
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    if not DATABASE_URL:
        print("Error: DATABASE_URL is not set.")
        return None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def create_contact_table():
    conn = get_db_connection()
    if not conn:
        return

    try:
        cur = conn.cursor()
        
        print("Creating contact_submissions table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS contact_submissions (
                submission_id SERIAL PRIMARY KEY,
                user_id VARCHAR(255),
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL,
                subject VARCHAR(255) NOT NULL,
                message TEXT NOT NULL,
                status VARCHAR(50) DEFAULT 'submitted',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        conn.commit()
        print("Successfully created contact_submissions table.")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error creating table: {e}")
        if conn:
            conn.rollback()
            conn.close()

if __name__ == "__main__":
    create_contact_table()
