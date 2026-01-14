"""
Migration script to add role system and class management tables
Run this script to update the database schema
"""
import psycopg2
from dotenv import load_dotenv
import os
import sys

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Import get_db_connection from app.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from app import get_db_connection
except ImportError:
    # Fallback: define a simple connection function
    def get_db_connection():
        if not DATABASE_URL:
            raise Exception("DATABASE_URL environment variable is not set")
        return psycopg2.connect(DATABASE_URL)

def detect_role_from_email(email):
    """Detect user role from email domain"""
    if not email:
        return 'student'
    email_lower = email.lower()
    if email_lower.endswith('@hult.edu') or email_lower.endswith('@faculty.hult.edu'):
        return 'professor'
    elif email_lower.endswith('@student.hult.edu'):
        return 'student'
    return 'student'  # Default to student

def migrate():
    """Run all migrations"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("Starting migration...")
        
        # 1. Add role column to users table
        print("\n1. Adding role column to users table...")
        try:
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'student';
            """)
            print("   ✓ Role column added")
        except Exception as e:
            print(f"   ⚠ Error adding role column (may already exist): {e}")
        
        # 2. Update existing users' roles based on email
        print("\n2. Updating existing users' roles based on email domain...")
        cursor.execute("SELECT user_id, email FROM users WHERE role IS NULL OR role = 'student'")
        users = cursor.fetchall()
        updated = 0
        for user_id, email in users:
            role = detect_role_from_email(email)
            if role == 'professor':
                cursor.execute("UPDATE users SET role = %s WHERE user_id = %s", (role, user_id))
                updated += 1
        print(f"   ✓ Updated {updated} users to professor role")
        
        # 3. Create classes table
        print("\n3. Creating classes table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS classes (
                id SERIAL PRIMARY KEY,
                class_id VARCHAR(255) UNIQUE NOT NULL,
                professor_id VARCHAR(255) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                name VARCHAR(500) NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_classes_professor_id ON classes(professor_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_classes_class_id ON classes(class_id);")
        print("   ✓ Classes table created")
        
        # 4. Create class_enrollments table
        print("\n4. Creating class_enrollments table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS class_enrollments (
                id SERIAL PRIMARY KEY,
                class_id VARCHAR(255) NOT NULL REFERENCES classes(class_id) ON DELETE CASCADE,
                student_id VARCHAR(255) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(class_id, student_id)
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_enrollments_class_id ON class_enrollments(class_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_enrollments_student_id ON class_enrollments(student_id);")
        print("   ✓ Class enrollments table created")
        
        # 5. Create class_chapters table
        print("\n5. Creating class_chapters table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS class_chapters (
                id SERIAL PRIMARY KEY,
                chapter_id VARCHAR(255) UNIQUE NOT NULL,
                class_id VARCHAR(255) NOT NULL REFERENCES classes(class_id) ON DELETE CASCADE,
                title VARCHAR(500) NOT NULL,
                description TEXT,
                chapter_number INTEGER,
                pdf_url TEXT,
                pdf_filename VARCHAR(500),
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chapters_class_id ON class_chapters(class_id);")
        print("   ✓ Class chapters table created")
        
        # 6. Create class_exercises table
        print("\n6. Creating class_exercises table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS class_exercises (
                id SERIAL PRIMARY KEY,
                exercise_id VARCHAR(255) UNIQUE NOT NULL,
                chapter_id VARCHAR(255) NOT NULL REFERENCES class_chapters(chapter_id) ON DELETE CASCADE,
                class_id VARCHAR(255) NOT NULL REFERENCES classes(class_id) ON DELETE CASCADE,
                title VARCHAR(500) NOT NULL,
                description TEXT,
                difficulty VARCHAR(20) DEFAULT 'medium',
                solution_code TEXT NOT NULL,
                exercise_number INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_exercises_chapter_id ON class_exercises(chapter_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_exercises_class_id ON class_exercises(class_id);")
        print("   ✓ Class exercises table created")
        
        # 7. Add class columns to practice_progress table
        print("\n7. Adding class columns to practice_progress table...")
        try:
            cursor.execute("ALTER TABLE practice_progress ADD COLUMN IF NOT EXISTS class_id VARCHAR(255);")
            cursor.execute("ALTER TABLE practice_progress ADD COLUMN IF NOT EXISTS class_exercise_id VARCHAR(255);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_practice_progress_class_id ON practice_progress(class_id);")
            print("   ✓ Class columns added to practice_progress")
        except Exception as e:
            print(f"   ⚠ Error adding columns (may already exist): {e}")
        
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
