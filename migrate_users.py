"""
Migration script to move existing localStorage user data to Supabase database
Supports both JSON and CSV file formats
"""
import psycopg2
from dotenv import load_dotenv
import os
import json
import sys
import csv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def hash_password(password):
    """Simple hash function (same as frontend/backend for compatibility)"""
    hash_val = 0
    for char in password:
        hash_val = ((hash_val << 5) - hash_val) + ord(char)
        hash_val = hash_val & hash_val  # Convert to 32bit integer
    return str(hash_val)

def migrate_from_csv(filename):
    """Migrate users from a CSV file"""
    try:
        users = []
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                user = {
                    'id': row.get('id', '').strip(),
                    'name': row.get('name', '').strip(),
                    'email': row.get('email', '').strip(),
                    'password': row.get('password_hash', '').strip(),
                    'profile': {
                        'fullName': row.get('fullName', '').strip(),
                        'bio': row.get('bio', '').strip(),
                        'profilePicture': row.get('profilePicture', '').strip()
                    },
                    'settings': {
                        'emailNotifications': row.get('emailNotifications', 'false').strip().lower() == 'true',
                        'darkMode': row.get('darkMode', 'false').strip().lower() == 'true'
                    }
                }
                users.append(user)
        
        if not users:
            print("No users found in CSV file.")
            return
        
        return migrate_users_list(users)
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
        return
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return

def migrate_from_file(filename):
    """Migrate users from a JSON file"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle both simple array format and full export format
        if isinstance(data, list):
            users = data
            export_data = {}
        elif isinstance(data, dict) and 'users' in data:
            users = data['users']
            export_data = data
        else:
            print("Error: Invalid JSON format. Expected array or object with 'users' key.")
            return
        
        return migrate_users_list(users, export_data if isinstance(data, dict) else {})
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
        return
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in file: {e}")
        return

def migrate_users_list(users, export_data=None):
    """Migrate a list of users to the database"""
    if not users:
        print("No users to migrate.")
        return
    
    print(f"\nFound {len(users)} user(s) to migrate.\n")
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        migrated = 0
        skipped = 0
        profiles_updated = 0
        settings_updated = 0
        
        # Get profiles and settings from export_data if available
        profiles = export_data.get('profiles', {}) if export_data else {}
        settings = export_data.get('settings', {}) if export_data else {}
        
        for user in users:
            try:
                email = user.get('email')
                name = user.get('name')
                password_hash = user.get('password')  # Already hashed
                user_id = user.get('id')
                
                if not email or not name or not password_hash:
                    print(f"Skipping user {email}: Missing required fields (email, name, or password)")
                    skipped += 1
                    continue
                
                # Generate user_id if not present
                if not user_id:
                    user_id = str(int(user.get('createdAt', 0)) if user.get('createdAt') else 0)
                    if user_id == '0':
                        import time
                        user_id = str(int(time.time() * 1000))
                
                # Check if user already exists
                cursor.execute("SELECT id, user_id FROM users WHERE email = %s", (email,))
                existing = cursor.fetchone()
                if existing:
                    print(f"Skipping user {email}: Already exists in database (user_id: {existing[1]})")
                    skipped += 1
                    continue
                
                # Insert user
                cursor.execute(
                    "INSERT INTO users (user_id, name, email, password_hash) VALUES (%s, %s, %s, %s) RETURNING user_id",
                    (user_id, name, email, password_hash)
                )
                inserted_user_id = cursor.fetchone()[0]
                
                # Get profile data (from CSV row or export_data)
                profile_data = user.get('profile', {}) or profiles.get(user_id, {})
                if profile_data:
                    full_name = profile_data.get('fullName') or name
                    bio = profile_data.get('bio', '')
                    profile_picture = profile_data.get('profilePicture', '')
                    
                    cursor.execute("""
                        INSERT INTO user_profiles (user_id, full_name, bio, profile_picture)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (user_id) DO UPDATE SET
                            full_name = EXCLUDED.full_name,
                            bio = EXCLUDED.bio,
                            profile_picture = EXCLUDED.profile_picture,
                            updated_at = CURRENT_TIMESTAMP
                    """, (inserted_user_id, full_name, bio, profile_picture))
                    profiles_updated += 1
                else:
                    # Create default profile
                    cursor.execute(
                        "INSERT INTO user_profiles (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
                        (inserted_user_id,)
                    )
                
                # Get settings data (from CSV row or export_data)
                settings_data = user.get('settings', {}) or settings.get(user_id, {})
                if settings_data:
                    email_notifications = settings_data.get('emailNotifications', False)
                    dark_mode = settings_data.get('darkMode', False)
                    
                    cursor.execute("""
                        INSERT INTO user_settings (user_id, email_notifications, dark_mode)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (user_id) DO UPDATE SET
                            email_notifications = EXCLUDED.email_notifications,
                            dark_mode = EXCLUDED.dark_mode,
                            updated_at = CURRENT_TIMESTAMP
                    """, (inserted_user_id, email_notifications, dark_mode))
                    settings_updated += 1
                else:
                    # Create default settings
                    cursor.execute(
                        "INSERT INTO user_settings (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING",
                        (inserted_user_id,)
                    )
                
                print(f"✓ Migrated user: {email} (ID: {inserted_user_id})")
                migrated += 1
                
            except Exception as e:
                print(f"✗ Error migrating user {user.get('email', 'unknown')}: {e}")
                skipped += 1
                conn.rollback()
                continue
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"\n{'='*50}")
        print(f"Migration Summary:")
        print(f"{'='*50}")
        print(f"✓ Migrated: {migrated} user(s)")
        if profiles_updated > 0:
            print(f"✓ Updated profiles: {profiles_updated}")
        if settings_updated > 0:
            print(f"✓ Updated settings: {settings_updated}")
        print(f"✗ Skipped: {skipped} user(s)")
        print(f"{'='*50}\n")
        
    except Exception as e:
        print(f"Database error: {e}")
        if conn:
            conn.rollback()
            conn.close()

def migrate_from_input():
    """Migrate users from interactive input"""
    print("This script helps migrate users from localStorage format to the database.")
    print("\nTo export your users data:")
    print("1. Open export_users.html in your browser")
    print("2. Click 'Export Users to CSV' to download users_export.csv")
    print("3. Run this script with: python3 migrate_users.py users_export.csv\n")
    
    users_json = input("Or paste the users JSON array here (or press Enter to exit): ").strip()
    
    if not users_json:
        print("No users data provided. Exiting.")
        return
    
    try:
        users = json.loads(users_json)
        if not isinstance(users, list):
            # Try to extract users from object
            if isinstance(users, dict) and 'users' in users:
                migrate_users_list(users['users'], users)
                return
            print("Error: Expected a JSON array or object with 'users' key")
            return
        
        migrate_users_list(users)
        
    except json.JSONDecodeError:
        print("Error: Invalid JSON format")
    except Exception as e:
        print(f"Error: {e}")

def main():
    if len(sys.argv) > 1:
        # Migrate from file
        filename = sys.argv[1]
        if filename.lower().endswith('.csv'):
            migrate_from_csv(filename)
        else:
            migrate_from_file(filename)
    else:
        # Interactive mode
        migrate_from_input()

if __name__ == "__main__":
    main()
