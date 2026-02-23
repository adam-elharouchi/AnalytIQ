import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def run_migration():
    if not DATABASE_URL:
        print("Error: DATABASE_URL is not set.")
        return

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # 1. Run the SQL schema changes
        migration_file = os.path.join(os.path.dirname(__file__), "..", "migrations", "002_superadmin_tenants.sql")
        with open(migration_file, "r") as f:
            sql = f.read()
            print("Executing DDL from 002_superadmin_tenants.sql...")
            cur.execute(sql)
        
        print("Creating tenant records for existing LTI issuers...")
        # Insert from configurations
        cur.execute("""
            INSERT INTO tenants (name, lti_issuer)
            SELECT DISTINCT platform_name, issuer
            FROM lti_configurations
            WHERE issuer IS NOT NULL
            ON CONFLICT (lti_issuer) DO NOTHING;
        """)
        # Insert from users (if any exist not in configs)
        cur.execute("""
            INSERT INTO tenants (name, lti_issuer)
            SELECT DISTINCT 'Unknown User Tenant', lti_issuer
            FROM users
            WHERE lti_issuer IS NOT NULL
            ON CONFLICT (lti_issuer) DO NOTHING;
        """)
        # Insert from classes (if any exist not in configs)
        cur.execute("""
            INSERT INTO tenants (name, lti_issuer)
            SELECT DISTINCT 'Unknown Class Tenant', lti_issuer
            FROM classes
            WHERE lti_issuer IS NOT NULL
            ON CONFLICT (lti_issuer) DO NOTHING;
        """)

        # 3. Create Default Local Tenant for non-LTI entities
        print("Creating default local tenant...")
        cur.execute("""
            INSERT INTO tenants (name, lti_issuer)
            VALUES ('Default Local Tenant', 'local')
            ON CONFLICT (lti_issuer) DO NOTHING;
        """)

        # Fetch Default Tenant ID
        cur.execute("SELECT tenant_id FROM tenants WHERE lti_issuer = 'local';")
        default_tenant_id = cur.fetchone()[0]

        # 4. Update foreign keys mappings
        print("Linking lti_configurations, users, and classes to tenants...")
        
        # Update configs
        cur.execute("""
            UPDATE lti_configurations c
            SET tenant_id = t.tenant_id
            FROM tenants t
            WHERE c.issuer = t.lti_issuer;
        """)

        # Update users
        cur.execute("""
            UPDATE users u
            SET tenant_id = t.tenant_id
            FROM tenants t
            WHERE u.lti_issuer = t.lti_issuer AND u.tenant_id IS NULL;
        """)
        # Assign local users to default tenant
        cur.execute("""
            UPDATE users
            SET tenant_id = %s
            WHERE lti_issuer IS NULL AND tenant_id IS NULL;
        """, (default_tenant_id,))

        # Update classes
        cur.execute("""
            UPDATE classes c
            SET tenant_id = t.tenant_id
            FROM tenants t
            WHERE c.lti_issuer = t.lti_issuer AND c.tenant_id IS NULL;
        """)
        # Assign local classes to default tenant
        cur.execute("""
            UPDATE classes
            SET tenant_id = %s
            WHERE lti_issuer IS NULL AND tenant_id IS NULL;
        """, (default_tenant_id,))

        # 5. Make the first user a Super Admin to avoid lockout (if needed, here we just pick the oldest user for testing or leave it)
        # We can create a user or just let the developer set it later. By default, no one is super admin. Let's make adamelharouchi@gmail.com super admin if he exists.
        cur.execute("""
            UPDATE users 
            SET is_super_admin = true
            WHERE email = 'adamelharouchi@gmail.com';
        """)

        conn.commit()
        print("Migration and tenant backfill completed successfully!")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"Error during migration: {e}")
        if 'conn' in locals() and conn:
            conn.rollback()
            conn.close()

if __name__ == "__main__":
    run_migration()
