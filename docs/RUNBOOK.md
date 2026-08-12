# AnalytIQ Operations Runbook

Last updated: 2026-08-11
Owner: Adam El Harouchi (solo founder — see "What only Adam can do today" at the bottom)

**Purpose:** AnalytIQ is currently operable by exactly one person. This document exists so a
competent engineer who has never seen this codebase can deploy, diagnose, and restore the
platform if Adam is unreachable. Read it once end-to-end before you need it under pressure.

**How to read the markers in this document:**
- **[VERIFIED — in repo config]**: derived directly from files in this repository (`render.yaml`,
  `config.py`, etc.). Trustworthy as a description of what is *configured*, though config can still
  diverge from what's actually live in Render's dashboard.
- **[UNVERIFIED — never tested]**: derived from config/code but the procedure itself has not been
  executed by anyone, or the outcome has not been confirmed. Treat these as a best-effort starting
  point, not a guarantee. If you execute one of these successfully, update this doc and remove the
  marker.
- **[UNKNOWN — not in repo]**: could not be determined from the codebase at all. Do not guess;
  find out before you need it (see Blockers in the accompanying session report).

---

## 1. What the system is

AnalytIQ is a Flask web application: professors create programming-exercise classes, students
practice code in a browser playground, and Gemini generates/grades exercises from uploaded course
material. **[VERIFIED — in repo config, `docs/ARCHITECTURE.md`]**

### Components and where they run

| Component | What it does | Where it runs |
|---|---|---|
| **Web service** (`analytiq`) | Flask app served by Gunicorn (`gunicorn -c gunicorn.conf.py app:app`, 4 sync workers, port 10000) | Render web service |
| **Worker service** (`analytiq-worker`) | Celery worker (`celery -A workers.celery_app.celery_app worker --loglevel=info --concurrency=2`) — async PDF text extraction, AI exercise generation, email sending, quality scoring, LTI session cleanup | Render background worker service |
| **PostgreSQL** | System of record: users, classes, chapters, exercises, progress, audit log, etc. | Supabase (managed Postgres), reached via `DATABASE_URL` |
| **Redis** | Celery broker/result backend, Flask-Limiter rate-limit storage, response caching | Render Managed Redis, reached via `REDIS_URL` |
| **Supabase Storage** | PDF chapter file storage (S3-compatible bucket, default `pdfs`) | Supabase, reached via `SUPABASE_URL`/`SUPABASE_KEY` |
| **Gemini API** | Exercise generation from PDF text, AI chat | Google, reached via `GEMINI_API_KEY` |
| **Sentry** | Error monitoring (Flask + Redis + Celery integrations) | Sentry SaaS, reached via `SENTRY_DSN` |
| **Resend / Gmail SMTP** | Transactional email (password reset, notifications) | Resend API (`RESEND_API_KEY`) and/or Gmail SMTP (`MAIL_*`) — both are wired in config |
| **Cloudflare** | CDN/proxy in front of the Render web service, caches `/static/*`, bypasses cache on `/api/*` | Cloudflare (one-time dashboard setup, not code-managed) |

Source for the table above: `render.yaml`, `Procfile`, `docs/ARCHITECTURE.md`, `config.py`.
**[VERIFIED — in repo config]**

### External dependencies the platform cannot live without

1. **PostgreSQL / Supabase** — hard dependency. `config.validate_config()` refuses to start
   without `DATABASE_URL`. If Supabase is down, the app is down (health check fails, see §5).
2. **Gemini API** — soft-critical. Exercise generation and AI chat fail without it, but the rest
   of the app (login, playground, existing exercises) keeps working. `blueprints/health.py` marks
   this non-critical.
3. **Redis** — soft-critical in current config. Rate limiting falls back to in-memory if Redis is
   unavailable in dev; in production `FEATURE_CACHING`/`FEATURE_ASYNC_TASKS` depend on it, and
   Celery cannot dispatch tasks without it, so PDF processing/exercise generation/email queue up
   or fail while Redis is down.
4. **Render** — hosting platform for both processes; no independent host exists today.
5. **Cloudflare** (if configured) — sits in front of the origin; `ORIGIN_VERIFY_SECRET`, when set,
   makes the origin *reject* direct traffic that skips Cloudflare, so Cloudflare being
   misconfigured can itself cause an outage. **[VERIFIED — in repo config, `config.py` lines
   around `ORIGIN_VERIFY_SECRET`, `core/middleware.py::check_origin_verify`]**

### Repository map (for orientation)

See `docs/ARCHITECTURE.md` for the full layout. The short version: `app.py` (entrypoint) →
`core/factory.py` (startup sequence) → `blueprints/` (routes) → `repositories/` (raw SQL) →
Postgres. `services/` holds business logic (Gemini calls, PDF extraction, code execution).
`workers/` holds the Celery app and task definitions. `migrations/` holds numbered idempotent SQL
files applied by `db_migrate.py`.

---

## 2. Deploy

### How a change reaches production

1. Push/merge to `main` on GitHub (`adamelharouchi5-blip/AnalytIQ`, per the Docker image label
   `org.opencontainers.image.source` and the current git remote owner).
2. GitHub Actions (`.github/workflows/ci.yml`) runs on the push: `test` job (flake8, black
   --check, mypy [non-gating], pytest+coverage against ephemeral Postgres 14 + Redis 7) and
   `security-scan` job (Bandit gated at MEDIUM+ severity, pip-audit gated on any known CVE in
   `requirements.txt`). A `deploy-notification` job just logs a message — **it does not trigger
   the deploy itself; Render's own GitHub integration does.** **[VERIFIED — in repo config,
   `.github/workflows/ci.yml`]**
3. Render's auto-deploy (configured in the Render dashboard, not in this repo) picks up the new
   commit on `main` and:
   a. Runs `buildCommand: pip install -r requirements.txt` for both the `analytiq` web service and
      the `analytiq-worker` service.
   b. Runs `preDeployCommand: python db_migrate.py` **once**, before the new version goes live.
      This applies any new files under `migrations/` and exits non-zero on a failed migration,
      which blocks the deploy rather than shipping code against a schema that never applied.
   c. Starts the new web/worker processes with the `startCommand`s in `render.yaml`.
   **[VERIFIED — in repo config, `render.yaml`]**

   Note: `config.RUN_MIGRATIONS_ON_BOOT` (default `True`) is a legacy path where every worker
   also tries to apply migrations at startup under a Postgres advisory lock
   (`db_migrate.run_migrations`), which is safe to run redundantly but is meant to be turned off
   (`RUN_MIGRATIONS_ON_BOOT=false`) once the `preDeployCommand` step above is confirmed working —
   check the current value in the Render dashboard; this repo cannot tell you which mode is
   actually active in production. **[UNKNOWN — not in repo: current value of
   `RUN_MIGRATIONS_ON_BOOT` in the live Render env]**

### How to tell whether a deploy worked

- **Render dashboard** shows build/deploy logs and a pass/fail status per deploy. **[UNVERIFIED —
  never tested by this agent; standard Render behavior but not something this repo can confirm]**
- **Health check:** Render polls `GET /api/health` (`healthCheckPath` in `render.yaml`). It
  returns `{"status": "healthy"}` (200) or `{"status": "degraded"}` (503). Only the **database**
  check is currently treated as critical for the overall status; Gemini/email/cache/storage are
  reported but do not flip the top-level status to unhealthy. **[VERIFIED — in repo config,
  `blueprints/health.py::_run_health_checks`]**
- **Authenticated detail view:** `GET /api/health/detail` (requires a valid Bearer token) returns
  the full per-service breakdown — use this to see *which* dependency is degraded, not just that
  something is. **[VERIFIED — in repo config, `blueprints/health.py`]**
- **Sentry:** a spike in new issues right after a deploy is release-tagged
  (`release=analytiq@<7-char git sha>` from `RENDER_GIT_COMMIT`), so you can filter Sentry by the
  release that just shipped. **[VERIFIED — in repo config, `core/sentry.py`]**
- **Manual smoke test:** sign in, open a class, open the playground, run a trivial `print(2+2)`
  exercise. **[UNVERIFIED — never tested as a formal post-deploy checklist by this agent; this is
  a recommendation, not a documented existing procedure]**

### Rollback

- **Render's dashboard supports rolling back to a previous successful deploy** (standard Render
  platform feature — redeploy an earlier build). This repo has no rollback script or documented
  click-path for this project specifically. **[UNVERIFIED — never tested; confirm the exact
  dashboard steps once, in advance, so you are not learning them during an incident]**
- **Database migrations do not auto-rollback.** `db_migrate.py` only applies forward migrations
  (tracked in the `schema_migrations` table by filename) and has no `down`/revert mechanism. If a
  bad migration shipped, you must hand-write and apply a corrective migration, or restore the
  database from backup (§3) — there is no automated "undo." **[VERIFIED — in repo config,
  `db_migrate.py`; the absence of a revert path is a code-reading finding, not a guess]**
- **Fastest safe rollback for a bad code change that did NOT ship a schema migration:** redeploy
  the previous commit via Render. **[UNVERIFIED — never tested]**
- **If the bad change DID ship a migration:** rolling back the code alone is not sufficient if the
  new code depends on the new schema — coordinate code rollback and schema state together. This is
  a real gap: there is no tested procedure for this today. **[UNVERIFIED — never tested; treat as
  a genuine risk, not just an unverified formality]**

---

## 3. Restore (database backup/restore)

**This is the most important section and the one this agent could NOT fully substantiate from the
repository. Do not trust it blindly — verify before you need it.**

What the repo says:
- `docs/PROJECT_OVERVIEW.md`: "**Database Host:** Supabase (Managed PostgreSQL). It handles
  backups, replication, and provides a powerful SQL editor." **[VERIFIED — this sentence exists in
  the repo]** — but it is a one-line marketing-style description, not an operational procedure.
- Nothing else in the repository (`docs/`, `scripts/`, `migrations/`, CI config) references
  `pg_dump`, `pg_restore`, point-in-time recovery, a backup schedule, a backup retention window, or
  a tested restore procedure. There is no backup/restore script in `scripts/`.

What this means operationally:
- **[UNKNOWN — not in repo]** Which Supabase plan/tier AnalytIQ is on, and therefore what backup
  capability is actually enabled (Supabase's free/Pro/Team tiers differ significantly in backup
  frequency, retention, and whether point-in-time recovery is offered at all).
- **[UNKNOWN — not in repo]** Whether anyone has ever performed a test restore.
- **[UNKNOWN — not in repo]** The RPO/RTO (how much data could be lost, how long a restore would
  take) if Supabase's backups are relied on as-is.
- **[UNKNOWN — not in repo]** Whether there is any additional backup (e.g. a scheduled `pg_dump`
  to external storage) outside of whatever Supabase does automatically.

**This is flagged as a Blocker in the accompanying session report — Adam needs to log into the
Supabase dashboard (Project Settings → Database → Backups, or equivalent for the current Supabase
UI) and confirm: (a) the plan tier, (b) what backup type is enabled and its retention window, (c)
whether point-in-time recovery is available, and (d) how to actually trigger a restore from the
dashboard. Until that's done, do not assume backups exist beyond whatever Supabase's default for
the account's tier provides.**

What IS substantiated: the schema itself is fully reproducible from source. `migrations/*.sql`
(currently `001`–`013`, see `migrations/` directory) plus `db_migrate.py` can rebuild an empty
database's schema from scratch by running `python3 db_migrate.py` against a fresh `DATABASE_URL`
(each file is required to be idempotent — `IF NOT EXISTS` / `ON CONFLICT DO NOTHING`). **This
recreates structure, not data.** **[VERIFIED — in repo config, `db_migrate.py`,
`migrations/*.sql`]**

Local dev database (for reference — NOT production): `docker-compose.yml` defines a throwaway
`postgres:14-alpine` container with a named Docker volume (`postgres_data`). This has no relation
to the production Supabase restore path and is mentioned only so you don't confuse the two.
**[VERIFIED — in repo config, `docker-compose.yml`]**

### PDF file storage restore

Chapter PDFs live in two possible places at once: `class_chapters.pdf_data` (a BYTEA column in
Postgres — so it IS covered by whatever Postgres backup exists) and/or Supabase Storage (the `pdfs`
bucket, S3-compatible). `docs/CODEBASE_AUDIT_MARCH_2026.md` notes both paths are active in
parallel, not one replacing the other. Supabase Storage's own backup/versioning behavior is
**[UNKNOWN — not in repo]** — check the Supabase dashboard for the storage bucket's settings
separately from the database backup settings.

---

## 4. Key / secret rotation (conceptual — names and locations only)

**No credential value is reproduced anywhere in this document.** All secrets are configured as
environment variables in the Render dashboard (per-service, for `analytiq` and
`analytiq-worker`); local development uses a `.env` file (never committed — see
`.gitignore`/`.env.example`). The full current variable name list, with which are required vs.
optional, is `.env.example` and `docs/RENDER_ENV_CHECKLIST.md`. **[VERIFIED — in repo config]**

| Secret (env var name) | Used for | Where configured | Rotation mechanism |
|---|---|---|---|
| `DATABASE_URL` | Postgres connection string (Supabase) | Render env, both services | Rotate in Supabase dashboard, then update the Render env var on both services and restart. **[UNVERIFIED — never tested]** |
| `SECRET_KEY` | Flask session signing; JWT fallback if `JWT_SECRET_KEY` unset | Render env | Generate via `python -c "import secrets; print(secrets.token_hex(32))"` (documented in `.env.example`). Rotating invalidates all active sessions/JWTs signed with the old key unless `JWT_SECRET_KEY` is set separately. **[UNVERIFIED — never tested]** |
| `JWT_SECRET_KEY` | JWT signing (falls back to `SECRET_KEY` if unset) | Render env | `config_security_warnings()` in `config.py` already flags production if this is not set distinct from `SECRET_KEY` — setting a distinct value is recommended so rotating one does not force-rotate the other. Rotating invalidates all outstanding access/refresh tokens (users must re-sign-in). **[UNVERIFIED — never tested]** |
| `GEMINI_API_KEY` | Google Gemini API access | Render env | Regenerate in Google AI Studio / Cloud console, update Render env var, restart. **[UNVERIFIED — never tested]** |
| `SUPABASE_URL` / `SUPABASE_KEY` | DB host reference + Storage (service-role key) | Render env | Rotate the service-role key in Supabase dashboard; update Render env var. This key is high-privilege (bypasses row-level security) — treat rotation as urgent if ever suspected leaked. **[UNVERIFIED — never tested]** |
| `REDIS_URL` | Celery broker/backend, rate-limit storage, cache | Render env (Render Managed Redis) | Managed by Render; if the Redis instance is recycled/rotated, update the env var on both services. **[UNVERIFIED — never tested]** |
| `SENTRY_DSN` | Error reporting endpoint | Render env | Not a secret in the traditional sense (DSNs are meant to be embeddable), but can be regenerated in Sentry project settings if needed. |
| `MAIL_USERNAME` / `MAIL_PASSWORD` | Gmail SMTP for transactional email | Render env | `MAIL_PASSWORD` is documented in `.env.example` as a Gmail **app password**, not the account password — regenerate in the Google Account's App Passwords settings, update Render env var. |
| `RESEND_API_KEY` | Resend transactional email API | Render env | Regenerate in Resend dashboard, update Render env var. |
| `ORIGIN_VERIFY_SECRET` | Shared secret validating Cloudflare→origin traffic | Render env + Cloudflare Transform Rule | Must be changed in **both** places simultaneously (Render env var and the Cloudflare Transform Rule header value) or the origin starts rejecting all real traffic. `.env.example` suggests `openssl rand -hex 32`. **[UNVERIFIED — never tested; this is the one rotation most likely to cause a self-inflicted outage if done out of sync]** |
| `SSO_ENCRYPTION_KEY` | Fernet key encrypting stored SSO client secrets | Render env | Rotating **invalidates all stored SSO provider client secrets** — they must be re-entered in the tenant admin UI after rotation. Only relevant if `FEATURE_SSO=True`. |
| `LTI_PRIVATE_KEY` / `LTI_PUBLIC_KEY` / `LTI_KEY_ID` | LTI 1.3 RSA key pair for LMS integration signing | Render env | Regenerate with `python3 scripts/generate_lti_keys.py`; bump `LTI_KEY_ID` when rotating so JWKS consumers (Canvas etc.) see a new key identifier, not a silent swap. |
| `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` | GitHub OAuth for portfolio sync | Render env | Regenerate in the GitHub OAuth App settings, update Render env var. |

General rotation shape for any of the above (derived from how `config.py` loads env vars — every
value is read once via `os.getenv()` at import time, no live-reload):
1. Generate/obtain the new value in the source system (Supabase, Google, Sentry, Resend, GitHub,
   etc.) — **never via this repo, never printed to a terminal that gets logged.**
2. Update the corresponding Render env var (dashboard: Service → Environment).
3. Trigger a restart/redeploy — `config.py` reads env vars once at process start, so a running
   Gunicorn/Celery worker will **not** pick up a changed env var without a restart.
4. Verify via `/api/health/detail` and Sentry that nothing broke.
**[UNVERIFIED — never tested end-to-end by this agent; this is the logical procedure implied by
how config is loaded, not a confirmed runbook.]**

---

## 5. On-call basics

### How to tell the platform is down

1. `GET https://www.myanalytiq.org/api/health` (or whichever domain is currently live — see the
   domain note at the end of this section) — 200 `{"status":"healthy"}` vs. 503
   `{"status":"degraded"}`. This is the same check Render uses to decide whether to keep routing
   traffic to a deploy. **[VERIFIED — in repo config, `render.yaml` `healthCheckPath`,
   `blueprints/health.py`]**
2. Render dashboard — service status, deploy status, and logs for both `analytiq` (web) and
   `analytiq-worker`.
3. Sentry — new/spiking issues, especially anything tagged with the current release.

### First three things to check, in order

1. **`GET /api/health/detail`** (needs a valid Bearer token — sign in first) to see which
   dependency is actually unhealthy: database, Gemini, email, cache, or storage. The **database**
   check is the only one that flips the top-level status; everything else degrades gracefully by
   design (`blueprints/health.py`). If database is unhealthy, this is a P0 — the whole app is
   unusable (every route goes through `get_db_connection()`).
2. **Render service logs** for both services — look for the specific exception. Gunicorn worker
   crashes, DB pool exhaustion (`ThreadedConnectionPool` max is `DB_POOL_MAX` per gunicorn
   *worker process*, default 5 in `config.py` but often overridden via env — 4 gunicorn workers ×
   pool max could exceed what Supabase's connection limit allows on a small plan), or a Celery
   worker stuck on a task (`task_time_limit=300`s / `task_soft_time_limit=240`s caps a single
   task, but a backlog can still build).
3. **Sentry** for the stack trace and release tag, to correlate "did this start right after a
   deploy" — if so, consider rollback (§2) before deep-debugging.

### Known-fragile areas

1. **Student code execution sandbox.** By default (`SANDBOX_USE_CONTAINER=False`), untrusted
   student code from the playground "Run" button and grading runs **on the same host process**
   as the web/worker, with only in-process defenses (an import blocklist that does NOT block
   `os`, so `os.system(...)` is a real escape; a read-only `open()` shim bypassable via
   `os.open`/`io.FileIO`; RLIMIT caps that don't apply on non-Linux). The "Run" path also keeps
   network access open (so `pd.read_csv(url)` works), which is an SSRF surface to internal
   services and cloud metadata endpoints. A container-based sandbox exists
   (`docker/sandbox.Dockerfile`, `services/container_runner.py`, flag
   `SANDBOX_USE_CONTAINER=true`) but is explicitly a **scaffold, default OFF**, and — critically —
   **Render's standard web/worker services cannot run Docker**, so this flag cannot simply be
   flipped on in the current hosting setup without a separate Docker-capable host. Full detail and
   a staging validation checklist: `docs/SANDBOX_CONTAINER.md`. **[VERIFIED — in repo config,
   `config.py` lines ~259–310, `docs/SANDBOX_CONTAINER.md`]**
2. **PDF content truncation before AI exercise generation.** `services/exercise_generator.py`
   hard-truncates extracted PDF text to `_TRUNCATION_LIMIT = 10,000` characters before sending it
   to Gemini, with **no chunking and no warning surfaced to the professor** — a dense/long PDF
   silently loses content past ~10k characters. This is a known, tracked bug (see
   `tests/unit/test_pdf_truncation_regression.py` and the referenced
   `reports/product-engineer/PDF_TRUNCATION_FIX_PLAN.md`), not a hypothetical risk. If a professor
   reports "the AI only generated exercises from part of my chapter," this is almost certainly why.
   **[VERIFIED — in repo config, `services/exercise_generator.py`,
   `tests/unit/test_pdf_truncation_regression.py`]**
3. **LLM provider (Gemini) dependency.** Exercise generation and AI chat both call the Gemini API
   directly (`services/exercise_generator.py`, `blueprints/ai.py`) with a 60-second timeout
   (`config.GEMINI_TIMEOUT`). If Gemini is slow or down, generation requests will time out or
   error; the health check correctly treats this as non-critical (rest of the app keeps working),
   but professors mid-upload will see failures. There is no fallback LLM provider.
4. **Database connection pool sizing under multiple Gunicorn workers.** `gunicorn.conf.py` runs 4
   sync workers, each initializing its own `ThreadedConnectionPool` (post-fork reset is handled
   correctly — see `post_fork` hook — so pools don't leak across forked workers, but each live
   worker still holds its own pool up to `DB_POOL_MAX_CONNECTIONS`). On a constrained Supabase
   connection limit, this is worth knowing about if you ever see "too many connections" errors.
   **[VERIFIED — in repo config, `gunicorn.conf.py`, `core/database.py`, `config.py`]**
5. **Domain naming is inconsistent across the repo.** `docs/ARCHITECTURE.md` states the live site
   is `https://www.myanalytiq.org`; `docs/RENDER_ENV_CHECKLIST.md`'s configured `CORS_ORIGINS`
   also uses `.org`; but `config.py` defaults `FRONTEND_URL` and `LTI_TOOL_URL` to
   `https://myanalytiq.com` (a `.com`, not `.org`), and `MAIL_DEFAULT_SENDER` defaults to
   `noreply@analytiq.com` (no "my" prefix, no "www"). These are just fallback defaults (real values
   come from Render env vars), but if SSO/LTI redirect URLs or CORS ever start failing after a
   deploy, check whether the actual configured domain matches what's live —
   **[UNKNOWN — not in repo: which domain(s) are actually registered/live and which env vars are
   currently set to what in Render]**.

---

## 6. What only Adam can do today (the actual bus-factor list)

This is the honest inventory of single points of failure — accounts, credentials, and knowledge
that exist in exactly one place: Adam's head or Adam's inbox. This is the actual deliverable of
this document; it is intentionally not softened.

**Accounts (only Adam has login/owner access, as far as this repo shows):**
- **GitHub** — repo owner account is `adamelharouchi5-blip` (per the current git remote and the
  Docker image label `org.opencontainers.image.source`). Nobody else can merge to `main`, manage
  GitHub Actions secrets, or approve/trigger anything at the source-control layer unless Adam adds
  a collaborator.
- **Render** — dashboard access controls env vars for both services, deploy history/rollback,
  and service logs. This is where every secret in §4 actually lives. **[UNKNOWN — not in repo:
  whether anyone besides Adam has Render dashboard access]**.
- **Supabase** — database + storage project owner. Controls backup settings (§3, currently
  unverified), connection strings, and the service-role key. **[UNKNOWN — not in repo: whether
  anyone besides Adam has Supabase dashboard access]**.
- **Cloudflare** (if in use) — DNS, cache rules, and the `X-Origin-Verify` Transform Rule that
  `ORIGIN_VERIFY_SECRET` depends on. **[UNKNOWN — not in repo: account ownership]**.
- **Google Cloud / AI Studio** (Gemini API key), **Sentry**, **Resend**, **Gmail** (SMTP
  account for `MAIL_USERNAME`), **GitHub OAuth App** (portfolio sync) — each is a separate
  external account referenced only by an env var name in this repo; ownership/access for each is
  **[UNKNOWN — not in repo]**.
- **Domain registrar** for whichever domain(s) are actually live (see the domain-inconsistency
  note in §5) — **[UNKNOWN — not in repo]**.

**Knowledge that exists only in Adam's head (not written down anywhere in this repo):**
- Which Supabase plan/tier is active and what backup guarantees it actually provides (§3 — this
  is the single biggest unresolved risk in this document).
- Whether `RUN_MIGRATIONS_ON_BOOT` is currently `True` or `False` in the live Render env, i.e.
  which of the two migration-application paths described in §2 is actually active.
- Current live values of every env var in §4 — this repo only has names and `.env.example`
  placeholder/documentation values, never real values.
- Whether anyone besides Adam has ever logged into Render, Supabase, Cloudflare, Sentry, Resend,
  or the Gemini/Google Cloud console for this project.
- Any informal operational habits (e.g., "I always check X before deploying," "the worker
  restarts itself if Y") that aren't captured in code or docs.

**What this means practically:** if Adam is unreachable, a capable engineer with this repo could
redeploy known-good code, read logs, and diagnose most application-level failures using this
document. They could **not**, without additional access being granted in advance:
rotate any secret, restore the database, change DNS/Cloudflare settings, or even confirm a backup
exists. **Closing that gap requires Adam to either grant a second person access to Render +
Supabase + Cloudflare (at minimum) now, or to leave sealed/escrowed credentials somewhere a
successor could reach in an emergency** — this document cannot substitute for that; it can only
make clear that the gap exists.

---

## Sources consulted while writing this document

`render.yaml`, `Procfile`, `gunicorn.conf.py`, `docker/sandbox.Dockerfile`, `docker-compose.yml`,
`Makefile`, `config.py`, `app.py`, `core/factory.py` (referenced, not fully read), `core/database.py`,
`core/storage.py`, `core/sentry.py`, `core/middleware.py`, `db_migrate.py`, `blueprints/health.py`,
`services/content_extractor.py`, `services/exercise_generator.py` (grep), `workers/celery_app.py`,
`.env.example`, `.github/workflows/ci.yml`, `docs/ARCHITECTURE.md`, `docs/RENDER_ENV_CHECKLIST.md`,
`docs/SANDBOX_CONTAINER.md`, `docs/SECURITY.md`, `docs/PROJECT_OVERVIEW.md`,
`docs/CODEBASE_AUDIT_MARCH_2026.md`, `migrations/` (directory listing),
`tests/unit/test_pdf_truncation_regression.py`.
