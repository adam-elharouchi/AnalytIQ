#!/usr/bin/env python3
"""
scripts/regenerate_exercises.py — Regenerate all exercises from stored PDF data.

For every chapter that has stored PDF/file bytes, this script:
  1. Extracts text from the stored binary content.
  2. Deletes the chapter's existing exercises (and their flywheel events).
  3. Calls generate_exercises_from_pdf_content() with the improved v1.2 prompt.
  4. Inserts the new exercises (+ flywheel generation events).

Usage:
  # Dry-run (preview what would be regenerated, no DB changes):
  python3 scripts/regenerate_exercises.py

  # Actually regenerate:
  python3 scripts/regenerate_exercises.py --execute

  # Limit to specific chapters:
  python3 scripts/regenerate_exercises.py --execute --chapter ch-abc ch-def

  # Limit to a specific class:
  python3 scripts/regenerate_exercises.py --execute --class-id cls-xyz
"""

import argparse
import logging
import os
import sys
import json
from datetime import datetime
from pathlib import Path

# --- Make sure repo root is on the path so imports work --------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(REPO_ROOT / ".env")

import psycopg2  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("regenerate_exercises")


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def get_conn():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set — add it to .env or export it")
    return psycopg2.connect(url)


def fetch_chapters(conn, class_id_filter=None, chapter_id_filter=None):
    """
    Return list of dicts with chapter metadata + binary PDF/file data.
    Only chapters that have pdf_data stored are returned.
    """
    where_clauses = ["cc.pdf_data IS NOT NULL"]
    params = []

    if class_id_filter:
        where_clauses.append("cc.class_id = %s")
        params.append(class_id_filter)

    if chapter_id_filter:
        placeholders = ", ".join(["%s"] * len(chapter_id_filter))
        where_clauses.append(f"cc.chapter_id IN ({placeholders})")
        params.extend(chapter_id_filter)

    where_sql = " AND ".join(where_clauses)

    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT cc.chapter_id, cc.class_id, cc.title, cc.pdf_filename,
               cc.pdf_data, c.professor_id
        FROM class_chapters cc
        JOIN classes c ON cc.class_id = c.class_id
        WHERE {where_sql}
        ORDER BY cc.class_id, cc.chapter_number
        """,
        params,
    )
    rows = cur.fetchall()
    cur.close()
    return [
        {
            "chapter_id": r[0],
            "class_id": r[1],
            "title": r[2],
            "pdf_filename": r[3],
            "pdf_data": bytes(r[4]),
            "professor_id": r[5],
        }
        for r in rows
    ]


def delete_chapter_exercises(conn, chapter_id):
    """Delete all exercises (and their flywheel events) for a chapter."""
    cur = conn.cursor()
    # Delete flywheel generation events first (FK constraint)
    cur.execute(
        """
        DELETE FROM exercise_generation_events
        WHERE exercise_id IN (
            SELECT exercise_id FROM class_exercises WHERE chapter_id = %s
        )
        """,
        (chapter_id,),
    )
    deleted_events = cur.rowcount
    cur.execute("DELETE FROM class_exercises WHERE chapter_id = %s", (chapter_id,))
    deleted_exercises = cur.rowcount
    cur.close()
    return deleted_exercises, deleted_events


def insert_exercise(conn, exercise_id, chapter_id, class_id, exercise, idx):
    """Insert a single generated exercise row."""
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO class_exercises
            (exercise_id, chapter_id, class_id, title, description, difficulty,
             solution_code, exercise_number, function_name, test_cases, language)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            exercise_id,
            chapter_id,
            class_id,
            exercise["title"],
            exercise["description"],
            exercise["difficulty"],
            exercise["solution_code"],
            idx,
            exercise.get("function_name", "solution"),
            json.dumps(exercise.get("test_cases") or []),
            exercise.get("language", "Python"),
        ),
    )
    cur.close()


def link_exercise_to_generation_event(conn, exercise_id, gen_event_id):
    cur = conn.cursor()
    cur.execute(
        "UPDATE class_exercises SET generation_event_id = %s WHERE exercise_id = %s",
        (gen_event_id, exercise_id),
    )
    cur.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def regenerate_chapter(conn, chapter, execute=False):
    """
    Regenerate exercises for one chapter.
    Returns (new_count, skipped_reason) where skipped_reason is None on success.
    """
    from services.content_extractor import extract_text
    from services.exercise_generator import generate_exercises_from_pdf_content
    from repositories.flywheel_repository import insert_generation_event

    chapter_id = chapter["chapter_id"]
    class_id = chapter["class_id"]
    title = chapter["title"]
    pdf_filename = chapter["pdf_filename"] or "chapter.pdf"
    pdf_data = chapter["pdf_data"]

    # 1. Extract text
    try:
        pdf_text = extract_text(pdf_data, pdf_filename)
    except Exception as e:
        return 0, f"text extraction failed: {e}"

    if not pdf_text or not pdf_text.strip():
        return 0, "extracted text is empty"

    logger.info("  chapter %-40s  text=%d chars", chapter_id, len(pdf_text))

    if not execute:
        return 0, None  # dry-run: just show what we would do

    # 2. Generate exercises
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return 0, "GEMINI_API_KEY not set"

    ext = pdf_filename.rsplit(".", 1)[-1].lower() if "." in pdf_filename else "pdf"
    try:
        exercises = generate_exercises_from_pdf_content(
            pdf_text, title, api_key, source_content_type=ext
        )
    except Exception as e:
        return 0, f"Gemini generation failed: {e}"

    if not exercises:
        return 0, "Gemini returned 0 exercises"

    # 3. Delete old exercises
    deleted, deleted_events = delete_chapter_exercises(conn, chapter_id)
    logger.info("  deleted %d old exercises (%d flywheel events)", deleted, deleted_events)

    # 4. Insert new exercises
    ts_ms = int(datetime.now().timestamp() * 1000)
    for idx, exercise in enumerate(exercises, 1):
        exercise_id = f"{chapter_id}_ex_{idx}_{ts_ms + idx}"
        insert_exercise(conn, exercise_id, chapter_id, class_id, exercise, idx)
        gen_meta = exercise.get("_gen_meta") or {}
        gen_meta.update(
            {"exercise_id": exercise_id, "class_id": class_id, "chapter_id": chapter_id}
        )
        gen_event_id = insert_generation_event(conn, gen_meta)
        if gen_event_id:
            link_exercise_to_generation_event(conn, exercise_id, gen_event_id)

    conn.commit()
    return len(exercises), None


def main():
    parser = argparse.ArgumentParser(description="Regenerate all exercises from stored PDFs")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually write to the DB (default is dry-run)",
    )
    parser.add_argument(
        "--chapter",
        nargs="+",
        metavar="CHAPTER_ID",
        help="Limit to specific chapter IDs",
    )
    parser.add_argument(
        "--class-id",
        metavar="CLASS_ID",
        help="Limit to chapters belonging to this class",
    )
    args = parser.parse_args()

    if not args.execute:
        logger.info("DRY-RUN mode — pass --execute to make DB changes")

    conn = get_conn()
    chapters = fetch_chapters(
        conn,
        class_id_filter=args.class_id,
        chapter_id_filter=args.chapter,
    )

    if not chapters:
        logger.warning("No chapters with stored PDF data found — nothing to do.")
        conn.close()
        return

    logger.info("Found %d chapter(s) to process", len(chapters))

    total_new = 0
    total_failed = 0

    for i, chapter in enumerate(chapters, 1):
        label = f"[{i}/{len(chapters)}] {chapter['title']!r} ({chapter['chapter_id']})"
        logger.info(label)

        try:
            new_count, skip_reason = regenerate_chapter(conn, chapter, execute=args.execute)
        except Exception as e:
            logger.error("  UNEXPECTED ERROR: %s", e, exc_info=True)
            conn.rollback()
            total_failed += 1
            continue

        if skip_reason:
            logger.warning("  SKIPPED — %s", skip_reason)
            total_failed += 1
        elif args.execute:
            logger.info("  ✓ inserted %d new exercises", new_count)
            total_new += new_count
        else:
            logger.info("  (dry-run) would regenerate exercises for this chapter")

    conn.close()

    print()
    if args.execute:
        print(
            f"Done. {total_new} exercises created across {len(chapters) - total_failed} chapters."
        )
        if total_failed:
            print(f"  {total_failed} chapter(s) had errors — check logs above.")
    else:
        print(f"Dry-run complete. {len(chapters)} chapter(s) would be regenerated.")
        print("Re-run with --execute to apply changes.")


if __name__ == "__main__":
    main()
