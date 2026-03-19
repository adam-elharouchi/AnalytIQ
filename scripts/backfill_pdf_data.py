#!/usr/bin/env python3
"""
scripts/backfill_pdf_data.py — Download PDFs from Supabase Storage into pdf_data column.

Finds chapters where pdf_data IS NULL but pdf_filename IS NOT NULL (uploaded via
presigned URL to Supabase), downloads each file, and stores the bytes back in the DB.

After this runs, every chapter has pdf_data, so regenerate_exercises.py works on all.

Usage:
  # Dry-run (show what would be downloaded, no DB changes):
  python3 scripts/backfill_pdf_data.py

  # Actually backfill:
  python3 scripts/backfill_pdf_data.py --execute
"""

import argparse
import logging
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(REPO_ROOT / ".env")

import psycopg2  # noqa: E402
import requests  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("backfill_pdf_data")


def get_conn():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(url)


def fetch_supabase_only_chapters(conn):
    """Chapters that have a Supabase filename but no local binary."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT chapter_id, class_id, title, pdf_filename
        FROM class_chapters
        WHERE pdf_data IS NULL AND pdf_filename IS NOT NULL
        ORDER BY class_id, chapter_number
        """
    )
    rows = cur.fetchall()
    cur.close()
    return [
        {"chapter_id": r[0], "class_id": r[1], "title": r[2], "pdf_filename": r[3]} for r in rows
    ]


def download_from_supabase(pdf_filename):
    """Download file bytes from Supabase Storage. Returns bytes or raises."""
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    supabase_key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
    bucket = os.getenv("SUPABASE_BUCKET", "analytiq-pdfs")

    if not supabase_url or not supabase_key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_KEY not set")

    # Authenticated download
    url = f"{supabase_url}/storage/v1/object/{bucket}/{pdf_filename}"
    resp = requests.get(
        url,
        headers={"Authorization": f"Bearer {supabase_key}", "apikey": supabase_key},
        timeout=30,
    )
    if resp.ok:
        return resp.content

    # Fallback: public URL
    public_url = f"{supabase_url}/storage/v1/object/public/{bucket}/{pdf_filename}"
    resp = requests.get(public_url, timeout=30)
    if resp.ok:
        return resp.content

    raise RuntimeError(f"Download failed ({resp.status_code}): {resp.text[:200]}")


def store_pdf_data(conn, chapter_id, pdf_bytes):
    cur = conn.cursor()
    cur.execute(
        "UPDATE class_chapters SET pdf_data = %s WHERE chapter_id = %s",
        (psycopg2.Binary(pdf_bytes), chapter_id),
    )
    cur.close()
    conn.commit()


def main():
    parser = argparse.ArgumentParser(description="Backfill pdf_data from Supabase into DB")
    parser.add_argument("--execute", action="store_true", help="Write to DB (default is dry-run)")
    args = parser.parse_args()

    if not args.execute:
        logger.info("DRY-RUN mode — pass --execute to make DB changes")

    conn = get_conn()
    chapters = fetch_supabase_only_chapters(conn)

    if not chapters:
        logger.info("All chapters already have pdf_data — nothing to do.")
        conn.close()
        return

    logger.info("Found %d chapter(s) missing pdf_data", len(chapters))

    ok = 0
    failed = 0
    for i, ch in enumerate(chapters, 1):
        logger.info("[%d/%d] %r  (%s)", i, len(chapters), ch["title"], ch["chapter_id"])
        logger.info("  filename: %s", ch["pdf_filename"])

        if not args.execute:
            logger.info("  (dry-run) would download and store pdf_data")
            ok += 1
            continue

        try:
            pdf_bytes = download_from_supabase(ch["pdf_filename"])
            logger.info("  downloaded %d bytes", len(pdf_bytes))
            store_pdf_data(conn, ch["chapter_id"], pdf_bytes)
            logger.info("  ✓ stored in DB")
            ok += 1
        except Exception as e:
            logger.error("  FAILED: %s", e)
            conn.rollback()
            failed += 1

    conn.close()
    print()
    if args.execute:
        print(f"Done. {ok} chapter(s) backfilled, {failed} failed.")
        if ok:
            print("Now run:  python3 scripts/regenerate_exercises.py --execute")
    else:
        print(f"Dry-run complete. {ok} chapter(s) would be backfilled.")
        print("Re-run with --execute to apply.")


if __name__ == "__main__":
    main()
