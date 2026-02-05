#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "pdfs")


def setup_storage():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Supabase credentials not found in .env")
        return

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    print(f"Checking bucket: {SUPABASE_BUCKET}...")

    try:
        # Check if bucket exists
        buckets = supabase.storage.list_buckets()
        bucket_exists = any(b.name == SUPABASE_BUCKET for b in buckets)

        if bucket_exists:
            print(f"✅ Bucket '{SUPABASE_BUCKET}' already exists.")
        else:
            print(f"Creating bucket '{SUPABASE_BUCKET}'...")
            # Attempt to create the bucket
            # Note: This may fail if using an anon key without sufficient permissions
            supabase.storage.create_bucket(SUPABASE_BUCKET, options={"public": True})
            print(f"✅ Bucket '{SUPABASE_BUCKET}' created successfully.")

    except Exception as e:
        print(f"❌ Error setting up storage: {e}")
        print(
            "\nTip: If you get a 403 error, you may need to create the bucket manually in the Supabase Dashboard"
        )
        print("or use the 'service_role' key instead of the 'anon' key.")


if __name__ == "__main__":
    setup_storage()
