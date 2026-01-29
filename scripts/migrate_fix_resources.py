
import psycopg2
from dotenv import load_dotenv
import os
import sys

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Import get_db_connection from app.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from app import get_db_connection
except ImportError:
    # Fallback: define a simple connection function
    def get_db_connection():
        if not DATABASE_URL:
            raise Exception("DATABASE_URL environment variable is not set")
        return psycopg2.connect(DATABASE_URL)

def migrate():
    """Migrate database to fix resources table"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("Starting resource table migration...")
        
        # Add resource_type column to class_resources table
        print("\nAdding resource_type column to class_resources table...")
        try:
            cursor.execute("""
                ALTER TABLE class_resources 
                ADD COLUMN IF NOT EXISTS resource_type VARCHAR(50) DEFAULT 'link';
            """)
            print("   ✓ resource_type column added")
            
            # Update any null values to default
            cursor.execute("""
                UPDATE class_resources 
                SET resource_type = 'link' 
                WHERE resource_type IS NULL;
            """)
            print("   ✓ Updated existing records")
            
        except Exception as e:
            print(f"   ⚠ Error adding column (may already exist): {e}")

        conn.commit()
        cursor.close()
        conn.close()
        
        print("\n" + "="*50)
        print("Migration completed successfully!")
        print("="*50)
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        if conn:
            conn.rollback()
            conn.close()
        raise

if __name__ == "__main__":
    migrate()
