# AnalytIQ — Architecture Snapshot

> Generated: 2026-02-17  
> Data analytics learning platform (LMS-style): professors manage classes/chapters/exercises; students practice and use an AI code assistant.

---

## 1. Frontend Stack

| Item | Details |
|------|--------|
| **Framework** | **Vanilla JavaScript** — no React, Next.js, or Vite. Multi-page app with plain HTML + JS. |
| **Build tool** | None — no bundler. Static assets (HTML, CSS, JS) are served as-is. |
| **Package manager** | None — no `package.json`; no npm/yarn/pnpm. |
| **Deployment** | **Same process as backend.** The Flask app serves both the API and static files. On Render, the single **web** service serves `/` and `/<path>` (HTML/JS/CSS) and `/api/*`. There is no separate static site (e.g. Render Static Site or Vercel) in this repo. |
| **API base URL** | Set in `js/api-helper.js`: `window.API_BASE_URL` is `http://localhost:5001/api` when host is localhost/127.0.0.1 or file, else `https://analytiq-qbfr.onrender.com/api` (hardcoded production URL). |

### Frontend structure

- **HTML (15 files):** `index.html`, `login.html`, `reset-password.html`, `profile.html`, `professor-dashboard.html`, `professor-class.html`, `student-classes.html`, `student-class.html`, `chapter-view.html`, `upload-assistant.html`, `resources.html`, `practice-playground.html`, `modules.html`, `code-assistant.html`, `contact.html`.
- **JS (14 files under `js/`):** `api-helper.js` (API base URL, auth headers, cache), `auth.js` (AuthManager, JWT in localStorage), `navigation.js`, `home-animation.js`, `professor-dashboard.js`, `professor-class.js`, `student-classes.js`, `student-class.js`, `upload-assistant.js`, `profile.js`, `contact.js`, `code-assistant.js`, `ai-agent.js`, `exercises-database.js`.
- **CSS:** `css/styles.css` (single main stylesheet).
- **Load order:** HTML files include `js/api-helper.js` first, then page-specific JS; order is documented in TASKS.md.

### Frontend environment variables

The frontend does **not** use a `.env` or build-time env. It relies on:

- **Runtime:** `window.location.origin` and `window.location.hostname` to decide API base (see `api-helper.js` and `auth.js`). Production API URL is hardcoded in `api-helper.js` as `https://analytiq-qbfr.onrender.com/api`.

---

## 2. Backend Stack

| Item | Details |
|------|--------|
| **Language** | **Python 3.9** (per CI). |
| **Framework** | **Flask 3.0.0** |
| **Entry point** | **`app.py`** — creates Flask app, loads `.env` via `python-dotenv`, registers blueprints, serves `/` and static catch-all. Production: **`gunicorn -c gunicorn.conf.py app:app`**. |
| **WSGI server** | **Gunicorn** — config in `gunicorn.conf.py`: `bind = "0.0.0.0:10000"`, `workers = 4`, `timeout = 300`, `worker_class = "sync"`, `max_requests = 1000`. |

### Dependencies (from `requirements.txt`)

| Package | Purpose |
|---------|--------|
| Flask, Flask-Cors | Web app, CORS |
| psycopg2-binary | PostgreSQL driver |
| python-dotenv | Env from `.env` |
| gunicorn | Production WSGI |
| google-generativeai | Gemini AI (also used via REST in `blueprints/ai.py`) |
| PyPDF2 | PDF text extraction |
| Flask-Mail | Email (password reset, etc.) |
| Flask-WTF, bcrypt, PyJWT | CSRF, password hashing, JWT |
| Flask-Limiter | Rate limiting (Redis or memory) |
| flask-swagger-ui, apispec | API docs at `/api/docs` |
| celery, redis | Async tasks, broker/backend |
| supabase | Storage client (PDF bucket) |
| python-json-logger | Structured logging |
| sentry-sdk[flask] | Error/performance monitoring |

### Blueprints (routes)

- **`blueprints/health`** — `/api/health`, `/api/health/detail`
- **`blueprints/ai`** — `POST /api/ai/chat` (Gemini proxy)
- **`blueprints/auth`** — signin, signup, forgot-password, reset-password, JWT
- **`blueprints/users`** — profile, preferences, conversations, code assistant, practice progress
- **`blueprints/chapters`** — chapter CRUD, PDF upload, extract text, generate exercises
- **`blueprints/exercises`** — exercise CRUD, leaderboards, progress
- **`blueprints.classes`** — class CRUD, enrollments, resources

All API routes are also exposed under **`/api/v1/`** via `register_api_v1_aliases()` in `app.py`.

### Deployment on Render

- **`render.yaml`** defines:
  - **Web service** `analytiq`: `env: python`, `buildCommand: pip install -r requirements.txt`, `startCommand: gunicorn -c gunicorn.conf.py app:app`, `healthCheckPath: /api/health`, `FLASK_ENV=production`.
  - **Worker** `analytiq-worker`: same build, `startCommand: celery -A celery_app.celery_app worker --loglevel=info --concurrency=2`, `FLASK_ENV=production`.
- No cron service in this repo; background work is via **Celery worker** only.

### Background job system

- **Celery** — app in `celery_app.py` (broker/backend: `REDIS_URL`). Tasks live in **`tasks.py`**:
  - `process_pdf_and_extract_text` — PDF → text (queue: `pdf_processing`)
  - `generate_exercises_async` — AI exercise generation (queue: `ai_tasks`)
  - `send_email_async` — email (queue: `emails`)
- **Base class:** `DatabaseTask` in `tasks.py` with DB connection handling and `on_failure` logging.
- **Feature flag:** `FEATURE_ASYNC_TASKS` (default `False`); when False, PDF/exercise work can be done synchronously in request handlers.

---

## 3. Database and Storage

### Database: PostgreSQL (Supabase)

- **Connection:** Backend uses **`DATABASE_URL`** (PostgreSQL connection string). Supabase is used as the Postgres host; connection is via **psycopg2** and a **threaded connection pool** in **`db.py`** (min/max conn from `config.DB_POOL_*`, timeouts, `sslmode=require`). No Supabase client for DB — only for storage.
- **Pool:** `db.get_db_connection()` (uses Flask `g`), `close_db_connection` in teardown.

### Supabase usage

| Area | Usage |
|------|--------|
| **Auth** | **Not used.** App uses its own auth: JWT issued after signin, passwords hashed with bcrypt, stored in `users` table. |
| **Database** | **Yes** — Supabase provides Postgres. Tables live in `public`; backend connects with `DATABASE_URL` (Pooler-compatible). |
| **Storage** | **Yes** — **`supabase_storage.py`** uses Supabase Python client (`SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_BUCKET`). Functions: `upload_pdf`, `get_pdf_url` (signed), `delete_pdf`, `migrate_pdf_from_db`, `storage_health_check`. Bucket default: `pdfs`. |
| **Edge Functions** | None detected in this repo. |

### Tables (public schema, from Supabase MCP + scripts/repos)

| Table | Purpose |
|-------|--------|
| **users** | id, user_id (UUID), name, email, password_hash, role, created_at, updated_at |
| **user_profiles** | user_id, full_name, bio, profile_picture |
| **user_settings** | user_id, email_notifications, dark_mode |
| **user_preferences** | user_id, current_language, gemini_model, ai_provider |
| **classes** | class_id, professor_id, name, description, archived |
| **class_enrollments** | class_id, student_id, enrolled_at |
| **class_chapters** | chapter_id, class_id, title, description, chapter_number, pdf_url, pdf_filename, extracted_content, pdf_data (bytea), etc. |
| **class_exercises** | exercise_id, chapter_id, class_id, title, description, difficulty, solution_code, exercise_number, etc. |
| **class_resources** | resource_id, class_id, user_id, title, description, resource_type, resource_url, file_data, filename |
| **conversations** | conversation_id, user_id, title, archived, deleted |
| **conversation_messages** | conversation_id, role, content, message_order |
| **ai_agent_digest** | user_id, goal, constraints, decisions, current_state, open_questions |
| **ai_agent_memory** | user_id, memory_item |
| **practice_progress** | user_id, exercise_id, class_id, class_exercise_id, best_score, total_attempts, completed, etc. |
| **exercise_attempts** | user_id, exercise_id, score, accuracy, time_spent, attempt_number |
| **password_resets** | email, token, expires_at |
| **contact_submissions** | user_id, name, email, subject, message, status |

RLS is enabled on these tables; the app uses a single DB user (service role) via `DATABASE_URL`.

### Repositories (data access)

- **`repositories/class_repository.py`** — classes, enrollments, chapters count, resources, leaderboards, student progress.
- **`repositories/chapter_repository.py`** — class_chapters, class_exercises (CRUD, ordering).
- **`repositories/exercise_repository.py`** — class_exercises, practice_progress, leaderboards.
- **`repositories/user_repository.py`** — users, user_profiles, user_settings, conversations, conversation_messages, ai_agent_*, user_preferences, practice_progress, exercise_attempts.
- **`repositories/auth_repository.py`** — users (by email), signup inserts, password reset (password_resets).

Blueprints call repository functions with `get_db_connection()`; no ORM.

---

## 4. External Services

| Service | Usage |
|---------|--------|
| **Sentry** | `sentry-sdk` + Flask/Redis/Celery integrations in **`sentry_config.py`**. Init from **`SENTRY_DSN`**; release from **`RENDER_GIT_COMMIT`**; env from **`FLASK_ENV`**. PII filtered in `before_send`. |
| **Google Gemini** | **REST** in `blueprints/ai.py`: `generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`. Key from **`GEMINI_API_KEY`**. Also **google-generativeai** in **`python/exercise_generator.py`** for exercise generation. Models: gemini-2.5-flash, gemini-2.5-pro, etc. |
| **Email (SMTP)** | **Flask-Mail** in **`extensions.py`** and **`blueprints/auth.py`** (e.g. password reset). Env: **MAIL_SERVER**, **MAIL_PORT**, **MAIL_USE_TLS**, **MAIL_USERNAME**, **MAIL_PASSWORD**, **MAIL_DEFAULT_SENDER**, **MAIL_SENDER_NAME**, **FRONTEND_URL** (for reset links). |
| **File processing** | **PyPDF2** in **`python/pdf_processor.py`** (`extract_text_from_pdf_bytes`). No other file-type libraries in use for parsing. |
| **Redis** | Rate limiting (Flask-Limiter), Celery broker/result backend, optional **cache** (`cache.py`, feature-flagged **FEATURE_CACHING**). |

---

## 5. Deployment Configuration

### Render

- **File:** **`render.yaml`**
  - **Web:** `analytiq`, health check `/api/health`.
  - **Worker:** `analytiq-worker` (Celery).
  - Env vars in YAML: only `FLASK_ENV=production`; all others (e.g. `DATABASE_URL`, `REDIS_URL`, `GEMINI_API_KEY`, `SUPABASE_*`, `SENTRY_DSN`) are expected to be set in Render dashboard or environment.

### GitHub Actions

- **File:** **`.github/workflows/ci.yml`**
  - **Triggers:** push to `main`/`develop`, PRs to `main`.
  - **Jobs:**
    - **test:** Ubuntu, Postgres 14 + Redis 7 services; Python 3.9; pip cache; install `requirements.txt`; flake8, black, mypy (continue-on-error); pytest with coverage; Codecov upload.
    - **security-scan:** bandit, upload artifact.
    - **deploy-notification:** on push to `main` after test + security-scan; echoes ready for Render deploy (Render auto-deploys from `main`).

### Environment variables referenced in code

Consolidated from **`config.py`**, **`app.py`**, **`sentry_config.py`**, **`blueprints/auth.py`**, **`.env.example`**, and **`scripts/verify_deployment.py`**:

| Variable | Used by | Notes |
|----------|--------|-------|
| **DATABASE_URL** | db, tasks, config | Required |
| **SECRET_KEY** | config, app | Required in prod |
| **JWT_SECRET_KEY**, **JWT_EXPIRY_HOURS** | config | JWT auth |
| **FLASK_ENV**, **FLASK_DEBUG**, **PORT**, **HOST** | app, config | Env/debug/port |
| **GEMINI_API_KEY**, **GEMINI_MODEL**, **GEMINI_TIMEOUT** | config, ai, chapters, exercise_generator | AI |
| **SUPABASE_URL**, **SUPABASE_KEY**, **SUPABASE_BUCKET** | config, supabase_storage | Storage |
| **REDIS_URL** | config, celery_app, app (limiter) | Redis |
| **CACHE_TTL**, **FEATURE_CACHING** | config, cache, health | Optional cache |
| **MAIL_***, **FRONTEND_URL**, **MAIL_SENDER_NAME** | config, auth blueprint | Email |
| **SENTRY_DSN** | sentry_config | Error monitoring |
| **RENDER_GIT_COMMIT** | sentry_config | Release tag |
| **CORS_ORIGINS**, **CORS_MAX_AGE** | config, app | CORS |
| **DB_POOL_MIN**, **DB_POOL_MAX**, **DB_CONNECTION_TIMEOUT**, **DB_STATEMENT_TIMEOUT** | config, db | Pool/timeouts |
| **RATE_LIMIT_*** | config, app | Limiter |
| **FEATURE_AI_EXERCISES**, **FEATURE_EMAIL**, **FEATURE_ANALYTICS**, **FEATURE_CSRF**, **FEATURE_ASYNC_TASKS** | config, app | Feature flags |
| **MAX_PDF_SIZE_MB**, **BCRYPT_ROUNDS**, **DEFAULT_PAGE_SIZE**, **MAX_PAGE_SIZE**, **HEALTH_CHECK_TIMEOUT**, **PW_RESET_EXPIRY_HOURS**, **LOG_LEVEL**, **LOG_FORMAT**, **CSRF_TIME_LIMIT** | config | Tuning/limits |

---

## 6. Overall Architecture Diagram (Text)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT (Browser)                                │
│  Vanilla JS (api-helper.js, auth.js, …) → localStorage (JWT, user)           │
│  HTML pages + css/styles.css                                                 │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │ HTTPS
                                    │ /api/* (JSON, Bearer JWT)
                                    │ /, /* (HTML/JS/CSS)
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        RENDER WEB SERVICE (analytiq)                          │
│  Gunicorn → Flask (app.py)                                                   │
│  Blueprints: health | ai | auth | users | chapters | exercises | classes     │
│  Middleware: CORS, rate limit (Redis), CSRF (optional), Sentry               │
│  Static: serve index.html + catch-all for frontend files                      │
└───┬─────────────┬─────────────┬─────────────┬─────────────┬─────────────────┘
    │             │             │             │             │
    │             │             │             │             │
    ▼             ▼             ▼             ▼             ▼
┌────────┐  ┌──────────┐  ┌─────────┐  ┌──────────┐  ┌─────────────┐
│ Redis  │  │ Postgres │  │ Supabase│  │ Gemini   │  │ SMTP        │
│        │  │ (Supabase│  │ Storage │  │ API      │  │ (e.g. Gmail)│
│ Limiter│  │ Postgres)│  │ (pdfs   │  │          │  │             │
│ Celery │  │ db.py    │  │ bucket) │  │ AI chat  │  │ Password    │
│ broker │  │ pool     │  │ upload  │  │ exercises│  │ reset       │
│ Cache  │  │ repos    │  │ signed  │  │          │  │             │
└───┬────┘  └──────────┘  └─────────┘  └──────────┘  └─────────────┘
    │
    │  queues: pdf_processing | ai_tasks | emails
    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     RENDER WORKER (analytiq-worker)                           │
│  Celery worker (celery_app.celery_app) — tasks.py                            │
│  process_pdf_and_extract_text | generate_exercises_async | send_email_async  │
│  DatabaseTask: own DB connection pool for worker                             │
└───────────────────────────────────┬───────────────────────────────────────────┘
                                    │
                                    ▼
                            Same Postgres (DATABASE_URL)
                            Same Redis (REDIS_URL)

┌─────────────────────────────────────────────────────────────────────────────┐
│  Sentry (SENTRY_DSN): receives errors + performance from Flask & Celery      │
│  Release = RENDER_GIT_COMMIT                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Summary:** One Render web service serves the full stack (API + frontend). Postgres and storage are Supabase; auth is app-owned (JWT + bcrypt). Redis backs rate limiting, Celery, and optional cache. Gemini powers AI chat and exercise generation. Email is SMTP; monitoring is Sentry.
