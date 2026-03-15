#!/usr/bin/env python3
"""
PDF Migration Script
Migrates PDF files from PostgreSQL database to Supabase Storage

Usage:
    python scripts/migrate_pdfs.py --dry-run  # Test without making changes
    python scripts/migrate_pdfs.py            # Run actual migration
"""
import os
import sys
import argparse
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
import psycopg2
from core.storage import migrate_pdf_from_db, supabase

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def get_chapters_with_pdfs(conn):
    """Get all chapters that have PDF data in database"""
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT chapter_id, pdf_filename, 
               octet_length(pdf_data) as pdf_size,
               pdf_url
        FROM class_chapters
        WHERE pdf_data IS NOT NULL
        ORDER BY chapter_id
    """
    )

    chapters = cursor.fetchall()
    cursor.close()

    return chapters


def migrate_chapter_pdf(conn, chapter_id, dry_run=False):
    """Migrate a single chapter's PDF to Supabase Storage"""
    cursor = conn.cursor()

    # Get PDF data
    cursor.execute(
        """
        SELECT pdf_data, pdf_filename
        FROM class_chapters
        WHERE chapter_id = %s
    """,
        (chapter_id,),
    )

    result = cursor.fetchone()
    if not result:
        return {"success": False, "error": "Chapter not found"}

    pdf_data, pdf_filename = result

    if not pdf_data:
        return {"success": False, "error": "No PDF data"}

    print(f"  Migrating: {pdf_filename} ({len(pdf_data)} bytes)")

    if dry_run:
        print(f"  [DRY RUN] Would upload to Supabase")
        cursor.close()
        return {"success": True, "dry_run": True, "filename": pdf_filename, "size": len(pdf_data)}

    # Upload to Supabase
    migration_result = migrate_pdf_from_db(chapter_id, pdf_data, pdf_filename)

    if not migration_result["success"]:
        cursor.close()
        return migration_result

    # Update database with new URL
    cursor.execute(
        """
        UPDATE class_chapters
        SET pdf_url = %s,
            updated_at = NOW()
        WHERE chapter_id = %s
    """,
        (migration_result["url"], chapter_id),
    )

    conn.commit()
    cursor.close()

    return migration_result


def clear_pdf_data(conn, chapter_id, dry_run=False):
    """Clear PDF data from database after successful migration"""
    if dry_run:
        print(f"  [DRY RUN] Would clear pdf_data for chapter {chapter_id}")
        return True

    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE class_chapters
        SET pdf_data = NULL
        WHERE chapter_id = %s
    """,
        (chapter_id,),
    )

    conn.commit()
    cursor.close()

    return True


def main():
    parser = argparse.ArgumentParser(description="Migrate PDFs from database to Supabase Storage")
    parser.add_argument(
        "--dry-run", action="store_true", help="Test migration without making changes"
    )
    parser.add_argument(
        "--clear-data", action="store_true", help="Clear pdf_data from database after migration"
    )
    parser.add_argument("--limit", type=int, help="Limit number of PDFs to migrate")

    args = parser.parse_args()

    print("=" * 70)
    print("PDF MIGRATION TO SUPABASE STORAGE")
    print("=" * 70)

    if args.dry_run:
        print("🧪 DRY RUN MODE - No changes will be made")

    # Check Supabase connection
    if not supabase:
        print("❌ Supabase client not initialized. Check SUPABASE_URL and SUPABASE_KEY")
        return 1

    print("✅ Supabase client initialized")

    # Connect to database
    try:
        conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        print("✅ Database connected")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return 1

    # Get chapters with PDFs
    chapters = get_chapters_with_pdfs(conn)
    total_chapters = len(chapters)

    print(f"\n📊 Found {total_chapters} chapters with PDF data")

    if total_chapters == 0:
        print("✅ No PDFs to migrate")
        conn.close()
        return 0

    # Calculate total size
    total_size = sum(chapter[2] for chapter in chapters)
    print(f"📦 Total size: {total_size / 1024 / 1024:.2f} MB")

    # Apply limit if specified
    if args.limit:
        chapters = chapters[: args.limit]
        print(f"⚠️  Limiting migration to {args.limit} chapters")

    # Migrate each chapter
    print(f"\n🚀 Starting migration...")
    print("-" * 70)

    success_count = 0
    fail_count = 0
    migrated_size = 0

    for i, (chapter_id, pdf_filename, pdf_size, current_url) in enumerate(chapters, 1):
        print(f"\n[{i}/{len(chapters)}] Chapter ID: {chapter_id}")

        # Skip if already has Supabase URL
        if current_url and "supabase" in current_url:
            print(f"  ⏭️  Already migrated (URL: {current_url[:50]}...)")

            # Check if we need to clear data for already migrated files
            if args.clear_data and pdf_size is not None and pdf_size > 0:
                if not args.dry_run:
                    clear_pdf_data(conn, chapter_id, dry_run=args.dry_run)
                    print(f"  🗑️  Cleared pdf_data from database (cleanup)")
                    migrated_size += pdf_size  # Count this towards space saved
                else:
                    print(f"  [DRY RUN] Would clear pdf_data (cleanup)")

            success_count += 1
            continue

        # Migrate
        result = migrate_chapter_pdf(conn, chapter_id, dry_run=args.dry_run)

        if result["success"]:
            print(f"  ✅ Success: {result.get('url', 'N/A')[:60]}...")
            success_count += 1
            migrated_size += pdf_size

            # Clear PDF data if requested
            if args.clear_data and not args.dry_run:
                clear_pdf_data(conn, chapter_id, dry_run=args.dry_run)
                print(f"  🗑️  Cleared pdf_data from database")
        else:
            print(f"  ❌ Failed: {result.get('error')}")
            fail_count += 1

    # Summary
    print("\n" + "=" * 70)
    print("MIGRATION SUMMARY")
    print("=" * 70)
    print(f"✅ Successful: {success_count}/{len(chapters)}")
    print(f"❌ Failed: {fail_count}/{len(chapters)}")
    print(f"📦 Migrated size: {migrated_size / 1024 / 1024:.2f} MB")

    if args.dry_run:
        print("\n🧪 This was a DRY RUN - no actual changes were made")
    else:
        print(f"\n✅ Migration complete!")

        if args.clear_data:
            print(f"🗑️  PDF data cleared from database")
            print(f"💾 Estimated database size reduction: {migrated_size / 1024 / 1024:.2f} MB")
        else:
            print("\n⚠️  PDF data still in database (use --clear-data to remove)")

    conn.close()
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
