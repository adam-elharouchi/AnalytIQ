import psycopg2
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def create_tables():
    """Create database tables for user management"""
    try:
        connection = psycopg2.connect(DATABASE_URL)
        cursor = connection.cursor()

        # Create users table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255) UNIQUE NOT NULL,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        )

        # Create user_profiles table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_profiles (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255) UNIQUE NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                full_name VARCHAR(255),
                bio TEXT,
                profile_picture TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        )

        # Create user_settings table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_settings (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255) UNIQUE NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                email_notifications BOOLEAN DEFAULT false,
                dark_mode BOOLEAN DEFAULT false,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        )

        # Create conversations table (code assistant chats)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id SERIAL PRIMARY KEY,
                conversation_id VARCHAR(255) UNIQUE NOT NULL,
                user_id VARCHAR(255) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                title VARCHAR(500),
                archived BOOLEAN DEFAULT false,
                deleted BOOLEAN DEFAULT false,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        )

        # Create conversation_messages table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_messages (
                id SERIAL PRIMARY KEY,
                conversation_id VARCHAR(255) NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
                role VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,
                message_order INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        )

        # Create ai_agent_digest table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_agent_digest (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255) UNIQUE NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                goal TEXT,
                constraints TEXT,
                decisions TEXT,
                current_state TEXT,
                open_questions TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        )

        # Create ai_agent_memory table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_agent_memory (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                memory_item TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        )

        # Create user_preferences table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_preferences (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255) UNIQUE NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                current_language VARCHAR(50) DEFAULT 'python',
                gemini_model VARCHAR(100) DEFAULT 'gemini-2.5-flash',
                ai_provider VARCHAR(50) DEFAULT 'gemini',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        )

        # Create practice_progress table (track exercise scores and progress)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS practice_progress (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                exercise_id VARCHAR(255) NOT NULL,
                exercise_title VARCHAR(500),
                class_id VARCHAR(255),
                class_exercise_id VARCHAR(255),
                best_score INTEGER DEFAULT 0,
                best_accuracy DECIMAL(5,2) DEFAULT 0,
                best_time INTEGER,
                total_attempts INTEGER DEFAULT 0,
                last_attempt_score INTEGER,
                last_attempt_accuracy DECIMAL(5,2),
                last_attempt_time INTEGER,
                completed BOOLEAN DEFAULT false,
                last_completed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, exercise_id)
            );
        """
        )

        # Create exercise_attempts table (track all attempts for detailed history)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS exercise_attempts (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                exercise_id VARCHAR(255) NOT NULL,
                score INTEGER NOT NULL,
                accuracy DECIMAL(5,2) NOT NULL,
                time_spent INTEGER NOT NULL,
                attempt_number INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        )

        # Create indexes for better performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversations_conversation_id ON conversations(conversation_id);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON conversation_messages(conversation_id);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_ai_memory_user_id ON ai_agent_memory(user_id);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_practice_user_id ON practice_progress(user_id);"
        )

        connection.commit()
        print("Tables created successfully!")

        cursor.close()
        connection.close()

    except Exception as e:
        print(f"Error creating tables: {e}")
        if connection:
            connection.close()


if __name__ == "__main__":
    create_tables()
