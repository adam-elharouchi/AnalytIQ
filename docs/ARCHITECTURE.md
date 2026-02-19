# AnalytIQ Architecture

Last updated: 2026-02-18

---

## Overview

AnalytIQ is a Flask web application that allows professors to create programming exercise
classes and students to practice code in a browser-based playground, with AI-powered
exercise generation and grading.

**Live at:** https://www.myanalytiq.org
**Deployed on:** Render (Python web service + background worker)

---

## Tech Stack

| Layer         | Technology                                     |
|---------------|------------------------------------------------|
| Web framework | Python 3.9, Flask 3.0.0                        |
| Database      | PostgreSQL via Supabase (psycopg2)             |
| File storage  | Supabase Storage (S3-compatible)               |
| Cache / queue | Redis 7 (Flask-Limiter + Celery broker)        |
| Task queue    | Celery (async PDF processing)                  |
| AI            | Google Gemini API (exercise generation + chat) |
| Frontend      | Vanilla JS, HTML5, CSS3 (no framework)         |
| Auth          | JWT Bearer (PyJWT), bcrypt                     |
| CI/CD         | GitHub Actions → Render auto-deploy            |

---

## Repository Layout

```
app.py                    # Flask app init, middleware, blueprint registration (~450 lines)
config.py                 # All env vars + validate_config()
auth_helpers.py           # JWT, bcrypt, require_auth/require_role decorators, validate_email
db.py                     # ThreadedConnectionPool, get_db_connection()
audit.py                  # FERPA audit_log table + audit() helper
extensions.py             # Flask-Limiter + csrf_exempt (avoids circular imports)
cache.py                  # Redis cache helpers
celery_app.py             # Celery app factory
supabase_storage.py       # Supabase Storage client
tasks.py                  # Celery task definitions (PDF processing)
utils.py                  # Shared utilities (escaping, validation)

blueprints/               # One file per domain
  auth.py                 # POST /api/users/signup|signin|forgot-password|reset-password
  users.py                # /api/users/profile|settings|password|delete|conversations|...
  classes.py              # /api/classes/** (CRUD, enrollment, leaderboard)
  chapters.py             # /api/chapters/** (CRUD, PDF upload, exercise generation)
  exercises.py            # /api/exercises/** + progress + leaderboard
  ai.py                   # POST /api/ai/chat
  health.py               # GET /api/health, /api/csrf-token, /api/tasks/<id>, /api/contact

repositories/             # SQL-only, no business logic
  auth_repository.py
  class_repository.py
  chapter_repository.py

python/
  exercise_generator.py   # Gemini REST call → JSON exercise list
  pdf_processor.py        # PyPDF2 text extraction

tests/
  conftest.py             # Shared fixtures (mocks DB)
  integration/            # Real-DB integration tests (31 tests, pytest + psycopg2)
  test_*.py               # Unit tests (mock DB via monkeypatch)

static/ (served by app.py)
  *.html                  # 14 pages
  js/*.js                 # 14 JS modules
  styles.css              # Single stylesheet
  js/ui-states.js         # Shared loading/empty/error/modal component
  js/api-helper.js        # authFetch(), getCurrentUser(), API_BASE_URL

docs/
  SECURITY.md             # Security reference (this sibling file)
  ARCHITECTURE.md         # This file
  knowledge_base/         # Auto-generated per-topic reference docs
```

---

## Request Lifecycle

```
Browser → Flask app.py (before_request: CORS, auth context)
        → Blueprint route handler
        → Repository layer (SQL via psycopg2)
        → PostgreSQL (Supabase)
        → audit() — shares transaction
        → conn.commit()
        → after_request: security headers added
        → JSON response
```

---

## Database

- **Connection pool:** `psycopg2.pool.ThreadedConnectionPool(minconn=1, maxconn=N)`
  where N defaults to `os.cpu_count() * 2`.
- **Connection management:** `get_db_connection()` (in `db.py`) fetches a connection from
  the pool and stores it in Flask `g`; `teardown_appcontext` returns it automatically.
- **Supabase:** used only for PostgreSQL hosting and file storage (PDFs). No Supabase
  client SDK; all DB access is raw psycopg2 SQL.

### Key tables

| Table               | Purpose                                         |
|---------------------|-------------------------------------------------|
| `users`             | Accounts (user_id UUID, email, bcrypt hash, role) |
| `user_profiles`     | Display name, bio, avatar                       |
| `user_settings`     | Notification preferences                        |
| `user_preferences`  | UI preferences (theme, language)                |
| `ai_agent_digest`   | Per-user AI context summary                     |
| `classes`           | Professor-created classes (class_id = join code) |
| `class_enrollments` | Student ↔ class membership                      |
| `class_chapters`    | PDF chapters belonging to a class               |
| `class_exercises`   | Coding exercises within a chapter               |
| `exercise_progress` | Per-student exercise submission scores          |
| `conversations`     | AI chat conversation history                    |
| `password_resets`   | Short-lived email reset tokens                  |
| `audit_log`         | FERPA-compliant mutation log                    |

---

## Authentication Flow

1. Client sends `POST /api/users/signin` → receives JWT.
2. All subsequent requests include `Authorization: Bearer <token>`.
3. `@require_auth` (in `auth_helpers.py`) decodes the token and sets `g.user_id` /
   `g.user_role` for the duration of the request.
4. Role-restricted endpoints additionally use `@require_role("professor")`.

---

## AI Features

### Exercise Generation
1. Professor uploads a PDF chapter.
2. `pdf_processor.py` extracts text (PyPDF2).
3. `exercise_generator.py` calls Gemini REST API with the extracted text + a system prompt.
4. Gemini returns a JSON array of exercises (title, description, difficulty, solution_code).
5. Exercises are stored in `class_exercises`.

### AI Chat (`/api/ai/chat`)
- Proxies messages to Gemini with conversation history.
- Rate-limited: 20/min + 100/hr per user.
- Payload capped: 50 KB body, 100 messages max before forwarding.

---

## Frontend Architecture

All pages are static HTML files served directly by Flask.

| Pattern        | Details                                                             |
|----------------|---------------------------------------------------------------------|
| Auth           | `currentUser` object stored in `localStorage`                       |
| API calls      | `authFetch()` in `api-helper.js` wraps `fetch()` + JWT header       |
| UI components  | `window.uiStates` (ui-states.js): showLoading, showEmpty, showError, showConfirmModal |
| Code editor    | Plain `<textarea>` with custom line numbers and syntax highlighting |
| Grading        | Levenshtein + line-by-line similarity on client side               |
| Autosave       | 500ms debounced `localStorage` draft, keyed by exercise ID         |

---

## Background Tasks (Celery)

- **Broker / result backend:** Redis.
- **Tasks:** PDF text extraction + exercise generation (async on large files).
- **Status polling:** `GET /api/tasks/<task_id>` returns `{state, result}`.
- `FEATURE_ASYNC_TASKS=False` disables Celery (runs synchronously in CI).

---

## Deployment

- **Platform:** Render (Python web service + background worker process).
- **Web process:** `gunicorn app:app -w 4 --timeout 120`
- **Worker process:** `celery -A celery_app worker --loglevel=info`
- **Environment:** All secrets in Render env vars (see `config.py` for the full list).
- **Auto-deploy:** GitHub push to `main` → Render rebuild.

---

## CI/CD (GitHub Actions)

Three jobs on every push/PR to `main` or `develop`:

1. **test** — spins up Postgres 14 + Redis 7, installs deps, runs flake8 + black check +
   mypy + pytest with coverage.
2. **security-scan** — Bandit static analysis, uploads `bandit-report.json` artifact.
3. **deploy-notification** — logs "ready for Render" on successful `main` push.

Integration tests in `tests/integration/` require `DATABASE_URL` to be set; they are
skipped in CI unless the workflow provides a real Postgres URL.

---

## Key Design Decisions

| Decision                        | Rationale                                                 |
|---------------------------------|-----------------------------------------------------------|
| Monolith → 7 Blueprints         | Enables per-domain ownership without micro-service overhead |
| Repository layer (no ORM)       | Fine-grained SQL control; avoids N+1 and ORM magic        |
| ThreadedConnectionPool          | Reuse connections across requests without per-request connect overhead |
| JWT over sessions               | Stateless; works well with Render's ephemeral filesystem  |
| Vanilla JS frontend             | Zero build step; fast load; no framework churn            |
| Gemini for AI                   | Generous free tier; good at structured JSON output        |
| Savepoint-based integration tests | Full isolation without truncating tables between tests  |
