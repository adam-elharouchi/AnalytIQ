"""
Database Index Migration
Adds missing indexes to improve query performance
Run this script once to add indexes to existing database
"""

import psycopg2
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def add_indexes():
    """Add missing database indexes for performance optimization"""
    try:
        connection = psycopg2.connect(DATABASE_URL)
        cursor = connection.cursor()
        
        print("Adding database indexes...")
        
        # Indexes for class_exercises table
        print("  - Adding index on class_exercises(class_id)...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_class_exercises_class_id 
            ON class_exercises(class_id)
        """)
        
        print("  - Adding index on class_exercises(chapter_id)...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_class_exercises_chapter_id 
            ON class_exercises(chapter_id)
        """)
        
        # Indexes for practice_progress table
        print("  - Adding index on practice_progress(class_id)...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_practice_progress_class_id 
            ON practice_progress(class_id)
        """)
        
        print("  - Adding index on practice_progress(class_exercise_id)...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_practice_progress_class_exercise_id 
            ON practice_progress(class_exercise_id)
        """)
        
        print("  - Adding index on practice_progress(user_id)...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_practice_progress_user_id 
            ON practice_progress(user_id)
        """)
        
        # Composite index for common query pattern
        print("  - Adding composite index on practice_progress(user_id, class_exercise_id)...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_practice_progress_user_exercise 
            ON practice_progress(user_id, class_exercise_id)
        """)
        
        # Indexes for class_enrollments table
        print("  - Adding index on class_enrollments(class_id)...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_class_enrollments_class_id 
            ON class_enrollments(class_id)
        """)
        
        print("  - Adding index on class_enrollments(student_id)...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_class_enrollments_student_id 
            ON class_enrollments(student_id)
        """)
        
        # Composite index for enrollment lookups
        print("  - Adding composite index on class_enrollments(class_id, student_id)...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_class_enrollments_class_student 
            ON class_enrollments(class_id, student_id)
        """)
        
        # Indexes for class_chapters table
        print("  - Adding index on class_chapters(class_id)...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_class_chapters_class_id 
            ON class_chapters(class_id)
        """)
        
        # Indexes for conversations table
        print("  - Adding index on conversations(user_id)...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_user_id 
            ON conversations(user_id)
        """)
        
        print("  - Adding index on conversations(user_id, archived)...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_user_archived 
            ON conversations(user_id, archived)
        """)
        
        # Indexes for conversation_messages table
        print("  - Adding index on conversation_messages(conversation_id)...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversation_messages_conversation_id 
            ON conversation_messages(conversation_id)
        """)
        
        connection.commit()
        print("\n✅ All indexes created successfully!")
        
        # Show index information
        print("\nVerifying indexes...")
        cursor.execute("""
            SELECT 
                schemaname,
                tablename,
                indexname
            FROM pg_indexes
            WHERE schemaname = 'public'
            AND indexname LIKE 'idx_%'
            ORDER BY tablename, indexname
        """)
        
        indexes = cursor.fetchall()
        print(f"\nTotal custom indexes: {len(indexes)}")
        for idx in indexes:
            print(f"  - {idx[1]}.{idx[2]}")
        
        cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"❌ Error adding indexes: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    add_indexes()
