# AnalytIQ

**An AI-powered platform for teaching data analytics and programming.** A professor uploads a
course PDF; AnalytIQ turns it into auto-graded coding exercises, runs student submissions in a
sandbox, grades them on actual output, and reports back who is struggling.

Live at **[myanalytiq.org](https://www.myanalytiq.org)** · Deployed on Render · Python 3.11 / Flask

---

## Table of Contents

- [What problem this solves](#what-problem-this-solves)
- [How it works](#how-it-works)
- [Features by role](#features-by-role)
- [Architecture](#architecture)
- [Tech stack](#tech-stack)
- [Repository layout](#repository-layout)
- [Data model](#data-model)
- [Getting started](#getting-started)
- [Configuration](#configuration)
- [Testing](#testing)
- [Code quality and CI](#code-quality-and-ci)
- [Deployment](#deployment)
- [Security model](#security-model)
- [Operations](#operations)
- [Documentation](#documentation)
- [License](#license)

---

## What problem this solves

Teaching a programming or analytics course has a bottleneck that scales badly: **writing and
grading exercises**. Writing good practice problems for every chapter takes hours, and grading
them by hand takes longer — so students get less practice than they need, and feedback arrives
too late to be useful.

Existing autograders mostly compare submitted source code to a reference answer, which rewards
copying the expected text rather than solving the problem.

AnalytIQ attacks both ends:

- **Generation** — course material goes in, exercises come out, each with machine-checkable test
  cases. The professor reviews and edits rather than authoring from scratch.
- **Grading** — submissions are *executed* and judged on their actual output against those test
  cases. There is deliberately **no string-similarity or Levenshtein comparison** anywhere in
  the grading path.

It plugs into an institution's existing LMS over LTI 1.3, so students never create a separate
account and grades flow back to the gradebook automatically.

## How it works

The core loop, end to end:

```
  ┌────────────────┐
  │   PROFESSOR    │
  └────────┬───────┘
           │ 1. uploads a course PDF (chapter)
           ▼
  ┌──────────────────────────────────────────────────┐
  │ content_extractor  →  Supabase Storage           │
  │ pypdf text extraction, optional chunking         │
  │ (FEATURE_PDF_CHUNKING: 10k chars, 500 overlap)   │
  └────────┬─────────────────────────────────────────┘
           │ 2. extracted text
           ▼
  ┌──────────────────────────────────────────────────┐
  │ exercise_generator  →  Google Gemini             │
  │ returns exercises + test cases as structured JSON│
  │ logs exercise_generation_events (the flywheel)   │
  └────────┬─────────────────────────────────────────┘
           │ 3. exercises land in class_exercises
           ▼
  ┌────────────────┐
  │    STUDENT     │  arrives via LTI launch from Canvas/Moodle,
  └────────┬───────┘  or email + password, or tenant SSO
           │ 4. writes code in the browser
           ▼
  ┌──────────────────────────────────────────────────┐
  │ code_runner — sandboxed execution                │
  │ Python · R · JavaScript · SQL · Java             │
  │ subprocess isolation + RLIMIT_* + import blocks  │
  └────────┬─────────────────────────────────────────┘
           │ 5. output-based score (0-100)
           │    80 correctness · 20 code quality
           ▼
  ┌──────────────────────────────────────────────────┐
  │ exercise_progress + exercise_outcome_events      │
  └────────┬─────────────────────────────────────────┘
           │ 6a. analytics → professor dashboard
           │ 6b. grade passback → LMS gradebook (LTI AGS)
           ▼
  ┌──────────────────────────────────────────────────┐
  │ Data flywheel: outcomes feed exercise quality    │
  │ scoring, which informs future generation         │
  └──────────────────────────────────────────────────┘
```

**Grading schema** (`services/code_runner.py`):

| Component | Points | How it is computed |
|---|---|---|
| Correctness | 0–80 | `(tests_passed / tests_total) * 80`, weighted per test |
| Quality | 0–20 | 10 runs cleanly + 5 no hardcoded answers + 5 basic style |
| **Total** | **0–100** | |

**The data flywheel.** Every generation is recorded in `exercise_generation_events` and every
student attempt in `exercise_outcome_events`. Joining the two gives a per-exercise quality signal
— an exercise nobody passes is probably a bad exercise, not a hard one — surfaced to professors
and superadmins through `/api/flywheel/*`.

## Features by role

AnalytIQ has four roles. `tenant_admin` is a parallel administrative track, **not** a senior
professor: it has the same administrative capabilities as `superadmin` but scoped to a single
tenant.

| | student | professor | tenant_admin | superadmin |
|---|:--:|:--:|:--:|:--:|
| Solve exercises, see own progress | ● | ● | | |
| AI code assistant / chat | ● | ● | ● | ● |
| Portfolio projects | ● | ● | | |
| Create classes, upload chapters | | ● | | |
| Generate + edit exercises | | ● | | |
| Class analytics, per-student progress | | ● | ● | ● |
| Exercise quality (flywheel) metrics | | ● | ● | ● |
| Manage users within one tenant | | | ● | ● |
| Configure tenant SSO + LTI | | | ● | ● |
| Platform-wide admin, all tenants | | | | ● |
| Announcements, IP blocklist, feature flags | | | | ● |

Roles are assigned at signup by email domain (`@myanalytiq.org` → `superadmin`, everything else
→ `student`). `tenant_admin` is **never** auto-assigned — a superadmin grants it explicitly via
`PATCH /api/superadmin/users/<id>/role`.

### Integrations

- **LTI 1.3** (`blueprints/lti.py`, 13 routes) — launch, Deep Linking for content selection, and
  Assignment & Grade Services for grade passback. Built on `PyLTI1p3`. Canvas setup guide in
  [`docs/LTI-Canvas-Setup-Guide.md`](docs/LTI-Canvas-Setup-Guide.md).
- **Per-tenant SSO** (`blueprints/sso.py`, 8 routes) — OIDC via `authlib`, supporting Google,
  Microsoft, and generic providers. Each tenant registers its own provider; client secrets are
  Fernet-encrypted at rest and OAuth2 `state` is held in Redis. SAML is not implemented.

## Architecture

A conventional layered Flask application. The dependency direction is strictly one-way, which is
what keeps the layers independently testable:

```
blueprints/   HTTP — routing, request parsing, auth decorators, response shaping
     │        no SQL, no business rules
     ▼
services/     business logic — generation, execution, grading, extraction
     │        no Flask imports, no SQL
     ▼
repositories/ data access — every SQL statement in the codebase lives here
     │
     ▼
core/         infrastructure — db pool, auth, cache, email, storage, errors, middleware
```

`app.py` is deliberately thin (about 100 lines). It defines `create_app()` and delegates every
startup concern to an explicitly ordered sequence in `core/factory.py`:

```python
factory.setup_logging(app)          # structured JSON logs + per-request request_id
factory.configure_app(app)          # values from config.py
factory.setup_sentry(app)
factory.setup_rate_limiting(app)    # Flask-Limiter, Redis-backed
factory.setup_csrf(app)             # Flask-WTF
factory.setup_swagger(app)          # OpenAPI UI
factory.setup_celery(app)
factory.register_request_hooks(app) # CORS, security headers, cache-control
factory.register_error_handlers(app)
factory.register_blueprints(app)
factory.register_frontend_routes(app)
factory.run_migrations(app)         # optional, RUN_MIGRATIONS_ON_BOOT
```

There are **17 blueprints serving roughly 180 REST endpoints**, plus Jinja-rendered pages. The
frontend is server-rendered HTML with vanilla ES modules — **no build step, no bundler, no npm
install**. A React rewrite was attempted and abandoned (rolled back twice in production); Jinja
plus plain JS is the single intentional frontend.

### Request lifecycle

1. `ProxyFix` normalises `X-Forwarded-*` (the app runs behind Cloudflare → Render).
2. `before_request` assigns a `request_id`, applies CORS, and handles preflight centrally.
3. `@require_auth` validates the JWT and populates `g.user_id`, `g.user_role`, `g.tenant_id`.
4. `@require_role(...)` / `@require_super_admin` authorise from `g.user_role` — no re-query.
5. The route delegates to a service and/or repository.
6. A connection is taken from the pool, stored on Flask `g`, and released at teardown.
7. `after_request` sets security and cache headers (`/api/*` is always `no-store`).

## Tech stack

| Layer | Choice |
|---|---|
| Runtime | Python 3.11.9 |
| Web framework | Flask 3.1 + Gunicorn |
| Database | PostgreSQL (Supabase), `psycopg2` `ThreadedConnectionPool` |
| Cache / broker | Redis |
| Async tasks | Celery (+ Flower for monitoring) |
| AI | Google Gemini (`gemini-flash-latest` by default) |
| Object storage | Supabase Storage (course PDFs) |
| Auth | JWT (`PyJWT`), bcrypt (12 rounds), OIDC (`authlib`), LTI 1.3 (`PyLTI1p3`) |
| Frontend | Jinja2 templates + vanilla ES modules (24 templates, 21 JS modules) |
| Docs | OpenAPI via `apispec` + `flask-swagger-ui` |
| Monitoring | Sentry, structured JSON logging |
| Email | Resend (primary) or SMTP |
| Tests | pytest (unit / integration / e2e) |
| CI | GitHub Actions — flake8, black, mypy, pytest, bandit, pip-audit |
| Hosting | Render (web + worker), Cloudflare in front |

## Repository layout

```
app.py                  Entry point — create_app(), Gunicorn target
config.py               Every env var, read once, with validate_config()
db_migrate.py           Forward-only SQL migration runner

blueprints/             17 blueprints, ~180 routes
  auth.py               signup, signin, refresh, password reset
  users.py              profile, settings, preferences
  classes.py            class CRUD, enrollment, roster, analytics
  chapters.py           PDF chapters within a class
  exercises.py          exercise CRUD, submission, grading
  content_import.py     upload + extraction pipeline
  ai.py                 Gemini chat proxy, code assistant
  portfolio.py          student portfolio projects
  lti.py                LTI 1.3 launch, deep linking, grade passback
  sso.py                per-tenant OIDC
  superadmin.py         platform-wide administration
  tenant_admin.py       tenant-scoped administration
  flywheel.py           exercise-quality instrumentation
  health.py             health checks, CSRF token, contact
  platform.py           public platform config
  api_docs.py           OpenAPI spec

services/               business logic (no Flask, no SQL)
  exercise_generator.py Gemini call → structured exercise JSON
  code_runner.py        sandboxed multi-language execution + grading
  container_runner.py   optional kernel-isolated container sandbox
  content_extractor.py  PDF/DOCX text extraction
  ai_grader.py          AI-assisted qualitative feedback
  portfolio_service.py  portfolio domain logic

repositories/           all SQL lives here (10 modules)
core/                   infrastructure (14 modules: database, auth, cache,
                        storage, email, errors, middleware, audit, sentry,
                        pagination, extensions, factory, response_helpers)
workers/                Celery tasks + beat schedule
templates/              24 Jinja2 templates
static/                 js/ (21 ES modules), css/, course PDFs
migrations/             14 forward-only SQL migrations
tests/                  58 test modules — unit/, integration/, e2e/
scripts/                operational scripts (backups, daily cycle, seeding)
docs/                   architecture, schema, security, runbook, ADRs
deployment/ docker/     Dockerfiles, sandbox image, compose
load-tests/             load-testing scenarios
```

## Data model

33 tables in PostgreSQL. Full column-level reference in
[`docs/DATABASE_SCHEMA.md`](docs/DATABASE_SCHEMA.md), generated from a freshly
migrated database rather than maintained by hand.

```
tenants ──┬── users ──┬── user_profiles / user_settings / user_preferences
          │           ├── conversations            (AI chat history)
          │           ├── ai_agent_digest          (per-user AI context)
          │           └── password_resets
          │
          ├── tenant_sso_providers                 (per-tenant OIDC config)
          ├── lti_configurations ── lti_sessions   (LMS registrations)
          │
          └── classes ──┬── class_enrollments      (student ↔ class)
                        ├── class_resources
                        └── class_chapters ── class_exercises
                                                   │
                                                   ├── practice_progress
                                                   │     (per-student best score)
                                                   ├── exercise_attempts
                                                   │     (every submission)
                                                   ├── exercise_ratings
                                                   ├── exercise_generation_events
                                                   ├── exercise_outcome_events
                                                   └── exercise_quality_scores
                                                         (the AI flywheel)

                 users ── portfolio_profiles ── portfolio_items / portfolio_views

platform-wide: platform_config · announcements · ip_blocklist · contact_submissions
               audit_log (FERPA mutation log) · schema_migrations
```

Notable conventions:

- `user_id` and `tenant_id` are UUID **strings**, not integers.
- `tenant_id IS NULL` means a platform-level user rather than a tenant member.
- `password_hash` is NULL for SSO-only and LTI-only accounts.
- `audit_log` records every mutation for FERPA compliance.

### Building the schema

The schema lives in exactly one place: the numbered SQL files in `migrations/`.
`000_initial_schema.sql` creates all of it from nothing, and each later migration
changes it once. So an empty database becomes a working one in one command:

```bash
createdb analytiq
DATABASE_URL=postgresql://localhost/analytiq python db_migrate.py
```

`db_migrate.py` applies the files in numeric order and records each one in
`schema_migrations`, skipping what is already there — it is the same command
Render runs as its pre-deploy step, and the same one the integration tests use to
build their schema. Every migration is idempotent, so re-running it is a no-op
and an existing database is unaffected by `000`.

Schema changes go in a new numbered file; `000` is frozen history and
`tests/unit/test_migrations.py` enforces that it only ever creates things.

## Getting started

### Prerequisites

- Python 3.11 (`.python-version` pins 3.11.9)
- Docker (for local PostgreSQL + Redis)
- A Google Gemini API key, for anything touching AI generation

### Setup

```bash
git clone https://github.com/adamelharouchi5-blip/AnalytIQ.git
cd AnalytIQ

python3 -m venv .venv && source .venv/bin/activate
make install                 # pip install -r requirements.txt
pip install -r requirements-dev.txt

cp .env.example .env         # then fill in the required values below
```

### Run it

`make help` lists every target. The common ones:

```bash
make services      # start PostgreSQL + Redis in Docker (background)
make migrate       # build the schema (or apply pending migrations)
make dev           # services + Flask dev server on :5001
```

`make services` brings up an empty `analytiq` database; `make migrate` turns it
into a complete schema — there is no manual DDL step and no seeding required to
start the app.

In a second terminal, for background tasks:

```bash
celery -A workers.celery_app.celery_app worker --loglevel=info
make flower        # optional Celery monitoring UI on :5555
```

Then:

- App — <http://localhost:5001>
- Health — <http://localhost:5001/api/health> (and `/api/health/detail`)
- API docs — <http://localhost:5001/api/docs>

Other useful targets: `make stop`, `make shell` (REPL with app context),
`make sandbox-image` (build the locked-down execution container), `make clean`.

## Configuration

Everything is read through `config.py`, which exposes `validate_config()` — called at startup and
**fatal in production only**, so local development can run partially configured. See
[`.env.example`](.env.example) for the full annotated list.

**Required**

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | Flask session + default JWT signing key |
| `GEMINI_API_KEY` | Google Gemini API key |
| `SUPABASE_URL` / `SUPABASE_KEY` | Storage for course PDFs (service-role key) |
| `REDIS_URL` | Cache, rate-limit store, Celery broker |

**Commonly set**

| Variable | Default | Purpose |
|---|---|---|
| `FLASK_ENV` | `development` | `development` / `testing` / `production` |
| `JWT_ACCESS_TTL_HOURS` | `24` | Access token lifetime |
| `JWT_REFRESH_TTL_DAYS` | `30` | Refresh token lifetime |
| `CORS_ORIGINS` | — | Comma-separated allowed origins |
| `DB_POOL_MIN` / `DB_POOL_MAX` | `1` / `5` | Connection pool bounds |
| `MAX_PDF_SIZE_MB` | `50` | Upload cap |
| `BCRYPT_ROUNDS` | `12` | Password hashing cost |
| `SSO_ENCRYPTION_KEY` | — | Dedicated Fernet key for stored SSO secrets |
| `LTI_PRIVATE_KEY` / `LTI_PUBLIC_KEY` | — | LTI 1.3 signing keypair |
| `RESEND_API_KEY` | — | Transactional email |
| `SENTRY_DSN` | — | Error tracking |

**Feature flags** — all read at startup:

| Flag | Default | Effect |
|---|---|---|
| `FEATURE_AI_EXERCISES` | on | AI exercise generation |
| `FEATURE_ANALYTICS` | on | Analytics endpoints |
| `FEATURE_CSRF` | **on** | CSRF protection |
| `FEATURE_EMAIL` | off | Outbound notification email |
| `FEATURE_ASYNC_TASKS` | off | Route heavy work through Celery |
| `FEATURE_PDF_CHUNKING` | off | Chunked extraction for large PDFs |
| `SANDBOX_USE_CONTAINER` | off | Kernel-isolated container sandbox (needs Docker) |

> Never commit a real `.env`. It is gitignored, and so is `~/.analytiq_env`, which holds the
> digest SMTP credentials.

## Testing

```bash
make test              # unit + integration (skips e2e)
make test-unit         # unit only — fully mocked, no services needed
make test-integration  # needs live PostgreSQL (make services)
make test-e2e          # needs a running app
make test-cov          # with coverage report
```

Test tiers:

- **`tests/unit/`** — mocks the database through `conftest.py`. Fast, no external services.
- **`tests/integration/`** — runs against real PostgreSQL, building its schema by applying
  `migrations/` to an empty database. It needs an explicitly disposable database, named by
  `TEST_DATABASE_URL`; `make test-integration` supplies a local default. Without it the tier
  skips, so a developer whose `DATABASE_URL` points at a real deployment can never have the
  suite write to it.
- **`tests/e2e/`** — drives a running application.

With `TESTING=True`, `require_auth` accepts an `X-Test-User-ID` header to impersonate a user.
This bypass is guarded by the environment and must never be reachable in production.

## Code quality and CI

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs three jobs on every push and PR:

**`test`** — Python 3.11, pip cached, then:

```bash
flake8          # lint        (gating)
black --check   # formatting  (gating)
mypy            # type check
pytest --cov    # tests → Codecov
```

**`security-scan`**

```bash
bandit   # full report as an artifact, AND gating on MEDIUM+ severity
pip-audit  # dependency CVE scan
```

Bandit was moved from advisory to a **gating MEDIUM+ check** after all 58 then-open findings were
triaged; the 19 `B608` hits were confirmed false positives (parameterised queries) and are skipped
with written justification rather than silenced wholesale.

`requirements.txt` carries an inline advisory ID next to each security-motivated pin
(`PYSEC-2026-2151`, `PYSEC-2026-87`, …) so a future bump cannot silently regress a fix.

**`deploy-notification`** — reports the result on `main`.

## Deployment

Render, configured by [`render.yaml`](render.yaml), with two services from one
[`Procfile`](Procfile):

```
web:    gunicorn -c gunicorn.conf.py app:app
worker: celery -A workers.celery_app.celery_app worker --loglevel=info --concurrency=2
```

- **Migrations run once per deploy** via `preDeployCommand: python db_migrate.py`. It exits
  non-zero on failure, which blocks the deploy rather than shipping code against a schema that
  never applied. Once that is confirmed working, set `RUN_MIGRATIONS_ON_BOOT=false` so workers
  stop migrating at boot.
- **Health check** — `/api/health`.
- **Caching** — Flask's `after_request` sets `no-store` on `/api/*` and `public, max-age=86400`
  elsewhere, which Cloudflare honours for `/static/*`. Render web services cannot set
  route-level headers in `render.yaml`, so these belong in the app. Cloudflare cache rules are
  documented inline in `render.yaml`.

Pre-deploy verification steps live in [`docs/RENDER_ENV_CHECKLIST.md`](docs/RENDER_ENV_CHECKLIST.md).

## Security model

**Authentication** — bcrypt (12 rounds) for passwords; JWT bearer tokens (24h access / 30d
refresh) with a `token_version` column for server-side invalidation; OIDC and LTI 1.3 identities
link to the same `users` row.

**Authorisation** — `@require_auth` populates `g.user_id` / `g.user_role` / `g.tenant_id` once;
`@require_role` and `@require_super_admin` authorise from that context. Tenant-scoped endpoints
filter on `g.tenant_id`, so a `tenant_admin` cannot read across tenants.

**Code execution** is the most security-sensitive surface. Defence in depth:

- Every non-SQL language runs in a child **subprocess** — never in the web process.
- `RLIMIT_AS` / `RLIMIT_FSIZE` / `RLIMIT_NPROC` on Linux.
- Python: dangerous imports blocked, `open()` restricted to read-only.
- JavaScript: `--disallow-code-generation-from-strings`.
- SQL: in-process SQLite with a `SIGALRM` timeout.
- Per-test `subprocess.run(timeout=...)` on every language.
- Fail-closed — an unavailable runtime returns `runtime_missing`, never "pass".
- Optional **kernel-isolated container sandbox** behind `SANDBOX_USE_CONTAINER`
  ([`docs/SANDBOX_CONTAINER.md`](docs/SANDBOX_CONTAINER.md)). Off by default; it needs a
  Docker-capable host, which Render does not provide.

**Application hardening** — CSRF on by default (Flask-WTF); per-endpoint rate limits
(Flask-Limiter over Redis: 5 signups/hour, 10 signins/minute, 3 password resets/hour);
`MAX_CONTENT_LENGTH` and per-type upload caps; PDF uploads screened for a valid header and
suspicious content patterns; secure/HttpOnly/SameSite cookies in production; CSP and other
security headers; `ip_blocklist`; Sentry; and an `audit_log` row for every mutation.

**Error handling** — internal exception text is logged, never returned. Clients get a generic
message and a `request_id` that correlates to the structured log entry.

Policy and reporting: [`docs/SECURITY.md`](docs/SECURITY.md).

### A note on this repository's history

This repository's git history was rewritten in October 2026 to purge credentials that had been
committed during early development — a Google Gemini API key that appeared as a hardcoded
fallback, and an LTI RSA private key. They are gone from the current tree and from every commit,
but a history rewrite cannot undo prior exposure: this repository was public beforehand, so both
credentials must be treated as permanently compromised and rotated at the provider rather than
merely deleted here. Any key found in an old clone, fork, or cached view is dead. No credential
belongs in this repository — everything is read from the environment via `config.py`.

## Operations

**Database backups** — `scripts/backup_db.sh` takes encrypted, verified, off-provider backups on
a schedule, after a production incident in which the Supabase dashboard showed no recoverable
backup. The script distinguishes failure classes deliberately: a connection dropping mid-dump is
retried (it can plausibly clear), while an absent Docker daemon fails fast on its own message
rather than burning three identical retries. Failures email the owner.
See [`docs/security/B27_BACKUP_SCHEDULE.md`](docs/security/B27_BACKUP_SCHEDULE.md).

**Migrations** — forward-only numbered SQL in `migrations/`, applied by `db_migrate.py`, tracked
in `schema_migrations`. Never edit an applied migration; add a new one.

**Runbook** — incident procedures and recovery steps in [`docs/RUNBOOK.md`](docs/RUNBOOK.md).

## Documentation

[`docs/README.md`](docs/README.md) is the full index. Highlights:

| Document | Contents |
|---|---|
| [`ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Layering, request lifecycle, design decisions |
| [`DATABASE_SCHEMA.md`](docs/DATABASE_SCHEMA.md) | Every table, column, and relationship |
| [`PROJECT_OVERVIEW.md`](docs/PROJECT_OVERVIEW.md) | Product and codebase orientation |
| [`SECURITY.md`](docs/SECURITY.md) | Security model and reporting policy |
| [`RUNBOOK.md`](docs/RUNBOOK.md) | Operational procedures |
| [`AI_EXERCISE_GENERATION.md`](docs/AI_EXERCISE_GENERATION.md) | The generation pipeline |
| [`OUTPUT_BASED_GRADING.md`](docs/OUTPUT_BASED_GRADING.md) | Grading schema and rationale |
| [`SANDBOX_CONTAINER.md`](docs/SANDBOX_CONTAINER.md) | Container isolation design |
| [`LTI-Canvas-Setup-Guide.md`](docs/LTI-Canvas-Setup-Guide.md) | Wiring AnalytIQ into Canvas |
| [`14-SSO-Tenant-Authentication.md`](docs/14-SSO-Tenant-Authentication.md) | Per-tenant OIDC |
| [`12-Superadmin-Architecture.md`](docs/12-Superadmin-Architecture.md) | Admin role design |
| [`ACCESSIBILITY.md`](docs/ACCESSIBILITY.md) | Accessibility commitments |
| [`adr/`](docs/adr) | Architecture decision records |

Contribution workflow and conventions: [`CONTRIBUTING.md`](CONTRIBUTING.md).

## License

[MIT](LICENSE) © 2026 Adam El Harouchi — for the **software**: source code, configuration,
migrations, tests, scripts, and technical documentation. You are free to use, copy, modify, and
distribute it, including commercially, provided the copyright and permission notices are retained.
It is provided as is, without warranty.

**Two carve-outs.** `sales/` and `research/` are business and research material published for
reference only — commercial pipeline, outreach drafts, invoice templates, and the internal
claims-evidence register. **All rights to their contents are reserved and they are not covered by
the MIT grant.** The licence also conveys no rights to the hosted AnalytIQ service, the AnalytIQ
name, or the logo.

See [`LICENSE`](LICENSE) for the full text and scope.
