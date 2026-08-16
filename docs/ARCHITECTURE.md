# AnalytIQ Architecture

Last updated: 2026-07-13

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
| Frontend      | Server-rendered Jinja2 templates + vanilla JS (ES modules) |
| Auth          | JWT Bearer (PyJWT), bcrypt                     |
| CI/CD         | GitHub Actions → Render auto-deploy            |

---

## Repository Layout

```
app.py                    # create_app() — calls core/factory.py helpers in sequence
config.py                 # All env vars; only file that calls os.getenv(). config_security_warnings() runs at startup (core/factory.py:87, non-fatal); validate_config() is defined but not called by app code (tests only).
db_migrate.py             # Migration runner (applies migrations/ SQL files)
gunicorn.conf.py          # Gunicorn production config
Procfile                  # web + worker process definitions
Makefile                  # Dev tasks: make dev, make test, make flower, make migrate
docker-compose.yml        # Local services: postgres, redis, flower

blueprints/               # One file per domain
  auth.py                 # POST /api/users/signup|signin|forgot-password|reset-password
  users.py                # /api/users/profile|settings|password|delete|conversations|...
  classes.py              # /api/classes/** (CRUD, enrollment, leaderboard)
  chapters.py             # /api/chapters/** (CRUD, PDF upload, exercise generation)
  exercises.py            # /api/exercises/** + progress + leaderboard
  ai.py                   # POST /api/ai/chat
  health.py               # GET /api/health, /api/csrf-token, /api/tasks/<id>, /api/contact
  sso.py                  # SSO / OIDC login flow + admin provider management
  tenant_admin.py         # /api/tenant-admin/** (tenant-scoped admin)
  superadmin.py           # /api/superadmin/** (platform-wide admin)
  lti.py                  # LTI 1.3 launch + grade passback
  api_docs.py             # OpenAPI spec builder (Swagger UI)

repositories/             # SQL-only, no business logic
  auth_repository.py
  class_repository.py
  chapter_repository.py
  sso_repository.py
  (+ more)

core/                     # Infrastructure (imported across blueprints/services)
  factory.py              # Flask app startup helpers (setup_logging, register_blueprints, ...)
  errors.py               # Typed error classes (ApiError, NotFoundError, ...)
  database.py             # ThreadedConnectionPool, get_db_connection()
  auth.py                 # JWT, bcrypt, require_auth/require_role decorators
  audit.py                # FERPA audit_log table + audit() helper
  cache.py                # Redis cache helpers
  extensions.py           # Flask-Limiter + csrf_exempt (avoids circular imports)
  storage.py              # Supabase Storage client
  sentry.py               # Sentry SDK init
  email.py                # Email sending via Resend (uses config.RESEND_API_KEY)
  middleware.py           # IP blocklist, maintenance mode
  pagination.py           # Pagination param parsing + response builders

services/                 # Business logic
  exercise_generator.py   # Gemini REST call → JSON exercise list
  code_runner.py          # Sandboxed code execution
  content_extractor.py    # PyPDF2 / docx / csv / ipynb text extraction

workers/                  # Celery async task infrastructure
  celery_app.py           # Celery app factory + task routing + beat schedule
  tasks.py                # Task definitions with exponential-backoff retry logic

static/
  js/                     # Vanilla-JS page modules (api-helper, auth, per-page controllers)
  css/                    # styles.css
  course-content/         # Static PDFs

templates/                # Jinja2 HTML templates (legacy pages)
migrations/               # Numbered SQL migration files (idempotent)
tests/
  conftest.py             # Shared fixtures (mocks DB)
  unit/                   # Unit tests (mock DB via monkeypatch)
  integration/            # Integration tests (require live DB + Redis)

scripts/                  # One-off admin/migration scripts
docs/
  adr/                    # Architecture Decision Records (ADR-001 through ADR-004)
  ARCHITECTURE.md         # This file
  DATABASE_SCHEMA.md      # Full table reference
  (+ more topic docs)
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
- **Connection management:** `get_db_connection()` (in `core/database.py`) fetches a connection from
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
3. `@require_auth` (in `core/auth.py`) decodes the token and sets `g.user_id` /
   `g.user_role` / `g.tenant_id` for the duration of the request.
4. Role-restricted endpoints additionally use `@require_role("professor")`.
5. Roles: `student`, `professor`, `tenant_admin` (admin scoped to one tenant), `superadmin` (platform-wide).

---

## AI Features

### Exercise Generation
1. Professor uploads a PDF (or DOCX, CSV, IPYNB, TXT) chapter.
2. `services/content_extractor.py` extracts plain text (PyPDF2 / python-docx / csv / json).
3. `services/exercise_generator.py` calls Gemini REST API with the extracted text + a system prompt.
4. Gemini returns a JSON array of exercises (title, description, difficulty, solution_code, function_name, test_cases, language).
5. Exercises are stored in `class_exercises`.

### AI Chat (`/api/ai/chat`)
- Proxies messages to Gemini with conversation history.
- Rate-limited: 20/min + 100/hr per user.
- Payload capped: 50 KB body, 100 messages max before forwarding.

---

## Frontend Architecture

AnalytIQ is a **server-rendered Jinja2 application** with vanilla-JS
progressive enhancement — no SPA framework and no client-side build step.
Flask's catch-all (`core/factory.py` → `register_frontend_routes` →
`serve_frontend`) maps each non-API path to a `.html` Jinja2 template
(falling back to `index.html`), and serves on-disk static assets directly.

| Pattern | Details |
|---|---|
| Auth | `currentUser` object + JWT in `localStorage` |
| API calls | `authFetch()` in `static/js/api-helper.js` wraps `fetch()` + JWT header; handles 401 expiry |
| UI helpers | `window.uiStates` (ui-states.js): `showLoading`, `showEmpty`, `showError` |
| Code editor | `<textarea>` with custom line numbers and syntax highlighting |
| Autosave | 500ms debounced `localStorage` draft, keyed by exercise ID |

---

## Background Tasks (Celery)

- **Broker / result backend:** Redis.
- **Tasks:** PDF text extraction, exercise generation, email sending, quality
  scoring, LTI session cleanup.
- **Retry strategy:** Each task retries with exponential backoff on any
  exception. On final failure (`MaxRetriesExceededError`), the task returns
  `{"success": False, "error": ...}`. See ADR-004.
- **Status polling:** `GET /api/tasks/<task_id>` returns `{state, result}`.
- **Monitoring:** Flower UI available at `:5555` (`make flower` locally; see
  `docker-compose.yml`).
- `FEATURE_ASYNC_TASKS=False` disables Celery (tasks run synchronously in CI).

---

## Deployment

- **Platform:** Render (Python web service + background worker process).
- **Web process:** `gunicorn -c gunicorn.conf.py app:app`
- **Worker process:** `celery -A workers.celery_app.celery_app worker --loglevel=info --concurrency=2`
- **Environment:** All secrets in Render env vars (see `config.py` for the full list).
- **Auto-deploy:** GitHub push to `main` → Render rebuild.

---

## CI/CD (GitHub Actions)

Three jobs on every push/PR to `main` or `develop`:

1. **test** — spins up Postgres 14 + Redis 7, installs Python deps, then runs
   flake8 + black check + mypy + pytest with coverage.
2. **security-scan** — Bandit static analysis (`-ll` severity filter), uploads
   `bandit-report.json` artifact.
3. **deploy-notification** — logs "ready for Render" on successful `main` push.

Integration tests in `tests/integration/` require `DATABASE_URL` to be set;
they are skipped in CI unless the workflow provides a real Postgres URL.

---

## Key Design Decisions

| Decision                              | Rationale                                                       |
|---------------------------------------|-----------------------------------------------------------------|
| Application Factory (`core/factory.py`) | Each startup concern is independently readable and testable; eliminates circular imports |
| Config centralization (`config.py`)   | Single source of truth; `config_security_warnings()` logs non-fatal warnings at startup (`core/factory.py:87`); `validate_config()` is defined but not called by app code (tests only — see `docs/SECURITY.md` §1); test patches are stable |
| Monolith → 12+ Blueprints             | Per-domain ownership without micro-service overhead             |
| Repository layer (no ORM)             | Fine-grained SQL control; avoids N+1 and ORM magic              |
| `core/` / `services/` / `workers/`   | Clear import direction: blueprints → repositories → DB; services stay framework-free |
| ThreadedConnectionPool                | Reuse connections across requests without per-request connect overhead |
| JWT over sessions                     | Stateless; works well with Render's ephemeral filesystem        |
| Celery exponential-backoff retry      | Transient network/API failures recover automatically; see ADR-004 |
| Gemini for AI                         | Generous free tier; structured JSON output; single SDK          |
| Savepoint-based integration tests     | Full isolation without truncating tables between tests          |

---

## Architecture Decision Records

Key decisions are documented in `docs/adr/`:

| ADR | Decision |
|-----|---------|
| [ADR-001](adr/001-application-factory.md) | Flask Application Factory pattern |
| [ADR-002](adr/002-config-centralization.md) | Centralize all config in `config.py` |
| [ADR-003](adr/003-react-typescript-frontend.md) | React + TypeScript strangler-fig migration (**superseded** — React removed) |
| [ADR-004](adr/004-celery-retry-strategy.md) | Celery task retry strategy |
