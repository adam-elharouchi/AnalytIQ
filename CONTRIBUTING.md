# Contributing to AnalytIQ

Welcome to the AnalytIQ codebase. This guide gets you from zero to a running
local environment and explains the patterns every new developer needs to know.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Setup (5 minutes)](#local-setup)
3. [Project Structure](#project-structure)
4. [Architecture in One Diagram](#architecture-in-one-diagram)
5. [How to Add a New API Endpoint](#how-to-add-a-new-api-endpoint)
6. [How to Add a Database Column](#how-to-add-a-database-column)
7. [Testing](#testing)
8. [Code Style](#code-style)
9. [Environment Variables](#environment-variables)
10. [Deployment](#deployment)

---

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| Python | 3.9+ | [python.org](https://python.org) |
| Docker Desktop | Latest | [docker.com](https://docker.com) |
| Git | Any | system |

---

## Local Setup

```bash
# 1. Clone
git clone https://github.com/yourusername/AnalytIQ.git
cd AnalytIQ

# 2. Install Python dependencies
make install

# 3. Copy environment template (edit .env with your actual values)
cp .env.example .env

# 4. Start PostgreSQL + Redis, run migrations, start Flask
make dev
```

Open http://localhost:5001 — the app is running.

**Minimum required .env values for local dev:**
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/analytiq
SECRET_KEY=any-random-string-for-dev
GEMINI_API_KEY=your-key-from-google-ai-studio
```

Everything else has sensible defaults for development.

---

## Project Structure

```
analytiq/
├── app.py                  # Entry point — defines create_app() and app = create_app()
├── config.py               # ALL env vars in one place — read from here, never os.getenv() elsewhere
│
├── core/                   # Infrastructure (no business logic)
│   ├── factory.py          # App setup functions called by create_app()
│   ├── database.py         # PostgreSQL connection pool (psycopg2)
│   ├── auth.py             # JWT, bcrypt, @require_auth decorator
│   ├── extensions.py       # Flask-Limiter, CSRF instances
│   ├── errors.py           # Centralized error response helpers
│   ├── cache.py            # Redis caching layer
│   ├── storage.py          # Supabase Storage client
│   ├── middleware.py       # IP blocklist, maintenance mode
│   └── audit.py            # Admin action logging
│
├── blueprints/             # HTTP layer — one file per domain
│   ├── auth.py             # POST /api/users/signup|signin|...
│   ├── classes.py          # /api/classes/*
│   ├── chapters.py         # /api/chapters/*
│   ├── exercises.py        # /api/exercises/*
│   ├── users.py            # /api/users/*
│   ├── ai.py               # POST /api/ai/chat
│   ├── superadmin.py       # /api/superadmin/*
│   ├── tenant_admin.py     # /api/tenant-admin/*
│   ├── lti.py              # /lti/* (LTI 1.3)
│   ├── sso.py              # /api/sso/*
│   └── ...
│
├── repositories/           # Data access — raw SQL, returns plain tuples/dicts
│   ├── auth_repository.py
│   ├── class_repository.py
│   └── ...
│
├── services/               # Business logic — calls repositories and external APIs
│   ├── exercise_generator.py   # Gemini API → exercises
│   ├── code_runner.py          # Sandboxed code execution
│   ├── ai_grader.py            # Gemini-based code grading
│   └── content_extractor.py   # PDF/DOCX/CSV text extraction
│
├── workers/                # Celery async tasks
│   ├── celery_app.py
│   └── tasks.py
│
├── migrations/             # Numbered SQL migrations (idempotent)
├── templates/              # Jinja2 HTML templates
├── static/                 # CSS, JS, images
│   └── js/                 # One JS module per page
│
├── tests/
│   ├── unit/               # Pure-function tests (no DB)
│   ├── integration/        # Tests against real PostgreSQL + Redis
│   └── e2e/                # Full user-flow tests
│
└── scripts/                # One-off admin / migration scripts
```

---

## Architecture in One Diagram

```
Browser / LMS
     │
     ▼
Flask (app.py → create_app())
     │
     ├── core/middleware.py   — IP blocklist, maintenance mode (before_request)
     │
     ├── blueprints/          — Parse request → validate → call service → return response
     │       │
     │       ├── repositories/ — All SQL queries (plain psycopg2, no ORM)
     │       │
     │       └── services/    — Business logic, external API calls (Gemini, Supabase)
     │
     ├── workers/tasks.py     — Celery: PDF processing, email, async exercise generation
     │
     └── core/                — Shared infrastructure: DB pool, JWT, rate limiting, cache
```

**Key rules:**
- **Blueprints** never contain SQL. They call repositories.
- **Repositories** never contain business logic. They execute SQL and return data.
- **Services** never touch Flask (`request`, `g`, `jsonify`). They are pure Python.
- **Config** is the single source of truth — never call `os.getenv()` outside `config.py`.

---

## How to Add a New API Endpoint

**Example:** `GET /api/classes/<class_id>/summary`

### Step 1 — Add the repository query

```python
# repositories/class_repository.py

def get_class_summary(conn, class_id: str) -> dict | None:
    cur = conn.cursor()
    cur.execute(
        "SELECT title, description, student_count FROM classes WHERE class_id = %s",
        (class_id,),
    )
    row = cur.fetchone()
    cur.close()
    return {"title": row[0], "description": row[1], "student_count": row[2]} if row else None
```

### Step 2 — Add the route to the blueprint

```python
# blueprints/classes.py

from core.errors import not_found, server_error

@bp.route("/api/classes/<class_id>/summary", methods=["GET"])
@require_auth
def get_class_summary(class_id):
    try:
        conn = get_db_connection()
        summary = class_repo.get_class_summary(conn, class_id)
        if summary is None:
            return not_found("Class not found")
        return jsonify(summary), 200
    except Exception as e:
        logger.error("get_class_summary error: %s", e, exc_info=True)
        return server_error()
```

### Step 3 — Write a test

```python
# tests/integration/test_classes_integration.py

def test_get_class_summary_returns_404_for_unknown(client, auth_headers):
    response = client.get("/api/classes/nonexistent/summary", headers=auth_headers)
    assert response.status_code == 404
    assert "error" in response.get_json()
```

That's it. No changes to `app.py` needed — blueprints are auto-registered.

---

## How to Add a Database Column

1. Create a new migration file:

```bash
# Name it with the next number in sequence
touch migrations/013_my_new_column.sql
```

2. Write idempotent SQL:

```sql
-- migrations/013_my_new_column.sql
ALTER TABLE classes
    ADD COLUMN IF NOT EXISTS archived BOOLEAN NOT NULL DEFAULT FALSE;
```

3. Apply locally:

```bash
make migrate
```

Migrations run automatically at app startup in all environments. They are
idempotent — safe to run multiple times.

---

## Testing

```bash
make test            # unit + integration (recommended before pushing)
make test-unit       # fast, no DB needed
make test-integration # requires local DB + Redis (make services first)
make test-cov        # with HTML coverage report in htmlcov/
```

**Test philosophy:**
- Integration tests hit a real PostgreSQL instance. They are the primary source
  of confidence. Do not mock the database.
- Unit tests cover pure functions only (validators, formatters, transformers).
- E2E tests cover full user flows and require a running app.

Authentication in tests: set `TESTING=True` in the Flask config and send
`X-Test-User-ID: <uuid>` to bypass JWT verification.

---

## Code Style

```bash
make lint           # flake8
make format         # black (writes files)
make format-check   # black --check (used in CI)
make typecheck      # mypy
```

All four gates run in CI. A PR cannot merge if any gate is red.

Key conventions:
- **Error responses** — always use `core/errors.py` helpers (`bad_request()`,
  `not_found()`, `server_error()`, etc.). Never hand-write `jsonify({"error":
  ...}), 500` in a blueprint.
- **Logging** — `logger.error(..., exc_info=True)` for exceptions; never
  `print()`.
- **Config** — read `config.SOME_VALUE`, never `os.getenv("SOME_VALUE")`.
- **Exception messages** — never return `str(e)` in a JSON response (info
  disclosure). Log the full exception server-side; return a generic message
  to the client.

---

## Environment Variables

All env vars are documented in `.env.example`. Required variables:

| Variable | Where to get it |
|---|---|
| `DATABASE_URL` | Supabase → Settings → Database → Connection string |
| `SECRET_KEY` | Generate: `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com) |
| `SUPABASE_URL` | Supabase → Settings → API |
| `SUPABASE_KEY` | Supabase → Settings → API (service_role key) |
| `REDIS_URL` | Upstash or local: `redis://localhost:6379/0` |

Optional feature flags (default off):

| Flag | Effect |
|---|---|
| `FEATURE_ASYNC_TASKS=True` | Enable Celery background tasks |
| `FEATURE_CACHING=True` | Enable Redis response caching |
| `FEATURE_SSO=True` | Enable per-tenant SSO (OAuth2/OIDC) |
| `FEATURE_CSRF_PROTECTION=True` | Enable CSRF tokens on all forms |

---

## Deployment

The app deploys to [Render](https://render.com) via `render.yaml`.

```bash
# Production process (set in render.yaml)
gunicorn app:app --config gunicorn.conf.py

# Celery worker (separate Render service)
celery -A workers.celery_app worker --loglevel=info
```

CI/CD runs on every push to `main` via `.github/workflows/ci.yml`:
- flake8 lint
- black format check
- mypy type check
- pytest (unit + integration against a real Postgres/Redis instance)
- bandit security scan

A green CI is required before merging to `main`.
