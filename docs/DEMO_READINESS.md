# Demo Readiness — Seeded Demo Class

Owner: Adam. This is the pre-flight checklist for any live buyer or professor
demo, plus the exact commands to seed / verify / reset the demo class built
by `scripts/seed_demo_class.py`.

**Status as of 2026-08-12: still NOT run end-to-end against a live database
by anyone.** No agent has (or should have) a `DATABASE_URL` or
`GEMINI_API_KEY` — this has been blocking on "someone with credentials runs
it once" for three days. **Section 0 below is that path, made copy-pasteable
end-to-end: it stands up a local Postgres from something already in this
repo (`docker-compose.yml` via `make services`), so it needs nothing you
don't already have installed (Docker + Python).** Do not treat the
60-second claim as measured until someone actually runs it and records a
real number in section 4.

---

## 0. Fastest path — the exact 10-minute local run (start here)

This is the whole B6 task end-to-end: stand up a throwaway local database,
seed the demo class into it, run the app, measure the loop, tear it down.
Every command below is literal — copy-paste in order. Nothing here touches
staging or production, and nothing here needs `GEMINI_API_KEY` (confirmed
below in step 6).

**Time budget:** steps 1–5 are one-time setup (~5 min, mostly Docker pulling
the Postgres image the first time). Steps 6–8 are the actual demo-loop
verification (~2 min). Step 9 tears everything down (~30 sec).

### Preconditions

- Docker Desktop running (for local Postgres — this repo already has
  `docker-compose.yml` + a `make services` target for this; no new setup
  invented here).
- Python 3.9+ with this repo's dependencies installed (`pip install -r
  requirements.txt`, or activate the repo's existing `.venv` if you use one).
- A terminal in the repo root (`AnalytIQ Repo/`).
- You do **not** need `GEMINI_API_KEY` for this loop. `config.validate_config()`
  is the only thing that would demand it, and it is never called at app
  startup (checked in `core/factory.py` / `app.py` on 2026-08-12) — nothing
  in the seeded-demo grade/analytics loop calls Gemini (see §1 below: the 5
  exercises are canned, grading is local code execution).

### The commands, in order

```bash
cd "AnalytIQ Repo"

# 1) Start a local Postgres (+ Redis) in Docker — uses this repo's existing
#    docker-compose.yml, nothing new to install.
make services
# Success looks like: "PostgreSQL: localhost:5432  |  Redis: localhost:6379"
# printed at the end. If you want to confirm the container is actually
# healthy (not just started): `docker ps` should show a `postgres:14-alpine`
# container with STATUS "healthy" (health check is built into the compose
# file, ~5-10s after start).

# 2) Point this shell session at that local DB. This does NOT edit your
#    .env file — `load_dotenv()` never overrides an already-exported
#    variable (confirmed: python-dotenv's `override` defaults to False), so
#    exporting here is safe even if your real .env has a different
#    DATABASE_URL in it.
#
#    The "?sslmode=disable" is NOT optional — read this before dropping it.
#    core/database.py's init_db_pool() appends "sslmode=require" to
#    DATABASE_URL automatically UNLESS the URL already contains "sslmode"
#    (checked by reading core/database.py on 2026-08-12). The docker-compose
#    postgres:14-alpine container has SSL off by default, so without this,
#    `python3 app.py` in step 6 will fail to get a DB connection — the
#    failure is swallowed once (logged as a warning, app still boots) but
#    every API call afterwards (including the whole §4 timed loop) will 500.
#    db_migrate.py and the seeder are unaffected either way (they don't force
#    sslmode), so this only matters for step 6 — but set it here regardless
#    so you don't have to remember it later.
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/analytiq?sslmode=disable"
export SECRET_KEY="local-dev-secret-not-for-prod"
unset FLASK_ENV   # make sure it is NOT "production" — the seeder hard-refuses if it is

# 3) Apply the schema to the fresh local DB.
python3 db_migrate.py
# Success looks like: one "db_migrate: applied 0XX_....sql" log line per file
# in migrations/ (there are 14 as of 2026-08-12), ending with
# "db_migrate CLI: all migrations applied (or already up to date)." and the
# process exiting 0. (Re-running this later is harmless/idempotent — it will
# just print nothing-to-do.)

# 4) Sanity-check the seeder against THIS session's actual output before
#    writing anything (dry run — no DB connection at all). Verified in this
#    session on 2026-08-12; you should see exactly this:
python3 scripts/seed_demo_class.py
```

Expected dry-run output (byte-for-byte, captured 2026-08-12 with no DB and
no GEMINI_API_KEY set):

```
DRY RUN — no database connection made, nothing written.

Would reset + recreate:
  tenant     : demo-tenant (AnalytIQ Demo University)
  professor  : demo-professor-001 <demo.professor@analytiq-demo.local>
  student    : demo-student-jordan <jordan.kim@analytiq-demo.local>
  student    : demo-student-riley <riley.chen@analytiq-demo.local>
  class      : DEMOCLASS01 — Intro to Data Analysis with Python (Demo)
  chapter    : demo-chapter-1 — Chapter 1 — Lists, Loops, and Basic Statistics (2323 chars of source content)
  exercises  : 5
      - [  easy] Calculate the Average
      - [  easy] Find the Maximum
      - [medium] Count Values Above a Threshold
      - [medium] Count Even Numbers
      - [  hard] Convert a Score to a Letter Grade
  progress   : 7 (student, exercise) submission(s) seeded

Re-run with --execute to actually write this to DATABASE_URL.
Re-run with --teardown to delete the demo fixtures without recreating them.
```

If that matches, continue. If it doesn't, stop — something changed in the
script and the rest of this checklist may be stale.

```bash
# 5) Actually seed it. `localhost` is auto-recognized as safe, so no extra
#    confirmation env var is needed here (SEED_DEMO_CONFIRM is only required
#    for a non-local DATABASE_URL).
python3 scripts/seed_demo_class.py --execute
# Success looks like log lines ending in:
#   "Demo class seeded successfully."
#   "Class code: DEMOCLASS01"
#   "Professor login: demo.professor@analytiq-demo.local / AnalytIQDemo#2026"
#   "Student login:   jordan.kim@analytiq-demo.local / AnalytIQDemo#2026"
#   "Student login:   riley.chen@analytiq-demo.local / AnalytIQDemo#2026"

# 6) Start the app.
python3 app.py
```

Watch the startup log for the actual port — **do not assume 5000.**
`app.py` defaults to `PORT=5001` when `PORT` is unset (confirmed by reading
`app.py` on 2026-08-12: `port = int(os.getenv("PORT", 5001))`). The startup
log prints the real values to use:

```
Starting Flask server on port 5001 (debug=False)
API base URL: http://localhost:5001/api
Health check: http://localhost:5001/api/health
```

Use whatever port actually printed for `BASE_URL` in step 7 below (the §4
timing script below was written assuming port 5000, which is wrong for a
default local run — override it).

```bash
# 7) In a SECOND terminal (leave app.py running in the first): confirm the
#    app is actually up before timing anything.
curl -s http://localhost:5001/api/health
# Success: a 200 response (exact body doesn't matter — just confirms the
# app + DB connection are alive before you start the timed loop).

# 8) Run the timed upload->exercises->grade->analytics loop. This is the
#    §4 script below — set BASE_URL to match the port from step 6.
BASE_URL="http://localhost:5001" bash -c '<paste the full script from section 4 below>'
# Record the `real` time `time` prints, and the /tmp/grade_result.json
# contents (must show "total_score": 100 and "passed": true), in section 4.

# 9) Tear down when you're done (stop the app with Ctrl-C in terminal 1 first).
python3 scripts/seed_demo_class.py --teardown
make stop
# `make stop` runs `docker-compose down` — this stops the containers but
# keeps the `postgres_data` volume, so re-running `make services` next time
# is instant and re-migrated data persists. If you want a fully clean slate
# instead, run `docker-compose down -v` to also drop the volume (you would
# need to redo step 3 next time).
```

### If something refuses to run

- `python3 scripts/seed_demo_class.py --execute` prints "REFUSING TO RUN:
  FLASK_ENV=production" → you have `FLASK_ENV=production` set somewhere
  (check `echo $FLASK_ENV`, and your shell profile / exported env). Unset it
  for this session.
- It prints "DATABASE_URL host '...' does not look like a local/demo
  database" → your `DATABASE_URL` isn't pointing at `localhost` /
  `127.0.0.1` / `*.local`. If you're intentionally targeting a real
  demo/staging host (not local, not prod), re-run with
  `SEED_DEMO_CONFIRM=yes` set. If you're trying to run this locally, re-check
  step 2 — you may have a stale `DATABASE_URL` exported from a previous
  session.
- `db_migrate.py` fails to connect → `make services` didn't finish starting
  Postgres yet. Check `docker ps` for a healthy `postgres:14-alpine`
  container, or run `docker-compose logs db`.
- Every request in step 7/8 returns a 500, and `app.py`'s own log shows
  something like "SSL connection is required" or "server does not support
  SSL, but SSL was required" → you exported `DATABASE_URL` without
  `?sslmode=disable` (see the comment on step 2). Kill `app.py`, re-export
  `DATABASE_URL` with `?sslmode=disable` on the end, and restart it.

---

## 1. What the demo class is

`scripts/seed_demo_class.py` creates a small, fixed, idempotent fixture:

| Thing | Value |
|---|---|
| Tenant | `demo-tenant` — "AnalytIQ Demo University" |
| Professor | `demo.professor@analytiq-demo.local` |
| Students | `jordan.kim@analytiq-demo.local` (strong performer, 5/5 exercises attempted), `riley.chen@analytiq-demo.local` (struggling, 2/5 attempted) |
| Password (all 3 demo accounts) | `AnalytIQDemo#2026` |
| Class code | `DEMOCLASS01` — "Intro to Data Analysis with Python (Demo)" |
| Chapter | "Chapter 1 — Lists, Loops, and Basic Statistics" (~2.3k characters of real source text, stored as `chapter1_lists_and_stats.txt`) |
| Exercises | 5 (2 easy / 2 medium / 1 hard), each with real test cases |
| Progress data | 7 seeded (student, exercise) submissions so the analytics page is never empty |

Two important design choices, both explained in the script's module
docstring — read it before changing either:

- **The chapter content is deliberately short (~2.3k chars).**
  `services/exercise_generator.py` has a hard-coded 10,000-character
  truncation limit that silently cuts off longer input with no warning to
  the user. That bug's fix is Adam's Aug 12 review item and is **not
  approved yet**. Do not lengthen the demo chapter until that fix has
  shipped and been verified — a longer chapter risks silently tripping the
  exact bug this fixture exists to avoid.
- **The 5 exercises are pre-written, not generated live by Gemini.**
  This removes the only two things that could make the demo flaky or cost
  money on every reset: a network call to Gemini, and a Gemini API key
  being present at all. Grading them still runs for real — `POST
  /api/exercises/<id>/grade` runs the submitted code against real test
  cases via `services/code_runner.run_test_cases()`, which is deterministic
  local execution, not an AI call.

---

## 2. Commands

All commands assume you are in the repo root with a `.env` (or exported
`DATABASE_URL`) pointing at a **demo/staging** database — never production.

```bash
# Preview the plan — makes NO database connection, writes nothing:
python3 scripts/seed_demo_class.py

# Seed (or reset to known-good state — safe to re-run any time, any number
# of times; it deletes-and-recreates rather than accumulating duplicates):
python3 scripts/seed_demo_class.py --execute

# Remove the demo fixtures without recreating them:
python3 scripts/seed_demo_class.py --teardown
```

The script refuses to run against anything that looks like production:

- Hard refusal, no override, if `FLASK_ENV=production`.
- For any `DATABASE_URL` whose host isn't `localhost` / `127.0.0.1` /
  `*.local`, it additionally requires `SEED_DEMO_CONFIRM=yes` in the
  environment before `--execute` or `--teardown` will do anything.

If you ever see the script refuse to run and you're confident the target
database is a safe demo/staging DB, set `SEED_DEMO_CONFIRM=yes` for that one
command — do not weaken the guard in the script itself.

**Prerequisite:** the DB schema must already be migrated
(`python3 db_migrate.py`, or however your environment normally applies
`migrations/*.sql`) — this script does not create tables, only rows.

---

## 3. Pre-demo checklist (run this before any live buyer/professor call)

1. [ ] Confirm you're pointed at the demo/staging environment, not prod
       (check the URL you're about to screen-share, and `FLASK_ENV` if you
       have terminal access).
2. [ ] Hit the health check once to make sure the app isn't cold
       (`GET /api/health`) — Render free/starter tiers can have a cold-start
       delay after idling; do this a minute or two before you go live, not
       during the call.
3. [ ] Re-seed the demo class so it's in exactly the known-good state:
       `python3 scripts/seed_demo_class.py --execute`
4. [ ] Log in as the demo professor (`demo.professor@analytiq-demo.local`)
       in the browser tab you'll actually share. Confirm the class
       `DEMOCLASS01` shows the chapter and all 5 exercises.
5. [ ] Log in as `jordan.kim@analytiq-demo.local` in a second tab/profile
       (or private window). Open exercise 1 ("Calculate the Average"),
       paste in a correct solution (the script's console output / section 4
       below has one), and click Grade once — confirm it returns 100/100
       within a couple of seconds. This is the single most likely step to
       stutter (see "known-fragile steps" below) — catching it now beats
       catching it live.
6. [ ] Back in the professor tab, open the class progress / analytics view
       and confirm both Jordan (strong, mostly-complete) and Riley
       (struggling, 2 of 5 started) show up with different completion
       levels — this contrast is the point of seeding two students.
7. [ ] Close any other tabs/apps that might pop up a notification during
       screen share.
8. [ ] Have the reset command (step 3) ready to run again silently between
       back-to-back demos so each one starts from the same known-good state.

---

## 4. Measuring the 60-second loop yourself

This was not measured in this session (no live DB/API access — see the
status note at the top). Here is the exact, copy-paste sequence to measure
it yourself in under 5 minutes. It exercises the same four stages
(upload/exercises already seeded → grade → analytics) end-to-end against a
running instance of the app, using only the seeded fixtures above, and wraps
the whole thing in `time` so you get a real wall-clock number.

If you followed §0 for a local run, plug in the port that `python3 app.py`
actually printed at startup — **do not assume 5000.** `app.py` defaults to
`PORT=5001` when the `PORT` env var is unset (`port =
int(os.getenv("PORT", 5001))`), so a local run without `PORT` set in `.env`
will be on `5001`, not `5000`.

```bash
# Set this to wherever the app is running (local dev server or staging URL) —
# for a local §0 run, use the port app.py actually printed at startup.
BASE_URL="http://localhost:5001"
PASSWORD="AnalytIQDemo#2026"

time (
  set -e

  # 1. Sign in as the demo professor.
  PROF_TOKEN=$(curl -s -X POST "$BASE_URL/api/users/signin" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"demo.professor@analytiq-demo.local\",\"password\":\"$PASSWORD\"}" \
    | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")

  # 2. View the class + the seeded chapter + exercises
  #    ("upload" and "exercises" stages — already seeded, this is the
  #    review/verification step Adam's plan describes).
  curl -s "$BASE_URL/api/classes/DEMOCLASS01" \
    -H "Authorization: Bearer $PROF_TOKEN" > /dev/null
  curl -s "$BASE_URL/api/classes/DEMOCLASS01/resources" \
    -H "Authorization: Bearer $PROF_TOKEN" > /dev/null
  curl -s "$BASE_URL/api/chapters/demo-chapter-1/exercises" \
    -H "Authorization: Bearer $PROF_TOKEN" > /dev/null

  # 3. Sign in as a demo student and grade exercise 1 for real
  #    ("grade" stage — a real code_runner execution, not a canned result).
  STUDENT_TOKEN=$(curl -s -X POST "$BASE_URL/api/users/signin" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"jordan.kim@analytiq-demo.local\",\"password\":\"$PASSWORD\"}" \
    | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")

  curl -s -X POST "$BASE_URL/api/exercises/demo-chapter-1-ex-1/grade" \
    -H "Authorization: Bearer $STUDENT_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"code":"def calculate_average(numbers):\n    total = sum(numbers)\n    count = len(numbers)\n    average = total / count\n    print(\"Average:\", average)\n    return average"}' \
    > /tmp/grade_result.json

  cat /tmp/grade_result.json
  echo

  # 4. View the analytics / progress page ("analytics" stage).
  curl -s "$BASE_URL/api/classes/DEMOCLASS01/progress" \
    -H "Authorization: Bearer $PROF_TOKEN" > /dev/null
)
```

Read the `real` line `time` prints at the end — that is your measured
upload→exercises→grade→analytics loop against the 60-second target. Sanity
check `/tmp/grade_result.json` shows `"total_score": 100` and
`"passed": true` before trusting the timing (a fast failure is not a fast
success).

Record the result here once measured:

> **Measured loop time:** _not yet recorded — run the sequence above and
> fill this in._

---

## 5. Known-fragile steps and what to do when one stutters

| Step | Failure mode | What to do |
|---|---|---|
| Live code grading (`POST /api/exercises/<id>/grade`) | If `SANDBOX_USE_CONTAINER=true` in the environment but Docker isn't running, grading fails closed with "The code sandbox is unavailable." | Default is `SANDBOX_USE_CONTAINER=False` (runs the grading harness as a local subprocess, no Docker needed) — confirm this env var is unset/false on whatever instance you're demoing from, or confirm Docker is actually up if it's on. |
| Live PDF upload of NEW content (not the seeded chapter) | The 10,000-character truncation bug (see §1) silently drops content past the limit with no warning — exercises get generated from a truncated chapter and can look wrong or thin. **This is not hypothetical: 2 of the 6 sample PDFs already sitting in this repo's `static/course-content/` folder measure over the limit — see §8.** If you (or a demo-er) reach for one of those files as "a real chapter to upload live," it will silently truncate. | For any live demo, prefer walking through the **already-seeded** chapter/exercises rather than re-uploading from scratch (the seeded chapter is a measured 2,323 chars — nowhere near the limit, see §8). If you do want to demo a live upload, use `static/course-content/Chapter 12 - Univariate Analysis.pdf`, `Chapter 7 - Introduction to Google Colab.pdf`, `Chapter 8 -California Housing.pdf`, or `Chepter 23 - Modeling.pdf` (all measured under the limit — §8). Do **not** use `Chapter 2 - Types of Analytics.pdf` or `Chapter 4 - SEMMA Process.pdf` for a live upload until the truncation fix (Adam's Aug 12 item, `reports/product-engineer/PDF_TRUNCATION_FIX_PLAN.md`) has shipped. |
| Live exercise generation from an upload | Depends on `GEMINI_API_KEY` being valid and Gemini being reachable/not rate-limited. | The seeded demo class does not depend on this at all — if Gemini is down or the key is bad, fall back to the pre-seeded chapter/exercises and skip the live-generation part of the demo. |
| App cold start | First request after idling (e.g. Render free/starter tier) can be slow (multiple seconds to tens of seconds) and will blow the 60-second target if it lands inside the timed window. | Hit `/api/health` a minute or two before going live (see checklist §3 step 2), not as part of the timed sequence. |
| Re-seeding right before a demo | Running `--execute` deletes and recreates the demo tenant/professor/students/class — if you are mid-session with the demo account logged in elsewhere, that session's JWT still works (tokens aren't tied to row identity beyond `user_id`, which doesn't change), but any *unsaved* state in a UI tab (e.g. a half-typed exercise) will look stale after reset. | Re-seed before opening any tabs for that day's demo, not in the middle of one. |
| Class code collision | `DEMOCLASS01` is a fixed ID. If a real (non-demo) class ever ends up with that exact code on a shared staging DB, the script will fail loudly with a duplicate-key error rather than silently touching someone else's data (reset only cascades from the fixed demo professor's `user_id`, so it can't delete a class it doesn't own). | If this ever happens, don't work around it by loosening the reset logic — pick a new `CLASS_ID` constant in the script and re-seed. |

---

## 6. What was actually verified in this session (and what wasn't)

**Re-confirmed 2026-08-12** (same result as 2026-08-09, re-run fresh this
session, exact output captured in §0 step 4 above): dry-run mode still
prints the correct plan and makes no DB connection; chapter content is still
2,323 characters. Also new this session: §0 (the full copy-pasteable local
path via `make services` + `db_migrate.py` + the seeder) and §8 (measured
character counts for every chapter the demo touches, plus every sample PDF
in the repo, so the truncation-bug blast radius is a measured fact, not a
guess).

Verified (no live DB required):
- `python3 -m py_compile scripts/seed_demo_class.py` — no syntax errors.
- Dry-run mode (`python3 scripts/seed_demo_class.py`, no `--execute`) prints
  the correct plan and makes no DB connection.
- Production guard refuses to run when `FLASK_ENV=production` (no bypass).
- Production guard refuses `--execute`/`--teardown` against a non-local
  `DATABASE_URL` unless `SEED_DEMO_CONFIRM=yes` is set.
- Production guard correctly *allows* a `localhost` `DATABASE_URL` through
  to the connection attempt (confirmed by intentionally pointing it at a
  closed local port and observing a normal `psycopg2.OperationalError:
  connection refused` — i.e. it reached the real seeding code, it just had
  nothing to connect to).
- Every repository function call in the script (`auth_repository`,
  `class_repository`, `chapter_repository`, `user_repository`) was checked
  against its actual signature in `repositories/*.py`.
- `core.auth.hash_password` and every `repositories/*` module the script
  imports were actually imported and exercised (not just read) in this
  session, outside of any DB connection — confirms there's no import-time
  or dependency error waiting in the `--execute` path.
- Every exercise's `solution_code` was actually executed in-process against
  every one of its `test_cases` (26 test cases across the 5 exercises, all
  passed) using the same string-comparison rule
  `services/code_runner.py`'s `_match()` falls back to
  (`str(actual).strip() == str(expected).strip()`). This is a direct
  Python `exec()` of the solution functions, not a run through the real
  sandboxed subprocess harness in `code_runner.py` — see "Not verified"
  below for that gap.
- Chapter content length (2,323 characters) confirmed well under the
  10,000-character truncation limit, with an `assert` in the script as a
  guardrail against future edits creeping it back up.

**Not verified** (blocked on no `DATABASE_URL` / no live Postgres in this
environment — this agent did not seek out credentials to work around that):
- An actual `--execute` run against a real database (row inserts, FK
  constraints, cascading deletes on re-run).
- The full HTTP loop in §4 against a running Flask instance.
- A real measured timing number for the 60-second target.
- The live `/grade` endpoint actually invoking `services/code_runner` end
  to end (sandbox execution, not just the unit-level trace).

## 7. What Adam still needs to do

1. Run §0 above, top to bottom, once (~10 minutes, mostly Docker pulling an
   image the first time). It is a local Postgres, not staging/production —
   safe to do any time, no coordination needed.
2. Record the real `time` output from §0 step 8 in §4.
3. Do the full checklist in §3 once, live, against wherever the actual
   buyer/professor demo will run from (staging/production URL, not the local
   §0 database) — this is literally the Aug 14 task on
   `PART1_EXECUTION_PLAN.md`. §0 de-risks this by catching any real bug
   (migration failure, FK error, endpoint 500) locally first, before it can
   show up live.
4. If anything in §5 actually stutters during that first run, it comes back
   to product-engineer per the plan.

---

## 8. Chapter content-length audit (measured 2026-08-12)

**Question:** does the seeded demo class — or any sample chapter sitting in
this repo that could plausibly get reached for during a live demo — exceed
the 10,000-character `_TRUNCATION_LIMIT` in
`services/exercise_generator.py:24`?

**Method:** every number below was produced by actually running the
extraction the app itself uses
(`services.content_extractor.extract_text_from_pdf_bytes` for the PDFs; the
seeder's own dry-run output, which computes `len(CHAPTER_TEXT)` in Python,
for the seeded chapter) — none of these are estimates.

### The seeded demo class itself

`scripts/seed_demo_class.py` seeds exactly **one** chapter. It is Python
source text hard-coded in the script (`CHAPTER_TEXT`), not one of the PDFs
below — confirmed by reading the script (§1 above) and by the dry-run output
in §0 step 4.

| Chapter (as seeded by `seed_demo_class.py`) | Characters extracted | Over the 10,000-char limit? |
|---|---:|---|
| Chapter 1 — Lists, Loops, and Basic Statistics (`demo-chapter-1`) | 2,323 | **No** |

**Answer for the seeded demo class: no chapter it seeds exceeds the limit.**
The demo is not silently dropping content today. This is also enforced in
code — the script asserts `len(CHAPTER_TEXT) < 8_000` at import time as a
guardrail against this drifting back up before the truncation fix ships.

### Other sample chapters shipped in this repo (NOT part of the seeded demo)

`static/course-content/` has 6 real course PDFs. Grepped for every reference
across `blueprints/`, `templates/`, `static/js/`: the **only** place any of
them is referenced anywhere in this codebase is as the fixture for the
truncation regression test (`tests/unit/test_pdf_truncation_regression.py`).
They are not wired into `seed_demo_class.py`, not served as "sample content"
in the UI, and not part of the seeded demo class. They are, however, sitting
right there in the repo under an obvious name, and are the first thing
someone would reach for if asked to demo a *live* PDF upload with "real"
content instead of the seeded chapter.

| Chapter file (`static/course-content/`) | Characters extracted | Over the 10,000-char limit? |
|---|---:|---|
| Chapter 2 - Types of Analytics.pdf | 17,677 | **Yes** |
| Chapter 4 - SEMMA Process.pdf | 16,649 | **Yes** |
| Chapter 8 -California Housing.pdf | 8,430 | No |
| Chapter 12 - Univariate Analysis.pdf | 6,549 | No |
| Chapter 7 - Introduction to Google Colab.pdf | 5,882 | No |
| Chepter 23 - Modeling.pdf | 4,123 | No |

**Answer: yes, 2 of the 6 sample PDFs already in the repo exceed the limit**
(matches the numbers already used as the regression-test fixture rationale —
re-measured independently here, not just re-quoted). If either is used for a
live "upload a real chapter" demo moment before the truncation fix ships,
the last ~43% of "Types of Analytics" (7,677 of 17,677 chars) or ~40% of
"SEMMA Process" (6,649 of 16,649 chars) never reaches Gemini, with nothing
on screen indicating anything was cut.

### Net risk-profile read

The **seeded demo class itself is safe** — §3's scripted walkthrough never
touches a PDF over the limit, so it does not need the truncation fix to
demo cleanly Friday. The risk is narrower than "the demo is broken today":
it is "do not ad-lib a live PDF upload using `Chapter 2` or `Chapter 4` from
`static/course-content/` before the fix ships" — now called out explicitly
in §5's fragile-steps table with the two filenames to avoid and four
alternates confirmed safe.
