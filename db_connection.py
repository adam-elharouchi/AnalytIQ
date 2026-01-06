import psycopg2
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

# Try to get DATABASE_URL first (Supabase format), otherwise use individual variables
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Use connection string (Supabase/Heroku style)
    try:
        connection = psycopg2.connect(DATABASE_URL)
        print("Connection successful using DATABASE_URL!")
    except Exception as e:
        print(f"Failed to connect using DATABASE_URL: {e}")
        connection = None
else:
    # Fall back to individual connection parameters
    USER = os.getenv("user")
    PASSWORD = os.getenv("password")
    HOST = os.getenv("host")
    PORT = os.getenv("port")
    DBNAME = os.getenv("dbname")
    
    try:
        connection = psycopg2.connect(
            user=USER,
            password=PASSWORD,
            host=HOST,
            port=PORT,
            dbname=DBNAME
        )
        print("Connection successful using individual parameters!")
    except Exception as e:
        print(f"Failed to connect: {e}")
        connection = None

if connection:
    try:
        # Create a cursor to execute SQL queries
        cursor = connection.cursor()
        
        # Example query
        cursor.execute("SELECT NOW();")
        result = cursor.fetchone()
        print("Current Time:", result)

        # Close the cursor and connection
        cursor.close()
        connection.close()
        print("Connection closed.")
    except Exception as e:
        print(f"Error executing query: {e}")
        if connection:
            connection.close()

