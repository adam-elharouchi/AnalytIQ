#!/usr/bin/env python3
"""Test database connection to diagnose timeout issues"""

import psycopg2
import time
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

print("Testing database connection...")
print(f"Connection string: {DATABASE_URL[:50]}...")

# Test 1: Direct connection with timeout
print("\n=== Test 1: Direct connection (10s timeout) ===")
try:
    start = time.time()
    conn = psycopg2.connect(DATABASE_URL, connect_timeout=10, sslmode="require")
    elapsed = time.time() - start
    print(f"✅ Connection successful! ({elapsed:.2f}s)")

    # Test query
    cursor = conn.cursor()
    cursor.execute("SELECT 1 as test")
    result = cursor.fetchone()
    print(f"✅ Query successful! Result: {result}")

    cursor.close()
    conn.close()
    print("✅ Connection closed successfully")

except psycopg2.OperationalError as e:
    elapsed = time.time() - start
    print(f"❌ Connection failed after {elapsed:.2f}s")
    print(f"Error: {e}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")

# Test 2: Try with different connection modes
print("\n=== Test 2: Testing different pooler modes ===")

# Supabase has two pooler modes:
# 1. Transaction mode (port 6543) - for serverless/short connections
# 2. Session mode (port 5432) - for long-lived connections

pooler_modes = [
    ("Session mode (port 5432)", DATABASE_URL),
    ("Transaction mode (port 6543)", DATABASE_URL.replace(":5432", ":6543")),
]

for mode_name, url in pooler_modes:
    print(f"\nTrying {mode_name}...")
    try:
        start = time.time()
        conn = psycopg2.connect(url, connect_timeout=10, sslmode="require")
        elapsed = time.time() - start
        print(f"  ✅ Connected in {elapsed:.2f}s")
        conn.close()
    except Exception as e:
        elapsed = time.time() - start
        print(f"  ❌ Failed after {elapsed:.2f}s: {str(e)[:100]}")

print("\n=== Test 3: Direct connection (bypassing pooler) ===")
# Try direct connection to database
direct_url = DATABASE_URL.replace(".pooler.supabase.com", ".supabase.co")
print(f"Trying direct connection: {direct_url[:50]}...")
try:
    start = time.time()
    conn = psycopg2.connect(direct_url, connect_timeout=10, sslmode="require")
    elapsed = time.time() - start
    print(f"✅ Direct connection successful! ({elapsed:.2f}s)")
    conn.close()
except Exception as e:
    elapsed = time.time() - start
    print(f"❌ Direct connection failed after {elapsed:.2f}s: {str(e)[:100]}")

print("\n=== Test Complete ===")
