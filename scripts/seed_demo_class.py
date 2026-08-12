#!/usr/bin/env python3
"""
scripts/seed_demo_class.py — Seed (or reset) the AnalytIQ seeded demo class.

Creates a self-contained, always-works demo fixture so Adam (or anyone else)
can walk a buyer/professor through the full upload -> exercises -> grade ->
analytics loop without depending on a live Gemini call, a real PDF, or any
production data.

Creates:
  - 1 demo tenant            ("AnalytIQ Demo University")
  - 1 demo professor account
  - 1 demo class              (code: see CLASS_ID below)
  - 1 chapter with short, real source content (a .txt file, extracted the
    same way a PDF would be — see "Why the chapter content is short" below)
  - 5 pre-generated exercises (canned, NOT a live Gemini call — see
    "Why exercises are canned, not generated live" below)
  - 2 demo student accounts, enrolled in the class
  - Practice-progress + attempt history for both students, so the
    professor-facing analytics page has real data to show on first load

IDEMPOTENT: every run first deletes any existing rows for the fixed demo IDs
below (cascades handle children), then recreates everything from scratch.
Re-running always resets the demo class to this exact known-good state —
it never duplicates or drifts.

--------------------------------------------------------------------------
Why the chapter content is short (READ BEFORE "helpfully" lengthening it)
--------------------------------------------------------------------------
services/exercise_generator.py has a hard-coded 10,000-character truncation
limit (_TRUNCATION_LIMIT, currently around line 26/147) that silently cuts
off anything longer with NO warning shown to the user. That is a known bug
and its fix is Adam's Aug 12 review item — it is NOT approved and this
script does not implement it. The chapter content below is ~2.3k characters
specifically to stay far away from that limit so the demo can never trip it.
Do not lengthen this content "to make the demo more realistic" until the
truncation fix has shipped and been verified.

--------------------------------------------------------------------------
Why exercises are canned, not generated live
--------------------------------------------------------------------------
Calling Gemini during seeding would (a) require a GEMINI_API_KEY, (b) cost
money on every reset, and (c) introduce network flakiness into a script
whose entire purpose is "always works, zero glitches." So the 5 exercises
below are hand-written in exactly the schema
services.exercise_generator.generate_exercises_from_pdf_content() produces
(title, description, difficulty, function_name, solution_code, test_cases,
language), and are inserted the same way blueprints/chapters.py inserts
Gemini-generated exercises (chapter_repository.insert_exercise). Grading
them uses services/code_runner.run_test_cases() — deterministic local
execution, not an AI call — so the live "type code, click Grade" demo step
also has no Gemini dependency.

--------------------------------------------------------------------------
Production guard
--------------------------------------------------------------------------
This script refuses to write to a database that looks like production:
  1. Hard refusal, no override, if FLASK_ENV=production.
  2. For any DATABASE_URL whose host isn't localhost/127.0.0.1/*.local,
     it additionally requires the environment variable
     SEED_DEMO_CONFIRM=yes to be set, so a bare `--execute` against an
     unknown remote host is never enough by accident.
  3. Default mode (no --execute) is a dry run: it prints the plan and
     touches nothing.

Usage:
  # Preview what would happen (no DB writes, no DB connection at all):
  python3 scripts/seed_demo_class.py

  # Actually seed / reset the demo class:
  python3 scripts/seed_demo_class.py --execute

  # Remove the demo fixtures without recreating them:
  python3 scripts/seed_demo_class.py --teardown
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

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
logger = logging.getLogger("seed_demo_class")


# ---------------------------------------------------------------------------
# Fixed demo IDs — deliberately human-readable so they're obviously fixtures
# and never collide with real UUIDs. Idempotency depends on these NEVER
# changing between runs.
# ---------------------------------------------------------------------------

TENANT_ID = "demo-tenant"
TENANT_NAME = "AnalytIQ Demo University"

PROFESSOR_ID = "demo-professor-001"
PROFESSOR_NAME = "Dr. Dana Reyes"
PROFESSOR_EMAIL = "demo.professor@analytiq-demo.local"

STUDENTS = [
    {
        "user_id": "demo-student-jordan",
        "name": "Jordan Kim",
        "email": "jordan.kim@analytiq-demo.local",
    },
    {
        "user_id": "demo-student-riley",
        "name": "Riley Chen",
        "email": "riley.chen@analytiq-demo.local",
    },
]

# Fixture-only password for the demo accounts above. These accounts must
# never exist in a production database (see production guard) — this is a
# known, published password for a throwaway demo/staging fixture, not a
# real credential.
DEMO_PASSWORD = "AnalytIQDemo#2026"

# This is also the professor-facing "class code" (must be alphanumeric,
# 3-20 chars, to match the same validation the real /api/classes endpoint
# applies — see blueprints/classes.py:create_class).
CLASS_ID = "DEMOCLASS01"
CLASS_NAME = "Intro to Data Analysis with Python (Demo)"
CLASS_DESCRIPTION = (
    "Seeded demo class for buyer/professor walkthroughs. Safe to reset at any "
    "time via `python3 scripts/seed_demo_class.py --execute`."
)

CHAPTER_ID = "demo-chapter-1"
CHAPTER_TITLE = "Chapter 1 — Lists, Loops, and Basic Statistics"
CHAPTER_DESCRIPTION = "Foundational Python: lists, loops, averages, counting, and simple categorisation."
CHAPTER_FILENAME = "chapter1_lists_and_stats.txt"

# ---------------------------------------------------------------------------
# Chapter source content — kept intentionally SHORT. See module docstring
# ("Why the chapter content is short") before changing this.
# Stored as .txt (not a crafted PDF binary): content_extractor.extract_text()
# supports .txt natively, so this exercises the exact same downstream code
# path (extract -> truncation-limit check -> exercise generation) a real PDF
# upload would, without the complexity/fragility of hand-crafting PDF bytes.
# ---------------------------------------------------------------------------

CHAPTER_TEXT = """Chapter 1 -- Lists, Loops, and Basic Statistics

Welcome to your first hands-on chapter in Python for data analysis. In this
chapter we cover three foundational building blocks that you will use in
almost every data science script you ever write: lists, loops, and simple
descriptive statistics.

1. Lists

A list is Python's basic ordered container. You create one with square
brackets:

    exam_scores = [72, 88, 91, 65, 79, 95, 60]

Lists can hold any number of items, and you can loop over every item with a
`for` loop:

    for score in exam_scores:
        print(score)

2. Aggregating a list

Three operations come up constantly when you first look at a new dataset:
the average (mean), the maximum value, and counting how many items satisfy
some condition.

The average is the sum of every value divided by how many values there are:

    total = sum(exam_scores)
    count = len(exam_scores)
    average = total / count

The maximum is the largest single value. Find it by keeping track of the
best value seen so far as you loop through the list:

    largest = exam_scores[0]
    for score in exam_scores:
        if score > largest:
            largest = score

Counting with a condition follows the same pattern -- start a counter at
zero, and increment it every time the condition is true:

    count = 0
    for score in exam_scores:
        if score > 70:
            count += 1

3. Even numbers

The modulo operator (`%`) returns the remainder of a division. A number is
even exactly when `number % 2 == 0`. This is one of the most common checks
you will write when cleaning or exploring a dataset.

4. Turning numbers into categories

Real datasets are rarely just numbers -- you usually need to turn a raw
number into a category a human can read. A simple way to do this is a chain
of `if` / `elif` / `else` statements, checked from the highest threshold
down to the lowest:

    if score >= 90:
        grade = "A"
    elif score >= 80:
        grade = "B"
    elif score >= 70:
        grade = "C"
    else:
        grade = "F"

Exercises for this chapter ask you to write small, self-contained functions
that compute an average, find a maximum, count values above a threshold,
count even numbers, and convert a numeric score into a letter grade -- the
same five patterns used throughout this chapter.
"""

assert len(CHAPTER_TEXT) < 8_000, (
    "Demo chapter content grew past the safety margin under the 10,000-char "
    "truncation limit in services/exercise_generator.py. Shrink it back down "
    "— see the module docstring before changing this on purpose."
)


# ---------------------------------------------------------------------------
# Canned exercises — same schema generate_exercises_from_pdf_content() would
# produce. Every solution_code below was hand-verified against its own
# test_cases using the same output-matching rules as services/code_runner.py
# (str(actual) == str(expected).strip()).
# ---------------------------------------------------------------------------

EXERCISES = [
    {
        "title": "Calculate the Average",
        "description": (
            "Write a function that takes a list of numbers and returns their "
            "average. Example data: [72, 88, 91, 65, 79]."
        ),
        "difficulty": "easy",
        "function_name": "calculate_average",
        "language": "Python",
        "solution_code": (
            "def calculate_average(numbers):\n"
            "    total = sum(numbers)          # add up every value in the list\n"
            "    count = len(numbers)          # count how many values there are\n"
            "    average = total / count       # compute the mean\n"
            "    print(\"Average:\", average)    # display for the student\n"
            "    return average                # return for automated testing\n"
        ),
        "test_cases": [
            {"description": "Five positive integers", "input": [1, 2, 3, 4, 5], "expected_output": "3.0", "weight": 1},
            {"description": "Two numbers", "input": [10, 20], "expected_output": "15.0", "weight": 1},
            {"description": "Single value", "input": [7], "expected_output": "7.0", "weight": 1},
            {"description": "Negative and positive cancel out", "input": [-5, 5], "expected_output": "0.0", "weight": 1},
            {"description": "Repeated values", "input": [4, 4, 4, 4], "expected_output": "4.0", "weight": 1},
        ],
    },
    {
        "title": "Find the Maximum",
        "description": (
            "Write a function that takes a list of numbers and returns the "
            "largest value. Example data: [3, 1, 4, 1, 5, 9, 2, 6]."
        ),
        "difficulty": "easy",
        "function_name": "find_maximum",
        "language": "Python",
        "solution_code": (
            "def find_maximum(numbers):\n"
            "    largest = numbers[0]          # start with the first value as a guess\n"
            "    for value in numbers:         # check every value in the list\n"
            "        if value > largest:       # is this value bigger than our current guess?\n"
            "            largest = value       # update the guess\n"
            "    print(\"Maximum:\", largest)    # display for the student\n"
            "    return largest                # return for automated testing\n"
        ),
        "test_cases": [
            {"description": "Mixed values", "input": [3, 1, 4, 1, 5, 9, 2, 6], "expected_output": "9", "weight": 1},
            {"description": "All negative", "input": [-1, -5, -3], "expected_output": "-1", "weight": 1},
            {"description": "Single value", "input": [42], "expected_output": "42", "weight": 1},
            {"description": "All equal", "input": [0, 0, 0], "expected_output": "0", "weight": 1},
            {"description": "Max in the middle", "input": [100, 99, 101, 98], "expected_output": "101", "weight": 1},
        ],
    },
    {
        "title": "Count Values Above a Threshold",
        "description": (
            "Write a function that takes a list of numbers and a threshold, and "
            "returns how many values are strictly greater than the threshold."
        ),
        "difficulty": "medium",
        "function_name": "count_above_threshold",
        "language": "Python",
        "solution_code": (
            "def count_above_threshold(numbers, threshold):\n"
            "    count = 0                              # start the counter at zero\n"
            "    for value in numbers:                  # look at every value in the list\n"
            "        if value > threshold:               # does it exceed the threshold?\n"
            "            count += 1                       # yes, so count it\n"
            "    print(\"Count above threshold:\", count)  # display for the student\n"
            "    return count                            # return for automated testing\n"
        ),
        "test_cases": [
            {"description": "Two of five above 3", "input": {"numbers": [1, 2, 3, 4, 5], "threshold": 3}, "expected_output": "2", "weight": 1},
            {"description": "One of three above 25", "input": {"numbers": [10, 20, 30], "threshold": 25}, "expected_output": "1", "weight": 1},
            {"description": "None strictly above the threshold", "input": {"numbers": [5, 5, 5], "threshold": 5}, "expected_output": "0", "weight": 1},
            {"description": "Threshold of zero", "input": {"numbers": [-1, 0, 1, 2], "threshold": 0}, "expected_output": "2", "weight": 1},
            {"description": "Single value above threshold", "input": {"numbers": [100], "threshold": 50}, "expected_output": "1", "weight": 1},
        ],
    },
    {
        "title": "Count Even Numbers",
        "description": (
            "Write a function that takes a list of numbers and returns how many "
            "of them are even."
        ),
        "difficulty": "medium",
        "function_name": "count_evens",
        "language": "Python",
        "solution_code": (
            "def count_evens(numbers):\n"
            "    count = 0                         # start the counter at zero\n"
            "    for value in numbers:             # check every number in the list\n"
            "        if value % 2 == 0:              # is this number even?\n"
            "            count += 1                   # yes, so count it\n"
            "    print(\"Even count:\", count)       # display for the student\n"
            "    return count                       # return for automated testing\n"
        ),
        "test_cases": [
            {"description": "Three evens out of six", "input": [1, 2, 3, 4, 5, 6], "expected_output": "3", "weight": 1},
            {"description": "No evens", "input": [1, 3, 5, 7], "expected_output": "0", "weight": 1},
            {"description": "All evens", "input": [2, 4, 6, 8], "expected_output": "4", "weight": 1},
            {"description": "Zero counts as even", "input": [0], "expected_output": "1", "weight": 1},
            {"description": "Negative evens count too", "input": [-2, -1, 0, 1, 2], "expected_output": "3", "weight": 1},
        ],
    },
    {
        "title": "Convert a Score to a Letter Grade",
        "description": (
            "Write a function that takes a single numeric score and returns a "
            "letter grade: 'A' for 90+, 'B' for 80-89, 'C' for 70-79, otherwise 'F'."
        ),
        "difficulty": "hard",
        "function_name": "letter_grade",
        "language": "Python",
        "solution_code": (
            "def letter_grade(score):\n"
            "    if score >= 90:                    # check for an A-range score\n"
            "        grade = \"A\"                     # assign A\n"
            "    elif score >= 80:                  # check for a B-range score\n"
            "        grade = \"B\"                     # assign B\n"
            "    elif score >= 70:                  # check for a C-range score\n"
            "        grade = \"C\"                     # assign C\n"
            "    else:                              # anything below 70\n"
            "        grade = \"F\"                     # assign F\n"
            "    print(\"Letter grade:\", grade)      # display for the student\n"
            "    return grade                       # return for automated testing\n"
        ),
        "test_cases": [
            {"description": "Clear A", "input": 95, "expected_output": "A", "weight": 1},
            {"description": "Clear B", "input": 82, "expected_output": "B", "weight": 1},
            {"description": "Clear C", "input": 71, "expected_output": "C", "weight": 1},
            {"description": "Clear F", "input": 50, "expected_output": "F", "weight": 1},
            {"description": "A boundary (inclusive)", "input": 90, "expected_output": "A", "weight": 1},
            {"description": "Just below C boundary is F", "input": 69, "expected_output": "F", "weight": 1},
        ],
    },
]

# ---------------------------------------------------------------------------
# Practice-progress fixture: gives the analytics page real, contrasting data
# on first load (a strong performer and a struggling performer) instead of
# an empty table. exercise_index is 1-based into EXERCISES above.
#   (student index in STUDENTS, exercise_index, best_score, attempts, time_spent_s)
# ---------------------------------------------------------------------------

PROGRESS_FIXTURE = [
    # Jordan Kim (index 0) — strong performer, attempted all 5 exercises.
    (0, 1, 100, 1, 40),
    (0, 2, 100, 1, 55),
    (0, 3, 90, 2, 70),
    (0, 4, 85, 1, 60),
    (0, 5, 80, 3, 120),
    # Riley Chen (index 1) — struggling performer, only started 2 of 5.
    (1, 1, 70, 2, 90),
    (1, 2, 30, 1, 150),
]


# ---------------------------------------------------------------------------
# Production guard
# ---------------------------------------------------------------------------


def _looks_local(database_url: str) -> bool:
    """Best-effort check that database_url points at an obviously-local DB."""
    try:
        url = database_url if "://" in database_url else "postgresql://" + database_url
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return False
    return host in ("localhost", "127.0.0.1", "::1") or host.endswith(".local")


def _safe_host(database_url: str) -> str:
    """Return just the host, never the password, for log messages."""
    try:
        url = database_url if "://" in database_url else "postgresql://" + database_url
        return urlparse(url).hostname or "<unparseable>"
    except Exception:
        return "<unparseable>"


def guard_not_production(database_url: str, will_write: bool) -> None:
    """Refuse to run against anything that looks like production.

    Exits the process (does not return) on refusal.
    """
    env = os.getenv("FLASK_ENV", os.getenv("ENV", "development"))
    if env == "production":
        logger.error(
            "REFUSING TO RUN: FLASK_ENV=production. This script must never "
            "touch a production database, no override exists for this check."
        )
        sys.exit(1)

    if not will_write:
        return  # dry-run never connects or writes — always safe

    if not database_url:
        logger.error("DATABASE_URL is not set (checked env and --database-url).")
        sys.exit(1)

    if _looks_local(database_url):
        return

    if os.getenv("SEED_DEMO_CONFIRM") != "yes":
        logger.error(
            "DATABASE_URL host '%s' does not look like a local/demo database.\n"
            "Refusing to write. This script must only ever run against a "
            "demo/staging database.\n"
            "If you are SURE this is not production, re-run with "
            "SEED_DEMO_CONFIRM=yes set in the environment.",
            _safe_host(database_url),
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def get_conn(database_url: str):
    return psycopg2.connect(database_url)


def all_demo_user_ids():
    return [PROFESSOR_ID] + [s["user_id"] for s in STUDENTS]


def reset_demo_fixtures(conn) -> None:
    """Delete every row belonging to the demo fixtures.

    Deleting the `users` rows cascades (ON DELETE CASCADE) through classes,
    class_chapters, class_exercises, class_enrollments, practice_progress,
    exercise_attempts, user_profiles, user_settings, user_preferences, and
    ai_agent_digest — see migrations/006_core_tables.sql and
    tests/integration/conftest.py for the FK chain. This makes reset a single
    statement instead of a long manual child-table walk that would silently
    drift out of sync with the schema over time.
    """
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE user_id = ANY(%s)", (all_demo_user_ids(),))
    deleted_users = cur.rowcount
    cur.execute("DELETE FROM tenants WHERE tenant_id = %s", (TENANT_ID,))
    cur.close()
    logger.info("Reset: removed %d existing demo user(s) (and cascaded children).", deleted_users)


# ---------------------------------------------------------------------------
# Seeding
# ---------------------------------------------------------------------------


def _attempt_score_curve(final_score: int, attempts: int) -> list:
    """Return `attempts` scores ending in final_score, simulating improvement."""
    if attempts <= 1:
        return [final_score]
    scores = []
    for i in range(attempts - 1):
        earlier = max(0, final_score - 20 * (attempts - 1 - i))
        scores.append(earlier)
    scores.append(final_score)
    return scores


def seed_demo_class(conn) -> None:
    from core.auth import hash_password
    from repositories import auth_repository as auth_repo
    from repositories import chapter_repository as chapter_repo
    from repositories import class_repository as class_repo
    from repositories import user_repository as user_repo

    # --- 1. Tenant ----------------------------------------------------------
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tenants (tenant_id, name, is_active) VALUES (%s, %s, true)",
        (TENANT_ID, TENANT_NAME),
    )
    cur.close()
    logger.info("Created demo tenant: %s", TENANT_NAME)

    # --- 2. Professor ---------------------------------------------------------
    password_hash = hash_password(DEMO_PASSWORD)
    auth_repo.insert_user(
        conn, PROFESSOR_ID, PROFESSOR_NAME, PROFESSOR_EMAIL, password_hash, "professor", tenant_id=TENANT_ID
    )
    auth_repo.create_default_profile(conn, PROFESSOR_ID)
    auth_repo.create_default_settings(conn, PROFESSOR_ID)
    auth_repo.create_default_preferences(conn, PROFESSOR_ID)
    logger.info("Created demo professor: %s <%s>", PROFESSOR_NAME, PROFESSOR_EMAIL)

    # --- 3. Students ------------------------------------------------------
    for student in STUDENTS:
        auth_repo.insert_user(
            conn,
            student["user_id"],
            student["name"],
            student["email"],
            password_hash,
            "student",
            tenant_id=TENANT_ID,
        )
        auth_repo.create_default_profile(conn, student["user_id"])
        auth_repo.create_default_settings(conn, student["user_id"])
        auth_repo.create_default_preferences(conn, student["user_id"])
        logger.info("Created demo student: %s <%s>", student["name"], student["email"])

    # --- 4. Class -----------------------------------------------------------
    class_repo.insert_class(conn, CLASS_ID, PROFESSOR_ID, CLASS_NAME, CLASS_DESCRIPTION)
    logger.info("Created demo class: %s (%s)", CLASS_NAME, CLASS_ID)

    # --- 5. Enroll students -------------------------------------------------
    for student in STUDENTS:
        class_repo.enroll_student(conn, CLASS_ID, student["user_id"])
    logger.info("Enrolled %d student(s) in %s", len(STUDENTS), CLASS_ID)

    # --- 6. Chapter (source content) ----------------------------------------
    chapter_repo.insert_chapter(
        conn,
        CHAPTER_ID,
        CLASS_ID,
        CHAPTER_TITLE,
        CHAPTER_DESCRIPTION,
        1,
        None,
        CHAPTER_FILENAME,
        CHAPTER_TEXT.encode("utf-8"),
    )
    logger.info(
        "Created chapter '%s' (%d chars of source content, %s)",
        CHAPTER_TITLE,
        len(CHAPTER_TEXT),
        CHAPTER_FILENAME,
    )

    # --- 7. Exercises (canned — see module docstring) -----------------------
    exercise_ids = []
    for idx, ex in enumerate(EXERCISES, start=1):
        exercise_id = f"{CHAPTER_ID}-ex-{idx}"
        exercise_ids.append(exercise_id)
        chapter_repo.insert_exercise(
            conn,
            exercise_id,
            CHAPTER_ID,
            CLASS_ID,
            ex["title"],
            ex["description"],
            ex["difficulty"],
            ex["solution_code"],
            idx,
            function_name=ex["function_name"],
            test_cases=ex["test_cases"],
            language=ex["language"],
        )
    logger.info("Created %d exercise(s) for chapter %s", len(exercise_ids), CHAPTER_ID)

    # --- 8. Practice progress + attempt history -----------------------------
    now = datetime.now(timezone.utc)
    for student_idx, exercise_idx, best_score, attempts, time_spent in PROGRESS_FIXTURE:
        student_id = STUDENTS[student_idx]["user_id"]
        exercise_id = exercise_ids[exercise_idx - 1]
        exercise_title = EXERCISES[exercise_idx - 1]["title"]
        accuracy = round(best_score / 100.0, 4)

        user_repo.upsert_practice_progress(
            conn,
            student_id,
            exercise_id,
            exercise_title,
            best_score,
            accuracy,
            time_spent,
            attempts,
            best_score,
            True,  # is_new_best
            CLASS_ID,
            exercise_id,
        )

        for attempt_n, attempt_score in enumerate(_attempt_score_curve(best_score, attempts), start=1):
            attempt_accuracy = round(attempt_score / 100.0, 4)
            user_repo.insert_exercise_attempt(
                conn, student_id, exercise_id, attempt_score, attempt_accuracy, time_spent, attempt_n
            )
        # Backdate last_completed_at slightly so the demo doesn't show
        # everything happening in the same database-transaction instant.
        if best_score >= 50:
            cur = conn.cursor()
            cur.execute(
                "UPDATE practice_progress SET last_completed_at = %s "
                "WHERE user_id = %s AND exercise_id = %s",
                (now - timedelta(hours=exercise_idx), student_id, exercise_id),
            )
            cur.close()

    logger.info(
        "Seeded practice-progress + attempt history for %d (student, exercise) pair(s)",
        len(PROGRESS_FIXTURE),
    )


# ---------------------------------------------------------------------------
# Plan preview (dry run — no DB connection at all)
# ---------------------------------------------------------------------------


def print_plan():
    print("DRY RUN — no database connection made, nothing written.")
    print()
    print(f"Would reset + recreate:")
    print(f"  tenant     : {TENANT_ID} ({TENANT_NAME})")
    print(f"  professor  : {PROFESSOR_ID} <{PROFESSOR_EMAIL}>")
    for s in STUDENTS:
        print(f"  student    : {s['user_id']} <{s['email']}>")
    print(f"  class      : {CLASS_ID} — {CLASS_NAME}")
    print(f"  chapter    : {CHAPTER_ID} — {CHAPTER_TITLE} ({len(CHAPTER_TEXT)} chars of source content)")
    print(f"  exercises  : {len(EXERCISES)}")
    for ex in EXERCISES:
        print(f"      - [{ex['difficulty']:>6}] {ex['title']}")
    print(f"  progress   : {len(PROGRESS_FIXTURE)} (student, exercise) submission(s) seeded")
    print()
    print("Re-run with --execute to actually write this to DATABASE_URL.")
    print("Re-run with --teardown to delete the demo fixtures without recreating them.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually write to the DB (default is dry-run / plan preview only)",
    )
    parser.add_argument(
        "--teardown",
        action="store_true",
        help="Delete the demo fixtures and exit (do not reseed)",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Override DATABASE_URL from the environment",
    )
    args = parser.parse_args()

    database_url = args.database_url or os.getenv("DATABASE_URL")
    will_write = args.execute or args.teardown

    guard_not_production(database_url, will_write)

    if not will_write:
        print_plan()
        return

    conn = get_conn(database_url)
    try:
        reset_demo_fixtures(conn)
        if args.teardown:
            conn.commit()
            logger.info("Teardown complete — demo fixtures removed, nothing recreated.")
            return

        seed_demo_class(conn)
        conn.commit()
        logger.info("Demo class seeded successfully.")
        logger.info("Class code: %s", CLASS_ID)
        logger.info("Professor login: %s / %s", PROFESSOR_EMAIL, DEMO_PASSWORD)
        for s in STUDENTS:
            logger.info("Student login:   %s / %s", s["email"], DEMO_PASSWORD)
    except Exception:
        conn.rollback()
        logger.error("Seeding failed — rolled back, database left unchanged.", exc_info=True)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
