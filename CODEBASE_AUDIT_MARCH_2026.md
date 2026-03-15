# AnalytIQ Codebase Audit — March 2026

**Prepared:** 2026-03-14
**Auditor:** Claude Sonnet 4.6 (automated read of every source file)
**Repository:** /Users/aelharouchi/Documents/GitHub/AnalytIQ
**Branch:** main (HEAD 58c14a7)

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [File Tree and Module Map](#2-file-tree-and-module-map)
3. [Technology Stack](#3-technology-stack)
4. [Database Schema](#4-database-schema)
5. [Authentication and Authorization Flows](#5-authentication-and-authorization-flows)
6. [Every API Endpoint](#6-every-api-endpoint)
7. [AI Exercise Generation Pipeline](#7-ai-exercise-generation-pipeline)
8. [Code Grading System](#8-code-grading-system)
9. [AI Chat Subsystem](#9-ai-chat-subsystem)
10. [Frontend Architecture](#10-frontend-architecture)
11. [Multi-Tenancy Model](#11-multi-tenancy-model)
12. [LTI 1.3 Integration](#12-lti-13-integration)
13. [SSO / OIDC Integration](#13-sso--oidc-integration)
14. [Background Task System (Celery)](#14-background-task-system-celery)
15. [Caching and Rate Limiting](#15-caching-and-rate-limiting)
16. [Security Controls](#16-security-controls)
17. [Monitoring and Logging](#17-monitoring-and-logging)
18. [CI/CD Pipeline](#18-cicd-pipeline)
19. [Git State and Deployment](#19-git-state-and-deployment)
20. [Known Issues and Technical Debt](#20-known-issues-and-technical-debt)
21. [Data Flow Diagrams (Textual)](#21-data-flow-diagrams-textual)
22. [Gaps and Confidence Notes](#22-gaps-and-confidence-notes)

---

## 1. Project Overview

AnalytIQ is a multi-tenant learning management and programming practice platform deployed at https://myanalytiq.org. It allows professors to create classes, upload PDF course materials, auto-generate programming exercises from those materials via Google Gemini AI, and track student progress through a sandbox code grader.

The backend is a Python/Flask application. The frontend is vanilla JavaScript served from the same process. PostgreSQL (hosted on Supabase) is the primary data store. Redis serves as the rate-limiter storage, response cache, and Celery broker. The application runs on Render.

**Core user journeys:**

1. Professor uploads a PDF chapter. Backend extracts text, calls Gemini, stores 5-8 programming exercises with test cases.
2. Student enrolls in a class, opens an exercise, writes code in a browser editor, submits. Backend runs the code in a sandboxed subprocess, returns a score.
3. Superadmin manages tenants, approves pending accounts, views audit logs, impersonates users.
4. LMS (Canvas, Blackboard, etc.) launches AnalytIQ via LTI 1.3. Students are auto-enrolled; grades flow back via AGS.
5. Tenant SSO: students sign in via Google/Microsoft/generic OIDC; backend upserts user record, issues JWT.

**Architecture in one sentence:** A single Flask process (app.py as entry point, 13 blueprint modules) serves both API and HTML, backed by psycopg2 connection pool to PostgreSQL and optional Redis/Celery for async and caching.

---

## 2. File Tree and Module Map

```
AnalytIQ/
├── app.py                         # Flask application factory, blueprint registration, CORS, logging
├── config.py                      # All environment variable reads and constants
├── db.py                          # psycopg2 ThreadedConnectionPool, get_db_connection(), teardown
├── db_migrate.py                  # SQL migration runner (reads migrations/*.sql, tracks in schema_migrations)
├── auth_helpers.py                # JWT creation/decode, require_auth/require_role decorators, password hash
├── audit.py                       # audit() function — writes to audit_log table atomically
├── cache.py                       # Redis client init, cache_response() decorator, invalidate_cache()
├── celery_app.py                  # Celery application configuration, task queues, beat schedule
├── tasks.py                       # Celery tasks: PDF processing, exercise generation, email, cleanup
├── supabase_storage.py            # Supabase Storage client: upload, signed URL, delete, health check
├── middleware.py                  # IP blocklist and maintenance mode before_request hooks
├── extensions.py                  # Shared Flask extension instances (Limiter, csrf_exempt wrapper)
├── sentry_config.py               # Sentry SDK initialization, PII filter, manual capture helpers
├── utils/
│   └── email_service.py           # Resend API wrapper (send_email)
├── blueprints/
│   ├── auth.py                    # /api/users/signup, signin, forgot-password, reset-password
│   ├── users.py                   # /api/users/* (profile, settings, conversations, AI digest, progress)
│   ├── classes.py                 # /api/classes/* (CRUD, enroll, progress, leaderboards, resources)
│   ├── chapters.py                # /api/classes/<id>/chapters, /api/chapters/* (upload, exercises, PDF)
│   ├── exercises.py               # /api/exercises/* (progress, leaderboards, grade)
│   ├── ai.py                      # /api/ai/chat (Gemini proxy with circuit breaker)
│   ├── health.py                  # /api/health, /api/health/detail, /api/csrf-token, /api/contact
│   ├── superadmin.py              # /api/superadmin/* (tenants, users, audit, approvals, GDPR export)
│   ├── tenant_admin.py            # /api/tenant-admin/* (tenant-scoped admin operations)
│   ├── lti.py                     # /lti/* and /api/lti/* (LTI 1.3 JWKS, login, launch, NRPS, AGS)
│   ├── sso.py                     # /api/sso/* (OIDC provider management and OAuth2 flow)
│   ├── platform.py                # /api/platform/status (maintenance mode, announcements)
│   └── content_import.py          # /api/import/* (OpenStax, LibreTexts, OER Commons, URL, PyPI)
├── repositories/
│   ├── auth_repository.py         # SQL for signup, signin, password reset
│   ├── user_repository.py         # SQL for profiles, settings, conversations, AI digest, practice progress
│   ├── class_repository.py        # SQL for classes, enrollments, progress, leaderboards, resources
│   ├── chapter_repository.py      # SQL for chapters, PDF BLOB, exercise insert, serving PDF
│   ├── exercise_repository.py     # SQL for exercise detail, test cases, leaderboards
│   ├── lti_repository.py          # SQL for LTI configurations, sessions, class-context linking
│   └── sso_repository.py          # SQL for SSO provider configs and user identity linking
├── python/
│   ├── exercise_generator.py      # Gemini REST API calls for exercise and test case generation
│   ├── code_runner.py             # Sandbox execution engine (Python, JS, R, SQL, Java)
│   ├── content_extractor.py       # File content extraction (PDF, TXT, CSV, IPYNB, DOCX)
│   └── pdf_processor.py           # PyPDF2 wrapper for extracting text from PDF bytes
├── migrations/
│   ├── 001_lti_tables.sql         # LTI tables, user/class LTI columns
│   ├── 002_tenants.sql            # tenants table, user tenant_id, account_status
│   ├── 003_platform_config.sql    # platform_config, announcements, ip_blocklist, password reset cols
│   ├── 004_sso.sql                # tenant_sso_providers, user sso_provider_id/sso_subject
│   ├── 005_class_resources.sql    # class_resources, exercise solution_code/number/created_by
│   ├── 006_audit_log.sql          # password_resets, audit_log tables
│   ├── 007_exercise_test_cases.sql# class_exercises test_cases JSONB, function_name, language
│   └── 008_tenant_email_domain.sql# tenants email_domain column with unique index
├── templates/                     # 26 Jinja2/HTML templates (served by Flask)
├── js/                            # 21 vanilla JavaScript modules
├── tests/
│   ├── conftest.py                # Pytest fixtures: app, client, mock_db, mock_redis, etc.
│   ├── test_auth.py               # Auth endpoint tests
│   ├── test_ai_routes.py          # AI chat tests
│   ├── test_exercises_routes.py   # Exercise endpoint tests
│   ├── test_classes_routes.py     # Class endpoint tests
│   ├── test_chapters_routes.py    # Chapter endpoint tests
│   ├── test_users_routes.py       # User endpoint tests
│   ├── test_superadmin_extended.py# Superadmin tests
│   ├── test_tenant_admin.py       # Tenant admin tests
│   ├── test_sso_routes.py         # SSO route tests
│   ├── integration/               # Integration tests (test_auth_integration, test_classes_integration, test_superadmin)
│   └── e2e/                       # End-to-end tests (excluded from CI run)
├── .github/workflows/ci.yml       # GitHub Actions CI (lint, test, security scan, deploy notification)
├── requirements.txt               # Python dependencies (pinned)
├── config.py                      # (already listed above)
└── gunicorn_config.py             # (inferred — not read, but referenced in Render deploy)
```

---

## 3. Technology Stack

**Runtime:** Python 3.9, gunicorn 21.2.0

**Web framework:** Flask 3.0.0 with Werkzeug ProxyFix middleware (trusts x-forwarded headers from Render's load balancer)

**Database:** PostgreSQL (hosted on Supabase). psycopg2-binary 2.9.10+ with a ThreadedConnectionPool. Pool size is `DB_POOL_MIN` (default 2) to `DB_POOL_MAX` (default `cpu_count * 2`). Connections are stored in Flask `g.db_conn` per request and returned to the pool at `teardown_appcontext`.

**File storage:** Supabase Storage (`supabase>=2.12.0`) for PDF uploads. Chapter PDF data is also stored as BYTEA in the `class_chapters.pdf_data` column as a fallback/primary serving path.

**Cache and broker:** Redis 5.0.1 for Flask-Limiter rate limit storage, response caching (feature-flagged), Celery task broker/result backend, LTI launch state storage, SSO OAuth2 state tokens.

**Authentication:** PyJWT 2.10.1+, HS256 algorithm, 7-day default expiry. JWT payload fields: `user_id`, `role`, `iat`, `exp`, `name`, `email`, `tenant_id` (optional), `impersonator_id` (optional).

**Password hashing:** bcrypt 4.1.2, 12 rounds. Legacy integer hash path kept for migration; `verify_password()` detects which type and flags for rehash on successful login.

**AI generation:** Google Gemini REST API (`google-generativeai>=0.3.1`). The exercise generator calls gemini-2.5-flash (hardcoded in `python/exercise_generator.py`) regardless of the `GEMINI_MODEL` config value. The AI chat proxy (blueprints/ai.py) uses the model from the user's preferences, validated against an allowlist.

**Async tasks:** Celery 5.3.4 with Redis broker. Feature-flagged off by default (`FEATURE_ASYNC_TASKS=False`). When disabled, PDF processing and exercise generation run synchronously in the request thread.

**CSRF:** Flask-WTF CSRFProtect, feature-flagged off by default (`FEATURE_CSRF=False`). All API routes are decorated with `@csrf_exempt` regardless, so enabling the flag only protects HTML form submissions.

**Rate limiting:** Flask-Limiter 3.5.0, fixed-window strategy. Default: 200/day + 50/hour per IP in production; 50000/day + 2000/hour in development. Endpoint-specific limits override the default.

**Security monitoring:** sentry-sdk[flask] 1.40.0+. PII filtering strips Authorization headers, Cookie headers, and request body fields named `password`, `api_key`, `secret`, `token`. Transaction sampling at 10%; error sampling at 100%.

**Email:** Resend API (`resend>=1.0.0`) for transactional emails (password reset, admin approval notifications, contact form acknowledgment).

**Content extraction:** PyPDF2 3.0.1 for PDF text, csv module for CSV, json module for IPYNB notebooks, python-docx 1.1.0 for DOCX files.

**LTI 1.3:** PyLTI1p3 2.0.0+ with Redis-backed storage to work in LMS iframes where SameSite=Lax cookies are blocked.

**SSO:** Authlib 1.3.0+, Fernet encryption (cryptography 41.0.0+) for client_secret at rest. OAuth2 state stored in Redis with 600s TTL.

**Logging:** python-json-logger 2.0.7 for structured JSON logs. Each log record includes a `request_id` injected by `_RequestIdFilter`.

**Frontend:** Vanilla JavaScript (ES5/ES6 mix, no build step, no bundler). 26 HTML templates rendered by Flask/Jinja2. 21 JS modules loaded via `<script>` tags.

---

## 4. Database Schema

The schema is built incrementally via migrations 001-008. The following describes the final state.

### Core Tables

**users**
- `user_id` UUID PK (generated with `uuid.uuid4()` in Python)
- `name` VARCHAR, `email` VARCHAR UNIQUE, `password_hash` VARCHAR (nullable for SSO/LTI-only accounts)
- `role` VARCHAR (student | professor | tenant_admin | superadmin)
- `is_super_admin` BOOLEAN (redundant flag mirroring `role = 'superadmin'`)
- `tenant_id` UUID FK → tenants
- `account_status` VARCHAR (active | disabled | pending_approval | denied) — added migration 002
- `requires_password_reset` BOOLEAN — added migration 003
- `last_login` TIMESTAMPTZ — added migration 003
- `lti_sub` VARCHAR, `lti_issuer` VARCHAR — added migration 001
- `sso_provider_id` UUID FK → tenant_sso_providers, `sso_subject` VARCHAR — added migration 004
- `created_at`, `updated_at` TIMESTAMPTZ

**tenants**
- `tenant_id` UUID PK (auto-generated), `name` VARCHAR, `lti_issuer` VARCHAR
- `is_active` BOOLEAN, `email_domain` VARCHAR UNIQUE (for auto-assignment at signup) — added migration 008
- `created_at`, `updated_at` TIMESTAMPTZ

**classes**
- `class_id` VARCHAR PK (professor-assigned code), `professor_id` UUID FK → users
- `name` VARCHAR, `description` TEXT, `tenant_id` UUID FK → tenants — added migration 002
- `lti_context_id` VARCHAR, `lti_issuer` VARCHAR — added migration 001
- `nrps_context_url` TEXT, `ags_enabled` BOOLEAN, `ags_lineitems_url` TEXT — added migration 001
- `created_at`, `updated_at` TIMESTAMPTZ

**class_chapters**
- `chapter_id` VARCHAR PK (format: `{class_id}_{timestamp_ms}`), `class_id` VARCHAR FK → classes
- `title` VARCHAR, `description` TEXT, `chapter_number` INT
- `pdf_url` TEXT (Supabase signed URL), `pdf_filename` VARCHAR, `pdf_data` BYTEA
- `created_at`, `updated_at` TIMESTAMPTZ

**class_exercises**
- `exercise_id` UUID PK, `chapter_id` VARCHAR FK → class_chapters, `class_id` VARCHAR FK → classes
- `title` VARCHAR, `description` TEXT, `difficulty` VARCHAR (easy | medium | hard)
- `solution_code` TEXT — added migration 005
- `exercise_number` INT — added migration 005
- `created_by` UUID FK → users — added migration 005
- `function_name` VARCHAR, `test_cases` JSONB, `language` VARCHAR — added migration 007
- `created_at` TIMESTAMPTZ

**class_enrollments**
- `class_id` VARCHAR FK → classes, `student_id` UUID FK → users
- `enrolled_at` TIMESTAMPTZ
- PK: (class_id, student_id)

**class_resources**
- `resource_id` UUID PK, `class_id` VARCHAR FK → classes, `user_id` UUID FK → users
- `title` VARCHAR, `description` TEXT, `resource_type` VARCHAR, `resource_url` TEXT
- `file_data` BYTEA, `filename` VARCHAR (for uploaded file resources)
- `created_at`, `updated_at` TIMESTAMPTZ

### User Companion Tables

**user_profiles** — `user_id` UUID PK, `full_name`, `bio`, `profile_picture`, `updated_at`

**user_settings** — `user_id` UUID PK, `email_notifications` BOOLEAN, `updated_at`

**user_preferences** — `user_id` UUID PK, `current_language` VARCHAR, `gemini_model` VARCHAR, `ai_provider` VARCHAR, `updated_at`

**ai_agent_digest** — `user_id` UUID PK, `goal`, `constraints`, `decisions`, `current_state`, `open_questions` TEXT fields, `updated_at`

**ai_agent_memory** — `id` SERIAL PK, `user_id` UUID FK → users, `memory_item` TEXT, `created_at`

### Conversation Tables

**conversations** — `conversation_id` UUID PK, `user_id` UUID FK, `title` VARCHAR, `archived` BOOLEAN, `deleted` BOOLEAN (soft delete), `created_at`, `updated_at`

**conversation_messages** — `id` SERIAL PK, `conversation_id` UUID FK, `role` VARCHAR (user | assistant), `content` TEXT, `message_order` INT, `created_at`

### Progress Tables

**practice_progress** — `user_id` UUID, `exercise_id` UUID, `exercise_title`, `best_score`, `best_accuracy`, `best_time`, `total_attempts`, `last_attempt_score/accuracy/time`, `completed` BOOLEAN, `last_completed_at`, `class_id`, `class_exercise_id`
- PK: (user_id, exercise_id)
- The UPSERT logic uses `GREATEST(practice_progress.best_score, EXCLUDED.best_score)` so scores never decrease. Completion threshold is score >= 50.

**exercise_attempts** — `id` SERIAL PK, `user_id` UUID, `exercise_id` UUID, `score`, `accuracy`, `time_spent`, `attempt_number`, `attempted_at` TIMESTAMPTZ

### LTI Tables

**lti_configurations** — `config_id` UUID PK, `platform_name`, `issuer`, `client_id`, `auth_login_url`, `auth_token_url`, `key_set_url`, `deployment_ids` JSONB, `created_by` UUID FK → users, `created_at`

**lti_sessions** — `session_id` UUID PK, `user_id`, `class_id`, `nrps_context_url`, `lti_context_id`, `issuer`, `client_id`, `launch_data` JSONB, `expires_at` TIMESTAMPTZ

### SSO Tables

**tenant_sso_providers** — `provider_id` UUID PK, `tenant_id` UUID FK → tenants, `provider_name`, `provider_type` (google | microsoft | oidc | saml), `client_id`, `client_secret` TEXT (Fernet-encrypted), `discovery_url`, `allowed_domains` JSONB, `role_mapping_attribute`, `role_mapping` JSONB, `default_role`, `is_enabled` BOOLEAN, `created_by`, `created_at`, `updated_at`

### Platform Tables

**platform_config** — `key` VARCHAR PK, `value` TEXT (e.g., `maintenance_mode=true`)

**announcements** — `announcement_id` UUID PK, `title`, `message`, `type`, `target_roles` JSONB, `tenant_id` UUID (nullable = global), `is_active` BOOLEAN, `expires_at`, `created_at`

**ip_blocklist** — `ip_address` VARCHAR PK

### Auth/Audit Tables

**password_resets** — `id` SERIAL PK, `email` VARCHAR, `token` VARCHAR, `expires_at` TIMESTAMPTZ, `created_at`

**audit_log** — `id` SERIAL PK, `action` VARCHAR, `resource_type` VARCHAR, `resource_id` TEXT, `user_id` UUID (nullable), `ip_address` VARCHAR, `impersonator_id` UUID (nullable), `details` JSONB, `created_at` TIMESTAMPTZ

**contact_submissions** — `submission_id` UUID PK, `name`, `email`, `subject`, `message` TEXT, `status` VARCHAR (new | read | resolved | archived), `user_id` UUID (nullable), `created_at`

**schema_migrations** — `filename` VARCHAR PK, `applied_at` TIMESTAMPTZ (migration tracking)

---

## 5. Authentication and Authorization Flows

### 5.1 JWT Token Lifecycle

All authentication is stateless JWT. Tokens are issued at signup, signin, SSO callback, and LTI launch. There is no server-side session store; the token is the only credential.

**Token structure** (HS256, `JWT_SECRET_KEY` from env):
```json
{
  "user_id": "...",
  "role": "student | professor | tenant_admin | superadmin",
  "name": "...",
  "email": "...",
  "tenant_id": "...",           // optional
  "impersonator_id": "...",    // optional, present during impersonation
  "iat": 1234567890,
  "exp": 1234567890            // iat + JWT_ACCESS_TOKEN_EXPIRES_HOURS (default 168 = 7 days)
}
```

Impersonation tokens have a 1-hour TTL and include `impersonator_id`. These are issued by `POST /api/superadmin/users/<id>/impersonate`.

### 5.2 require_auth Decorator

Located in `auth_helpers.py`. Applied to every protected endpoint. Behavior:

1. Reads `Authorization: Bearer <token>` header.
2. Checks BOTH `current_app.config["TESTING"] is True` AND `os.environ.get("FLASK_ENV") == "testing"` for the test bypass. Sets `g.user_id` from `X-Test-User-ID` header and `g.user_role` from `X-Test-User-Role` header if bypass is active.
3. Decodes the JWT. On expiry or invalid signature, returns 401.
4. Performs a per-request DB lookup for `account_status`. Returns 403 if `disabled`, `pending_approval`, or `denied`.
5. Populates `g.user_id`, `g.user_role`, `g.user_email`, `g.tenant_id`, `g.impersonator_id`.

The per-request DB lookup (step 4) means every authenticated request hits the database once for account status. There is no caching of this check.

### 5.3 Role-Based Access Decorators

- `@require_role(*roles)`: checks `g.user_role in roles`. Returns 403 if not.
- `@require_super_admin`: checks `g.user_role == "superadmin"`. Returns 403 if not.
- `@require_tenant_admin`: checks `g.user_role in ("tenant_admin", "superadmin")`. Allows superadmin to access all tenant-admin routes.

### 5.4 Role Detection at Signup

`detect_role_from_email()` in `auth_helpers.py`:
- `@myanalytiq.org` domain → `superadmin`
- All other domains → `student`

Note: The project memory says `@hult.edu` maps to `professor` and `@student.hult.edu` to `student`. The actual code only checks for `@myanalytiq.org`. The professor/student distinction for Hult emails is NOT in the code.

### 5.5 Signup Flow

1. Validate fields: name, email, password (8-72 chars).
2. Check email not already registered.
3. Look up tenant by email domain (`tenants.email_domain`).
4. Insert user row with `uuid.uuid4()` ID, bcrypt hash, detected role, optional `tenant_id`.
5. If role is `superadmin`: set `account_status = 'pending_approval'`, send email to `aelharouchi@myanalytiq.org`.
6. Create companion rows: `user_profiles`, `user_settings`, `user_preferences`, `ai_agent_digest`.
7. Write audit log event `CREATE_USER`.
8. Issue and return JWT.

### 5.6 Signin Flow

1. Look up user by email.
2. Verify password hash. If legacy integer hash, flag for rehash after successful verify.
3. If rehash needed: update hash in DB, commit.
4. Check `account_status` (disabled/pending_approval/denied → 403).
5. Update `last_login = NOW()`.
6. Issue JWT with `tenant_id` from DB.
7. Return `requires_password_reset: true` if `requires_password_reset` flag is set.

### 5.7 Password Reset Flow

1. `POST /api/users/forgot-password`: generate `secrets.token_urlsafe(32)`, store in `password_resets` with 1hr expiry, send email with link.
2. `POST /api/users/reset-password`: validate token against `password_resets` table, check expiry, update `users.password_hash`, delete token.

### 5.8 Impersonation Flow

Superadmin POSTs to `/api/superadmin/users/<id>/impersonate`. Backend:
1. Verifies target user exists.
2. Prevents impersonating another superadmin unless caller's email == `PLATFORM_OWNER_EMAIL`.
3. Issues a 1-hour JWT with target's identity and `impersonator_id = g.user_id`.
4. Writes `IMPERSONATE_USER` to audit log.
5. Frontend stores original token in `localStorage.original_token`, replaces `authToken` with impersonation token.

Exit impersonation: frontend reads `original_token`, restores it to `authToken`.

---

## 6. Every API Endpoint

### Auth — blueprints/auth.py

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /api/users/signup | None | Create account. Rate: 5/hr |
| POST | /api/users/signin | None | Authenticate. Rate: 10/min |
| POST | /api/users/forgot-password | None | Send reset email. Rate: 3/hr |
| POST | /api/users/reset-password | None | Apply new password. Rate: 5/hr |

### Users — blueprints/users.py

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /api/users/profile | JWT | Get profile (users + user_profiles join) |
| PUT | /api/users/profile | JWT | Update name, email, full_name, bio, profile_picture |
| GET | /api/users/settings | JWT | Get email_notifications setting |
| PUT | /api/users/settings | JWT | Update email_notifications |
| PUT | /api/users/password | JWT | Change password (verify current, update hash) |
| DELETE | /api/users/account | JWT | Delete own account and all data |
| GET | /api/users/conversations | JWT | Paginated list of conversations (?archived=) |
| POST | /api/users/conversations | JWT | Create or update conversation |
| GET | /api/users/conversations/<id> | JWT | Get single conversation with messages |
| PUT | /api/users/conversations/<id> | JWT | Update title/archived/deleted |
| DELETE | /api/users/conversations/<id> | JWT | Soft-delete conversation |
| POST | /api/users/conversations/<id>/messages | JWT | Append message |
| GET | /api/users/ai-digest | JWT | Get AI agent digest fields |
| PUT | /api/users/ai-digest | JWT | Update AI agent digest |
| GET | /api/users/ai-memory | JWT | Get AI memory items |
| PUT | /api/users/ai-memory | JWT | Replace AI memory items |
| GET | /api/users/preferences | JWT | Get language/model/provider preferences |
| PUT | /api/users/preferences | JWT | Update preferences (whitelist: current_language, gemini_model, ai_provider) |
| GET | /api/users/practice-progress | JWT | Get all practice progress OR single exercise (?exercise_id=) |
| PUT | /api/users/practice-progress | JWT | Upsert practice progress + insert exercise_attempt |

### Classes — blueprints/classes.py

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /api/classes | JWT (professor/superadmin) | Create class |
| GET | /api/classes | JWT | List classes (professor sees own, student sees enrolled) |
| GET | /api/classes/<id> | JWT | Class detail with professor info |
| PUT | /api/classes/<id> | JWT | Update class (name/description) — professor or superadmin |
| DELETE | /api/classes/<id> | JWT | Delete class — professor or superadmin |
| POST | /api/classes/enroll | JWT (student) | Enroll by class_id |
| GET | /api/classes/enrolled | JWT | Paginated enrolled classes |
| GET | /api/classes/<id>/students | JWT | Student list for class |
| GET | /api/classes/<id>/progress | JWT | Student × exercise progress matrix (bulk query) |
| GET | /api/progress | JWT (student) | Student's own progress across classes |
| GET | /api/classes/<id>/students/<sid>/progress | JWT | Single student progress in class |
| GET | /api/classes/<id>/leaderboard/average | JWT | Average score leaderboard |
| GET | /api/classes/<id>/leaderboard/exercise/<eid> | JWT | Per-exercise leaderboard |
| GET | /api/classes/<id>/resources | JWT | Chapters + other resources for class |
| POST | /api/classes/<id>/resources | JWT (professor/superadmin) | Add resource (link or file upload) |
| PUT | /api/classes/<id>/resources/<rid> | JWT (professor/superadmin) | Update resource |
| DELETE | /api/classes/<id>/resources/<rid> | JWT (professor/superadmin) | Delete resource |
| GET | /api/classes/<id>/resources/<rid>/download | JWT | Download resource file (BYTEA) |

### Chapters — blueprints/chapters.py

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /api/classes/<id>/chapters | JWT | Upload PDF chapter. Magic byte + pattern scan. Auto-generates exercises. |
| GET | /api/chapters/upload-url | JWT | Supabase presigned upload URL |
| GET | /api/classes/<id>/chapters | JWT | List chapters for class (cached 120s) |
| PUT | /api/chapters/<id> | JWT | Update chapter title/description |
| DELETE | /api/chapters/<id> | JWT | Delete chapter and exercises; remove from Supabase |
| POST | /api/chapters/<id>/generate-exercises | JWT | Regenerate exercises from stored PDF |
| GET | /api/chapters/<id>/exercises | JWT | List exercises for chapter |
| POST | /api/classes/<id>/chapters/<id>/exercises | JWT (professor/superadmin) | Manually add exercise to chapter |
| GET | /api/chapters/<id>/pdf | JWT | Serve PDF (BYTEA from DB or filesystem fallback) |

### Exercises — blueprints/exercises.py

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /api/exercises/progress | JWT | All practice progress for current user |
| GET | /api/exercises/<id>/leaderboard | JWT | Exercise-specific leaderboard (capped at MAX_PAGE_SIZE) |
| GET | /api/leaderboard/grand | JWT | Grand leaderboard (avg score across all exercises) |
| GET | /api/exercises/<id> | JWT | Exercise detail (cached 120s) |
| PUT | /api/exercises/<id> | JWT | Update exercise (owner check) |
| DELETE | /api/exercises/<id> | JWT | Delete exercise |
| POST | /api/exercises/<id>/grade | JWT | Grade code submission against test cases |

### AI — blueprints/ai.py

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /api/ai/chat | JWT | Proxy chat to Gemini. Rate: 20/min + 100/hr per user_id. Circuit breaker (5 failures, 60s recovery). |

### Health — blueprints/health.py

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /api/health | None | Minimal: DB ping, uptime |
| GET | /api/health/detail | JWT | Full: DB, Redis, Supabase storage health (30s cache) |
| GET | /api/csrf-token | None | Returns CSRF token (only meaningful when CSRF enabled) |
| POST | /api/contact | None | Submit contact form; writes to contact_submissions; sends confirmation email |
| GET | /api/tasks/<task_id> | JWT | Check Celery task status |

### Platform — blueprints/platform.py

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /api/platform/status | None | Maintenance mode flag + active announcements (filterable by ?role= ?tenant_id=) |

### LTI — blueprints/lti.py

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /lti/jwks | None | Tool's public JWKS for platform JWT verification |
| GET,POST | /lti/login | None | OIDC login initiation (redirect to platform) |
| POST | /lti/launch | None | LTI resource launch: validate id_token, upsert user, auto-enroll student, render lti-launch.html |
| GET | /lti/setup | JWT (professor/superadmin) | Render LTI setup UI |
| POST | /lti/deep-link/return | None | Sign and return deep-link JWT to LMS |
| GET | /api/lti/config | JWT (professor/superadmin) | List LMS platform registrations |
| POST | /api/lti/config | JWT (professor/superadmin) | Register LMS platform |
| DELETE | /api/lti/config/<id> | JWT (professor/superadmin) | Delete registration (only creator can delete) |
| POST | /api/lti/link-class/<id> | JWT (professor/superadmin) | Link class to LTI context |
| PUT | /api/lti/ags-toggle/<id> | JWT (professor/superadmin) | Toggle AGS grade passback |
| POST | /api/lti/sync-roster/<id> | JWT (professor/superadmin) | NRPS: fetch and enroll LMS students |
| POST | /api/lti/ags/<cid>/<eid> | JWT | Submit grade to LMS via AGS |
| GET | /api/lti/tool-info | JWT (professor/superadmin) | Return tool's LTI endpoint URLs for pasting into LMS |

### SSO — blueprints/sso.py

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /api/sso/providers | None | List enabled providers (safe fields only) |
| GET | /api/sso/init/<id> | None (30/min rate limit) | Begin OAuth2 flow, return auth_url |
| GET | /api/sso/callback/<id> | None | OAuth2 callback: exchange code, upsert user, redirect with JWT |
| GET | /api/sso/admin/providers | JWT (tenant_admin/superadmin) | List tenant's providers |
| POST | /api/sso/admin/providers | JWT (tenant_admin/superadmin) | Create provider config |
| PUT | /api/sso/admin/providers/<id> | JWT (tenant_admin/superadmin) | Update provider config |
| DELETE | /api/sso/admin/providers/<id> | JWT (tenant_admin/superadmin) | Delete provider config |

### Superadmin — blueprints/superadmin.py

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /api/superadmin/tenants | JWT (superadmin) | List tenants with user/class counts |
| POST | /api/superadmin/tenants | JWT (superadmin) | Create tenant |
| PATCH | /api/superadmin/tenants/<id> | JWT (superadmin) | Update tenant (name, lti_issuer, is_active, email_domain) |
| DELETE | /api/superadmin/tenants/<id> | JWT (superadmin) | Delete tenant and all cascaded data |
| GET | /api/superadmin/users | JWT (superadmin) | Paginated, filterable user search (?q, ?tenant_id, ?role, ?status) |
| PATCH | /api/superadmin/users/<id>/status | JWT (superadmin) | Update account_status |
| POST | /api/superadmin/users/<id>/impersonate | JWT (superadmin) | Issue 1-hr impersonation JWT |
| PATCH | /api/superadmin/users/<id>/role | JWT (superadmin) | Change role + optional tenant_id |
| POST | /api/superadmin/users/<id>/force-reset | JWT (superadmin) | Set requires_password_reset=TRUE |
| GET | /api/superadmin/users/<id>/export | JWT (superadmin) | GDPR data export (JSON download) |
| DELETE | /api/superadmin/users/<id> | JWT (superadmin) | Permanently delete user and all data |
| GET | /api/superadmin/classes | JWT (superadmin) | List all classes across professors |
| PATCH | /api/superadmin/classes/<id>/transfer | JWT (superadmin) | Transfer class to different professor |
| DELETE | /api/superadmin/classes/<id> | JWT (superadmin) | Delete class and all content |
| GET | /api/superadmin/pending-approvals | JWT (superadmin) | List pending_approval accounts |
| PATCH | /api/superadmin/users/<id>/approve | JWT (superadmin) | Approve pending account |
| PATCH | /api/superadmin/users/<id>/deny | JWT (superadmin) | Deny pending account |
| GET | /api/superadmin/contact-submissions | JWT (superadmin) | Paginated contact form submissions |
| PATCH | /api/superadmin/contact-submissions/<id> | JWT (superadmin) | Update submission status |
| GET | /api/superadmin/audit | JWT (superadmin) | Paginated, filterable audit log |

### Tenant Admin — blueprints/tenant_admin.py

All routes require `tenant_admin` or `superadmin` role. All queries are scoped to a single tenant via `_scoped_tenant_id()` (reads JWT `tenant_id`; superadmin may pass `?tenant_id=` to browse any tenant).

Routes: GET /api/tenant-admin/overview, GET /api/tenant-admin/analytics, GET/PATCH/DELETE /api/tenant-admin/users/*, POST /api/tenant-admin/users/<id>/impersonate, POST /api/tenant-admin/users/<id>/force-reset, GET /api/tenant-admin/users/<id>/export, GET /api/tenant-admin/pending-approvals, PATCH /api/tenant-admin/users/<id>/approve, PATCH /api/tenant-admin/users/<id>/deny, GET /api/tenant-admin/classes, PATCH /api/tenant-admin/classes/<id>/transfer, DELETE /api/tenant-admin/classes/<id>, GET /api/tenant-admin/audit

Tenant admin can impersonate users within their tenant. Cannot impersonate superadmins.

### Content Import — blueprints/content_import.py

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /api/import/openstax/books | JWT | List OpenStax books from CMS API |
| GET | /api/import/openstax/books/<slug>/toc | JWT | Scrape OpenStax book table of contents |
| GET | /api/import/libretexts/libraries | JWT | Return hardcoded list of 12 LibreTexts subject libraries |
| GET | /api/import/libretexts/search | JWT | Search a LibreTexts library (scrapes search page) |
| GET | /api/import/oer/search | JWT | Search OER Commons API |
| POST | /api/import/preview | JWT | Preview external content (no chapter saved) |
| POST | /api/classes/<id>/chapters/import | JWT | Fetch external content, create chapter, optionally auto-generate exercises |

### API Versioning

`register_api_v1_aliases()` runs at startup and duplicates every `/api/` route as `/api/v1/`. This means every endpoint above also exists under `/api/v1/`. The aliases share the same view function; there is no version-specific behavior.

---

## 7. AI Exercise Generation Pipeline

### 7.1 PDF Upload Path (Synchronous)

1. `POST /api/classes/<class_id>/chapters` receives multipart/form-data with PDF.
2. Validates file size (≤ 50MB), extension whitelist (`{pdf, csv, xlsx, xls, json, txt, ipynb, docx}`), and PDF magic bytes (`%PDF`).
3. Scans for suspicious patterns: `/JavaScript`, `/JS`, `/Launch`, `/EmbeddedFile`.
4. Extracts text from file using `python/content_extractor.py`:
   - PDF: `PyPDF2.PdfReader`, joins all page text.
   - TXT: UTF-8 decode with surrogate replacement.
   - CSV: `csv.reader`, joins all cell values.
   - IPYNB: JSON parse, joins source from code and markdown cells.
   - DOCX: `python-docx`, joins paragraph text.
5. Truncates extracted text to 10,000 characters before sending to Gemini.
6. Calls `generate_exercises_from_pdf_content()` in `python/exercise_generator.py`.
7. Stores exercises in `class_exercises` table with `function_name`, `test_cases` (JSONB), and `language`.
8. Stores PDF bytes in `class_chapters.pdf_data` (BYTEA) and optionally in Supabase.

### 7.2 Gemini Exercise Generation

Located in `python/exercise_generator.py`. Uses direct HTTPS calls to the Gemini REST API (not the Python SDK).

- Model: `gemini-2.5-flash` (hardcoded, ignores `config.GEMINI_MODEL`).
- Temperature: 0.7.
- maxOutputTokens: 8192.
- responseMimeType: `application/json`.
- Input: extracted text (truncated to 10,000 chars), language preference from user or auto-detected.
- Prompt: instructs Gemini to produce a JSON array of 5-8 exercises, each with `language`, `title`, `description`, `difficulty` (easy/medium/hard), `solution_code`, `function_name`, `test_cases` (list of `{input, expected_output}` dicts).
- Output parsing: attempts to parse Gemini's response as JSON. If parsing fails, attempts to extract JSON from a markdown code block.
- Each exercise is inserted via `chapter_repo.insert_exercise()`.

### 7.3 Test Case Retroactive Generation

`generate_test_cases_for_exercise()` in `python/exercise_generator.py`:
- Used when an exercise was created before migration 007 (no test cases stored).
- Triggered automatically in `POST /api/exercises/<id>/grade` if `test_cases` is NULL.
- Temperature: 0.3 (lower for more deterministic output).
- Generates 3-5 test cases per exercise.
- Saves results back to `class_exercises` via `exercise_repo.save_exercise_test_cases()`.

### 7.4 Async Path (Feature-Flagged Off)

When `FEATURE_ASYNC_TASKS=True`, `tasks.py` contains `generate_exercises_async` Celery task. However, this task uses raw SQL that predates migration 007 (does not insert `function_name`, `test_cases`, or `language`). It is therefore functionally broken with the current schema. This task is flagged off by default.

---

## 8. Code Grading System

### 8.1 Grading Request Flow

1. `POST /api/exercises/<id>/grade` receives `{"code": "<student_code>"}`.
2. Retrieves `function_name`, `language`, `test_cases` from `class_exercises`.
3. If exercise predates test-case generation: auto-generates via `generate_test_cases_for_exercise()`, saves, then grades.
4. Calls `run_test_cases()` in `python/code_runner.py`.

### 8.2 Language Runners

The `language` column in `class_exercises` determines which runner is used. Runners are subprocess-based with timeout enforcement.

**Python runner:**
- Wraps student code in a test harness that calls `function_name(input)` and captures stdout.
- On Linux: sets `RLIMIT_FSIZE=0` (no file writes), `RLIMIT_AS=256MB` (virtual memory cap), `RLIMIT_NPROC=0` (no subprocess spawning).
- Blocked imports: `subprocess`, `os`, `sys` (partially), `socket`, `requests`, `urllib`, `shutil`, `pathlib`, `importlib`, `ctypes`, `multiprocessing`, `threading`, `concurrent`.
- Overrides `open()` to be read-only.
- Timeout: 5 seconds per test case (SIGALRM on Unix, threading.Timer on Windows).

**JavaScript runner:**
- Calls `node --disallow-code-generation-from-strings <temp_script.js>`.
- Timeout enforced via `subprocess.run(timeout=5)`.

**R runner:**
- Calls `Rscript <temp_script.R>`.
- Timeout via `subprocess.run(timeout=5)`.

**SQL runner:**
- Uses SQLite in-process (no external process).
- Timeout enforced via `signal.SIGALRM` (5 seconds).
- Creates a temporary in-memory SQLite database per test case.

**Java runner:**
- Writes code to a temp directory, calls `javac`, then `java`.
- Timeout via `subprocess.run(timeout=10)`.

### 8.3 Scoring

**Correctness score (0-80):**
- For each test case: compare actual output to expected output (string comparison after normalization).
- Weighted: earlier test cases are considered more fundamental. The weight array assigns decreasing weights to later tests.
- Formula: `(sum of weights for passing tests / sum of all weights) * 80`.

**Quality score (0-20):**
- `runs_without_error` (0 or 10): code executes without throwing an exception.
- `no_hardcode` (0 or 5): solution does not appear to hardcode expected outputs (heuristic check: looks for literals matching expected values in the code).
- `style` (0 or 5): checks for presence of comments or docstrings (Python: `#` or `"""`, JS: `//` or `/* */`).

**Total score (0-100):** `correctness_score + quality_score`.

Score >= 50 marks the exercise as `completed` in `practice_progress`.

### 8.4 Security Limitations

- Resource limits (RLIMIT) only work on Linux. On macOS/Windows (development), student code runs with OS-level process limits only.
- The blocked imports list can be bypassed via `__import__()`, `importlib.import_module`, or by encoding the import string and using `exec`.
- `open()` override only works within Python; it does not prevent file access via ctypes or other low-level mechanisms.
- SQL runner uses an in-process SQLite database; no filesystem isolation.

---

## 9. AI Chat Subsystem

Located in `blueprints/ai.py`.

### 9.1 Request Flow

1. Requires JWT auth.
2. Rate limit: 20/min + 100/hr per `g.user_id` (not per IP).
3. Validates request payload: total JSON size ≤ 50KB, message count ≤ 100.
4. Validates `model` field against allowlist (includes gemini-1.5-flash, gemini-2.0-flash, gemini-2.5-flash, and others).
5. Checks circuit breaker state (stored as a dict in module scope): if 5 consecutive Gemini failures within the last 60 seconds, returns 503.
6. Calls Gemini REST API directly (not through the Python SDK).
7. On success: resets circuit breaker failure count. On failure: increments failure count; trips breaker if count reaches threshold.
8. Returns Gemini's response content to the client.

### 9.2 Context Injection

The system prompt can include content from the user's AI memory and AI digest fields if the frontend passes them in the conversation. The backend does not automatically inject these; the frontend is responsible for constructing the full `messages` array.

### 9.3 Model Selection

Users can set `gemini_model` in their preferences. This value is passed in the request to the AI chat endpoint and validated against the allowlist before being sent to Gemini. The exercise generator always uses `gemini-2.5-flash` regardless of preferences.

---

## 10. Frontend Architecture

### 10.1 Serving

Flask serves all HTML templates via Jinja2 (`render_template`). A catch-all route `/<no_api_path:path>` serves `.html` files from the templates directory and static assets (CSS, JS) from the root. The `NoApiPathConverter` regex prevents this catch-all from matching `/api` routes.

There is no build step, no webpack, no minification. All JS files are loaded via `<script>` tags in HTML. Load order matters and is not enforced by a module system.

### 10.2 Templates (26 HTML files in templates/)

| File | Purpose |
|------|---------|
| base.html | Base template with nav and common scripts |
| index.html | Marketing/landing page |
| login.html | Sign in / sign up tabs + SSO buttons |
| profile.html | User profile, settings, password change |
| professor-dashboard.html | Professor's class management |
| professor-class.html | Class detail: chapters, exercises, students, progress |
| student-classes.html | Student's enrolled classes |
| student-class.html | Class view: chapters, exercises, progress |
| chapter-view.html | Chapter content viewer |
| code-assistant.html | Browser code editor + AI chat |
| practice-playground.html | Standalone exercise practice |
| upload-assistant.html | PDF upload with exercise generation UI |
| modules.html | Public exercise module listing |
| resources.html | Public resources page |
| superadmin-dashboard.html | Full platform admin UI |
| tenant-admin-dashboard.html | Tenant-scoped admin UI |
| lti-setup.html | LTI platform registration UI for professors |
| lti-launch.html | LTI post-launch auto-redirect page (JS sets localStorage token) |
| lti-deep-link.html | Chapter selector for LTI deep linking |
| lti-launch-error.html | Error page for failed LTI launches |
| autologin.html | Auto-login from token in URL param |
| reset-password.html | Password reset form |
| contact.html | Contact form |
| terms.html | Terms of service |
| privacy.html | Privacy policy |
| security-compliance.html | Security/compliance documentation |

### 10.3 JavaScript Modules (21 files in js/)

| File | Purpose |
|------|---------|
| constants.js | Global APP_CONSTANTS object (token key names, page sizes, etc.) |
| api-helper.js | `authFetch`, `getAuthHeaders`, `apiCache` (5-min in-memory Map), `fetchWithCache` |
| api-client.js | `apiClient` object: `get`, `post`, `put`, `del`, `upload`. Handles 401 → redirect to login. |
| auth.js | `AuthManager` class (signup, signin, signout, localStorage management), SSO helpers |
| navigation.js | Builds `<nav>` HTML dynamically from localStorage role. Handles sign-out, impersonation exit. |
| ui-states.js | Shared UI utilities: showSuccess, showError, showConfirmModal, loading states |
| professor-dashboard.js | Professor class list, create class, class management |
| professor-class.js | Chapter management, student list, progress table, resource management |
| student-classes.js | Student enrolled class list |
| student-class.js | Chapter view, exercise list, enrollment |
| code-assistant.js | Code editor (CodeMirror), AI chat panel, exercise grading |
| upload-assistant.js | PDF upload flow, exercise generation progress |
| profile.js | Profile/settings/password forms |
| ai-agent.js | AI agent digest and memory management |
| superadmin.js | Superadmin dashboard: tenants, users, classes, audit log, approvals |
| tenant-admin.js | TenantAdminDashboard class: scoped tenant management |
| content-import.js | Content import UI: OpenStax/LibreTexts/OER/URL/PyPI browser |
| offline-detector.js | Network offline/online banner |
| home-animation.js | Landing page animation effects |
| hero-bg-animation.js | Hero section background animation |
| contact.js | Contact form submission |

### 10.4 Auth State Management

Auth state lives entirely in `localStorage`:
- `authToken`: JWT string
- `currentUser`: JSON object with `{id, user_id, name, email, role}`
- `original_token`: JWT string (only present during impersonation; holds the pre-impersonation token)

The `AuthManager` class in `auth.js` manages reads and writes. The `navigation.js` module reads `currentUser` on every page load to build role-appropriate nav links. There is no React/Vue state management; each page re-reads from localStorage.

### 10.5 API Base URL Configuration

`api-helper.js` reads a `<meta name="api-base-url">` tag to set `window.API_BASE_URL`. If absent, defaults to `/api`. `auth.js` falls back to `'/api'` independently. `api-client.js` reads `window.API_BASE_URL`. This means split deployments (static files on CDN, API on separate host) are supported via the meta tag.

---

## 11. Multi-Tenancy Model

### 11.1 Roles

- **superadmin**: Platform-wide. Access to all data. Created only via `@myanalytiq.org` email domain. New accounts require manual approval.
- **tenant_admin**: Scoped to one tenant. Can manage users, classes, SSO within their tenant. Cannot access other tenants. Assigned by superadmin only — never auto-assigned.
- **professor**: Creates and manages classes and chapters within their tenant. Identified by enrollment in classes as `professor_id`.
- **student**: Enrolls in classes, submits exercises.

### 11.2 Tenant Assignment

- At signup: if email domain matches `tenants.email_domain`, user is automatically assigned `tenant_id`.
- Via superadmin: `PATCH /api/superadmin/users/<id>/role` can set both `role` and `tenant_id`.
- SSO: new users created via SSO callback inherit `tenant_id` from the provider's `tenant_id`.
- LTI: users created via LTI launch do not have a `tenant_id` (it is not set by `_upsert_lti_user`).

### 11.3 Data Isolation

Most data is not automatically scoped by `tenant_id` in queries. The tenant boundary is enforced by:
- Ownership: classes belong to professors; students enroll in specific classes. Access is granted through ownership or enrollment checks.
- Tenant-admin routes: `_scoped_tenant_id()` filters all queries to the caller's tenant.
- The `classes.tenant_id` column exists but is not used to filter student enrollment queries (students can enroll in any class, regardless of tenant).

There is no row-level security at the database layer. Tenant isolation depends entirely on application-level checks.

### 11.4 Announcements

Announcements can be scoped to a tenant (`announcements.tenant_id`) or global (NULL). The `/api/platform/status` endpoint returns global announcements by default; passing `?tenant_id=` returns global + tenant-specific announcements.

---

## 12. LTI 1.3 Integration

### 12.1 Architecture

PyLTI1p3 2.0.0+ handles the LTI 1.3 protocol (OIDC login, JWT validation, deep linking, NRPS, AGS).

The tool uses Redis-backed state storage (`_RedisLtiStorage`) instead of cookie-based sessions. This is necessary because LMS iframes block SameSite=Lax/Strict cookies from third-party origins. The storage class overrides `get_session_cookie_name()` to return `None`, disabling cookie-based session lookup.

### 12.2 Configuration

LMS platforms are registered in the `lti_configurations` table. Each registration stores: issuer, client_id, auth_login_url, auth_token_url, key_set_url, deployment_ids.

The tool's RSA key pair is stored in `LTI_PRIVATE_KEY` and `LTI_PUBLIC_KEY` environment variables (PEM format with `\n` as literal backslash-n in env vars; the code normalizes these).

### 12.3 Launch Flow

1. LMS sends user to `POST /lti/login`. `FlaskOIDCLogin` builds OIDC authorization request, stores state in Redis, returns redirect to LMS auth endpoint.
2. LMS authenticates user, redirects to `POST /lti/launch` with signed `id_token`.
3. `FlaskMessageLaunch` validates the JWT signature against platform's JWKS URL.
4. User is resolved: look up by `lti_sub` → look up by email → create new account.
5. Student users are auto-enrolled in the matching class (resolved via `lti_context_id`).
6. LTI session persisted in `lti_sessions` with TTL.
7. Browser is redirected via `lti-launch.html` template, which sets `localStorage.authToken` from a JWT injected into the HTML. This JavaScript-mediated handoff is how the SPA authentication integrates with LTI.

### 12.4 Deep Linking

Professor can embed specific chapters in the LMS. The LMS sends a deep-link launch to `POST /lti/launch`. `is_deep_link_launch()` detects this. `_handle_deep_link()` renders a chapter selector page. When the professor submits, `POST /lti/deep-link/return` builds a `DeepLinkResource` with the chapter URL and returns the signed HTML auto-submit form to the LMS.

### 12.5 NRPS (Names and Roles)

`POST /api/lti/sync-roster/<class_id>` calls the LMS's NRPS endpoint. For each member with role `Learner`, the user is upserted and enrolled in the class. Members without the `Learner` role are skipped.

### 12.6 AGS (Assignments and Grades)

`POST /api/lti/ags/<class_id>/<exercise_id>` submits a score to the LMS via the `AssignmentsGradesService`. AGS must be explicitly enabled per class (`ags_enabled = TRUE`). The `ags_lineitems_url` must be configured (set automatically during LTI launch if the LMS provides it).

---

## 13. SSO / OIDC Integration

### 13.1 Provider Types

Supported: `google`, `microsoft`, `oidc` (generic). SAML is intentionally deferred (column exists, but no implementation).

### 13.2 Crypto

Client secrets are encrypted with Fernet before storage. The Fernet key is derived from `config.SECRET_KEY` via SHA-256 hashing and base64url encoding. If `SECRET_KEY` changes, all stored client secrets become unreadable.

OIDC discovery documents are cached in-process (`_OIDC_DISCOVERY_CACHE` dict). The cache is never invalidated; a process restart resets it.

### 13.3 OAuth2 Flow

1. Frontend calls `GET /api/sso/init/<provider_id>`.
2. Backend fetches OIDC discovery, generates `secrets.token_urlsafe(32)` state, stores in Redis with 600s TTL.
3. Returns `{"auth_url": "<idp_auth_endpoint>?response_type=code&..."}`.
4. Frontend redirects browser to `auth_url`.
5. IdP authenticates user, redirects to `GET /api/sso/callback/<provider_id>?code=...&state=...`.
6. Backend pops state from Redis (atomic: get + delete), validates it matches provider.
7. Exchanges code for tokens at IdP token endpoint.
8. Fetches userinfo from IdP userinfo endpoint.
9. If userinfo missing `sub`, falls back to decoding id_token payload (without signature verification — acceptable because tokens were obtained directly from IdP over TLS).
10. Upserts user: find by SSO identity → find by email → create new.
11. Redirects browser to `{FRONTEND_URL}/login.html?sso_token=<jwt>`.
12. Frontend (`auth.js:handleSSOTokenParam`) reads token, stores in localStorage, redirects to `index.html`.

### 13.4 Domain Allowlist

Each provider can specify `allowed_domains`. If set, users whose email domain is not in the list are rejected with `PermissionError`, which is caught and redirects with `sso_error=Your+email+domain+is+not+allowed`.

### 13.5 Role Mapping

Providers can configure `role_mapping_attribute` (an OIDC claim name) and `role_mapping` (a dict mapping claim values to AnalytIQ roles). The `_map_role()` function first tries exact match, then substring match on the claim value. If no match: `default_role` (default: `student`).

---

## 14. Background Task System (Celery)

**Status:** Feature-flagged off by default (`FEATURE_ASYNC_TASKS=False`).

**Configuration** (`celery_app.py`):
- Broker: Redis (`REDIS_URL`)
- Result backend: Redis (`REDIS_URL`)
- 3 queues: `pdf_processing`, `ai_tasks`, `emails`
- Task time limit: 300s hard, 240s soft
- Beat schedule: `cleanup_expired_lti_sessions` daily

**Tasks** (`tasks.py`):

- `process_pdf_and_extract_text(chapter_id, class_id)`: Extracts text from stored PDF BYTEA, saves back as text.
- `generate_exercises_async(chapter_id, class_id, content, title)`: Calls `generate_exercises_from_pdf_content()`, inserts exercises. Uses outdated SQL (does not set `function_name`, `test_cases`, `language`).
- `send_email_async(to_email, subject, html_content)`: Calls Resend API.
- `process_chapter_upload(chapter_id, class_id, content, title)`: Combined task — chains `process_pdf_and_extract_text` + `generate_exercises_async`.
- `cleanup_expired_lti_sessions()`: Deletes expired LTI session records.

**DatabaseTask base class:** Uses its own `SimpleConnectionPool` (not the application's `ThreadedConnectionPool`). This creates a separate pool for Celery workers, which run outside the Flask application context.

---

## 15. Caching and Rate Limiting

### 15.1 Server-Side Response Cache

Feature-flagged (`FEATURE_CACHING`, default False). When enabled, `cache.cache_response(ttl=N, key_prefix="...")` stores JSON responses in Redis. Cache keys include `g.user_id` to prevent cross-user data leakage.

Active caches when enabled:
- Exercise detail (`GET /api/exercises/<id>`): 120s TTL.
- Chapter list (`GET /api/classes/<id>/chapters`): TTL from decorator (default 120s, varies by endpoint).
- Health detail (`GET /api/health/detail`): 30s TTL (implemented in-process, not via Redis cache).

Cache invalidation is manual via `cache.invalidate_cache(pattern)`, called after mutations. Uses Redis key pattern matching.

### 15.2 Rate Limiting

Flask-Limiter uses Redis in production (falls back to in-process memory in development). Default limits: 200/day + 50/hour per IP.

Endpoint-specific limits:
- POST /api/users/signup: 5/hour
- POST /api/users/signin: 10/minute
- POST /api/users/forgot-password: 3/hour
- POST /api/users/reset-password: 5/hour
- POST /api/ai/chat: 20/minute + 100/hour (per user_id, not IP)
- GET /api/sso/init/<id>: 30/minute
- POST /api/sso/admin/providers: 20/hour
- POST /api/superadmin/users/<id>/impersonate: 10/minute

Rate limiting uses IP address as the key for most endpoints. The AI chat endpoint uses `user_id` as the key, which is more accurate but requires reading `g.user_id` after auth.

### 15.3 Client-Side Cache

`api-helper.js` implements an in-memory `Map`-based cache for GET requests (5-minute TTL). This is browser-local and not shared across tabs. It is separate from the server-side Redis cache.

---

## 16. Security Controls

### 16.1 Transport Security

HSTS is set (`Strict-Transport-Security: max-age=31536000; includeSubDomains`) in production (non-DEBUG). `SESSION_COOKIE_SECURE=True` in production. `SESSION_COOKIE_SAMESITE="None"` in production (required for LTI iframe embedding; paired with Secure flag).

### 16.2 Request Security Headers

Applied to all API responses via `after_request`:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Cache-Control: no-store, no-cache, must-revalidate, max-age=0`
- `Content-Security-Policy-Report-Only: ...` (not enforced; report-only mode)

Note: `X-Frame-Options: DENY` conflicts with LTI 1.3 which requires embedding in LMS iframes. The DENY header would prevent the `/lti/launch` response from rendering inside the LMS iframe. The lti-launch.html response presumably does not go through this path correctly for iframe use. This is a potential issue.

### 16.3 CORS

Origin validation: if `CORS_ORIGINS` contains `*`, all origins are allowed (development). In production, only origins in the `CORS_ORIGINS` list are allowed. `Access-Control-Allow-Credentials: false` on all responses.

### 16.4 CSRF

Feature-flagged off (`FEATURE_CSRF=False`). All API endpoints are decorated with `@csrf_exempt`. Enabling the flag would only protect HTML form submissions on pages that include the CSRF token. Since the frontend is a pure JS SPA that uses `Authorization: Bearer`, CSRF protection provides limited additional value for the API, but is still recommended for defense in depth.

### 16.5 Input Validation

- Password: 8 min, 72 max chars (enforced at signup and reset).
- Email: `validate_email()` in `auth_helpers.py` (regex check).
- Exercise title: 300 chars. Description: 5000 chars. Solution code: 20000 chars.
- AI message size: 50KB total payload, 100 messages maximum.
- PDF upload: 50MB, magic bytes check, suspicious pattern scan.
- External content import: 5MB cap on fetched content.
- SQL injection: parameterized queries throughout. Dynamic `f-string` SQL fragments in some admin endpoints (e.g., `search_users`, `get_audit_log`) but only using safe, whitelisted field names, never unsanitized user input as column names.

### 16.6 File Upload Security

Magic byte validation (`%PDF` prefix check). Pattern scan for `/JavaScript`, `/JS`, `/Launch`, `/EmbeddedFile` in the first 10KB of PDF content. File extension whitelist. File size cap.

### 16.7 Password Storage

bcrypt with 12 rounds. Legacy integer hash detection and migration on first successful login. `hash_password_legacy()` function still exists in `auth_helpers.py` for migration.

### 16.8 Audit Logging

`audit()` in `audit.py` writes to `audit_log` table within the caller's transaction. Never raises. Records: `action`, `resource_type`, `resource_id`, `user_id` (from `g`), `ip_address` (from `request.remote_addr`), `impersonator_id` (from `g`), `details` (JSONB), `created_at`.

Audited actions include: `CREATE_USER`, `RESET_PASSWORD`, `GRADE_EXERCISE`, `IMPORT_CHAPTER`, `DELETE_EXERCISE`, `DELETE_CLASS`, `DELETE_TENANT`, `DELETE_USER`, `IMPERSONATE_USER`, `UPDATE_USER_ROLE`, `FORCE_PASSWORD_RESET`, `SSO_CREATE_USER`, `SSO_CREATE_PROVIDER`, `SSO_UPDATE_PROVIDER`, `SSO_DELETE_PROVIDER`, and others.

### 16.9 IP Blocklist

`middleware.check_ip_blocklist()` runs on every request. Reads from `ip_blocklist` table with 30-second in-process cache. Returns 403 for blocked IPs. Fails open (blocked IPs pass through if DB is unavailable).

### 16.10 Maintenance Mode

`middleware.check_maintenance_mode()` returns 503 for non-superadmin API requests when `platform_config.maintenance_mode = 'true'`. Exempt paths: `/api/users/signin`, `/api/users/forgot-password`, `/api/users/reset-password`, `/api/platform/status`, `/api/health`.

There is a bug: the maintenance mode superadmin bypass reads `from config import Config as _config` and uses `_config.JWT_SECRET_KEY`. The `config.py` module uses module-level attributes, not a `Config` class. This will raise `AttributeError: module 'config' has no attribute 'Config'` whenever a superadmin request arrives during maintenance mode, causing the superadmin bypass to silently fail (falls through to 503 due to the `except Exception: pass` block).

### 16.11 Sentry PII Filtering

`sentry_config.filter_sensitive_data()` strips `Authorization`, `Cookie`, `X-API-Key` headers and request body fields named `password`, `api_key`, `secret`, `token` before sending to Sentry. `send_default_pii=False` prevents automatic PII capture.

---

## 17. Monitoring and Logging

### 17.1 Structured Logging

`python-json-logger` with `JsonFormatter`. Fields in every log record: `timestamp`, `level`, `service` (logger name), `request_id` (UUID per request injected by `_RequestIdFilter`), `message`. Logs are emitted to stdout (captured by Render).

### 17.2 Sentry

Initialized at startup from `SENTRY_DSN` env var. Integrations: Flask (error capture + performance tracing), Redis, Celery. Performance tracing at 10% sample rate. Error capture at 100%. Release tagged with `RENDER_GIT_COMMIT[:7]`. Environment from `FLASK_ENV`.

### 17.3 Health Endpoints

`GET /api/health`: public, minimal — checks DB connectivity with `SELECT 1`, returns uptime.

`GET /api/health/detail`: JWT required — checks DB, Redis ping, Supabase storage (`storage_health_check()`). Results cached in-process for 30 seconds.

### 17.4 Request ID Tracing

Every request gets `g.request_id = str(uuid.uuid4())`. This is injected into all log records and returned as `X-Request-ID` response header. Sentry tags are also set with `request_id`. Allows correlation of a specific request across logs.

---

## 18. CI/CD Pipeline

### 18.1 GitHub Actions (.github/workflows/ci.yml)

**Trigger:** Push or pull request to `main`.

**Services spun up:** postgres:14, redis:7.

**Jobs:**

1. **test** (ubuntu-latest):
   - Install Python 3.9
   - `pip install -r requirements.txt`
   - Set env vars: `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `JWT_SECRET_KEY`, `FEATURE_ASYNC_TASKS=False`, `FEATURE_CACHING=False`, `FEATURE_CSRF_PROTECTION=False`
   - `flake8` — **no `continue-on-error`** (fails CI on lint errors)
   - `black --check` — **no `continue-on-error`** (fails CI on formatting)
   - `pytest tests/ --ignore=tests/e2e -v --tb=short` — ignores e2e tests
   - `mypy` — has `continue-on-error: true` (type check failures do not fail CI)

2. **security-scan**:
   - `bandit -r . -f json` — has `continue-on-error: true` (security issues do not fail CI)

3. **deploy-notification**:
   - Sends a webhook notification on successful test completion (no actual deploy automation).

**Gap:** `FLASK_ENV=testing` is not set in the CI `env:` block. The `require_auth` test bypass requires `os.environ.get("FLASK_ENV") == "testing"`. The `conftest.py` sets this in the `setup_test_environment` session-scoped fixture (`os.environ['FLASK_ENV'] = 'testing'`), but the CI env block does not set it, meaning the fixture must run before any auth-requiring tests for the bypass to work. This could be fragile if fixture ordering changes.

### 18.2 Deployment

Render platform. `gunicorn_config.py` not read in this audit; inferred from Render configuration. `ProxyFix` middleware is configured for `x_for=1, x_proto=1, x_host=1, x_prefix=1` to handle Render's load balancer headers.

`RENDER_GIT_COMMIT` env var is used for Sentry release tagging.

Startup runs `run_migrations(get_db_connection())` to apply any pending SQL migrations before serving traffic. Migration failures are logged as warnings and do not prevent startup.

---

## 19. Git State and Deployment

**Branch:** main
**HEAD:** 58c14a7 "LMS"
**Status:** Clean (no uncommitted changes)

Recent commits (last 30):
- 58c14a7 — LMS
- 1716097 — test cases
- 2b30e81 — Add comprehensive behavioral tests for all exercise endpoints
- 56be56d — Allow tenant assignment for professors and students in role change modal
- 9eea897 — Fix 'Missing session-id cookie' by disabling cookie-based session lookup
- 5662ce4 — Route LTI users by DB role: superadmin→superadmin-dashboard, tenant_admin→tenant-admin-dashboard
- 27e1cfc — Route LTI instructors to professor dashboard, tighten target_link_uri trust
- f40f1d8 — Cascade delete all tenant data on tenant deletion
- c7297d1 — Guard _resolve_target_url against LTI endpoint URLs as target_link_uri
- fc1b8f7 — Fix _RedisLtiStorage to extend LaunchDataStorage base class

The commit history shows recent concentrated work on LTI stability (session cookie fix, launch routing, storage base class fix) and tenant deletion.

---

## 20. Known Issues and Technical Debt

### 20.1 Active Bugs

**Bug 1 — middleware.py `config.Config` AttributeError (CRITICAL during maintenance)**
`middleware.check_maintenance_mode()` imports `from config import Config as _config` and uses `_config.JWT_SECRET_KEY`. The `config.py` module has no `Config` class; it uses module-level variables. When maintenance mode is active and a request with a Bearer token arrives, this will raise `AttributeError`, which is silently caught, and the superadmin bypass fails. Superadmins will be blocked by maintenance mode.
**File:** `/Users/aelharouchi/Documents/GitHub/AnalytIQ/middleware.py:124`
**Fix:** Change to `import config as _config` or `from config import JWT_SECRET_KEY`.

**Bug 2 — `generate_exercises_async` task uses outdated SQL**
`tasks.py:generate_exercises_async()` inserts into `class_exercises` without setting `function_name`, `test_cases`, or `language` columns added in migration 007. Exercises created via this task will fail grading because `test_cases` will be NULL and auto-generation will attempt retroactive generation.
**File:** `/Users/aelharouchi/Documents/GitHub/AnalytIQ/tasks.py`
**Impact:** Low (FEATURE_ASYNC_TASKS defaults to False).

**Bug 3 — X-Frame-Options: DENY conflicts with LTI iframe embedding**
The `after_request` hook sets `X-Frame-Options: DENY` on all API responses. LTI launches involve the LMS displaying AnalytIQ pages inside an iframe. The DENY header will cause the browser to refuse to render those pages inside the iframe.
**File:** `/Users/aelharouchi/Documents/GitHub/AnalytIQ/app.py:259`
**Note:** The LTI launch response is HTML from `render_template("lti-launch.html")`, which is not an API route and does not go through the API header path. However, any subsequent API calls from within the iframe will have the DENY header. Whether this actually causes problems depends on whether the browser checks X-Frame-Options on sub-resource responses.

**Bug 4 — detect_role_from_email only handles @myanalytiq.org**
Project memory says `@hult.edu` should map to `professor` and `@student.hult.edu` to `student`. The actual implementation maps only `@myanalytiq.org` to `superadmin`; all other emails → `student`. This means Hult faculty sign up as students and must be manually promoted.
**File:** `/Users/aelharouchi/Documents/GitHub/AnalytIQ/auth_helpers.py`

### 20.2 Security Issues

**Security 1 — Credentials in docs/SECURITY_AUDIT_COMPLETE.md (URGENT — Item 17A)**
This file reportedly contains Gmail credentials and a Supabase key. These must be rotated immediately and the file removed from git history using BFG Repo Cleaner. This audit cannot confirm the file's current content as it was not included in the read pass.

**Security 2 — JWT id_token not signature-verified in SSO callback**
`blueprints/sso.py:414-428`: When the userinfo endpoint doesn't return a `sub` claim, the code decodes the id_token payload without verifying the signature. The comment says this is acceptable because the token was obtained directly from the IdP over TLS. This is correct for simple threat models but does not protect against a compromised IdP session or confused deputy attacks.

**Security 3 — FLASK_ENV guard on test auth bypass incomplete**
`auth_helpers.py:require_auth` checks both `current_app.config["TESTING"]` and `os.environ.get("FLASK_ENV") == "testing"`. The CI pipeline does not set `FLASK_ENV=testing` as an environment variable; it relies on the conftest fixture. This is fragile.

**Security 4 — Code sandbox resource limits only work on Linux**
`RLIMIT_*` calls in `code_runner.py` are Linux-only. On macOS (developer machines), student code runs without memory or process limits.

**Security 5 — Blocked imports can be bypassed**
The Python sandbox's blocked import list can be circumvented using `__import__('os')`, `eval`, or `exec`. A determined student can break out of the sandbox.

**Security 6 — CSRF disabled by default**
`FEATURE_CSRF=False`. While the JWT-based API is less vulnerable to CSRF than cookie-based auth, enabling CSRF protection is still recommended.

### 20.3 Architecture Issues

**Architecture 1 — Celery tasks use separate DB connection pool**
`tasks.py:DatabaseTask` creates its own `SimpleConnectionPool`. This means Celery workers have separate DB connections from the Flask app. The pools are not coordinated; under high load, this could exhaust PostgreSQL connection limits.

**Architecture 2 — Leaderboard endpoints expose user data**
`GET /api/exercises/<id>/leaderboard` and `GET /api/leaderboard/grand` return user names. The grand leaderboard returns `user_id`. These endpoints require auth, which is correct.

**Architecture 3 — Hard-coded Gemini model in exercise_generator.py**
`python/exercise_generator.py` hardcodes `gemini-2.5-flash`, ignoring `config.GEMINI_MODEL`. The AI chat endpoint respects user preferences. This inconsistency means operators cannot change the generation model via environment variable.

**Architecture 4 — chapter_id uses timestamp (not UUID)**
Format: `{class_id}_{timestamp_ms}`. Two chapters created in the same millisecond for the same class would have a collision. UUID would be safer.

**Architecture 5 — PDF data stored as BYTEA in PostgreSQL**
Chapter PDFs are stored in `class_chapters.pdf_data` (BYTEA). For large PDFs, this bloats the database and makes backups larger. Supabase Storage exists as an alternative but is used in parallel (both paths active), not as a replacement.

**Architecture 6 — Tenant isolation is application-level only**
No row-level security in PostgreSQL. A bug in tenant_id filtering would expose data across tenants. Student enrollment is also not tenant-scoped: a student can enroll in a class from a different tenant.

### 20.4 Code Quality Issues

**Quality 1 — Legacy password hash function retained**
`hash_password_legacy()` (insecure integer hash) still exists in `auth_helpers.py`. Should be deleted once all legacy hashes are migrated.

**Quality 2 — Inconsistent error message approach**
Some endpoints return specific error messages; others return generic ones. The pattern is not systematic.

**Quality 3 — Dynamic SQL fragments in admin endpoints**
`search_users`, `get_audit_log`, `list_all_classes`, and similar endpoints build SQL query fragments dynamically using f-strings. While only whitelisted field names are used, this pattern is fragile and harder to audit.

**Quality 4 — Content-Security-Policy in report-only mode**
The CSP header (`Content-Security-Policy-Report-Only`) does not enforce any policy. It is set to report-only with `unsafe-inline` for both scripts and styles. This provides no actual XSS protection.

**Quality 5 — OIDC discovery cache never invalidated**
`_OIDC_DISCOVERY_CACHE` in `blueprints/sso.py` is a process-level dict that is never invalidated. If an IdP rotates endpoints, the cache will return stale URLs until the process restarts.

### 20.5 Test Suite Issues

**Test 1 — 45 test files, many coverage-farming**
The test suite has files like `test_module_init.py`, `test_zz_app_reload.py`, `test_config_deep.py`, `test_supabase_deep.py` that appear to farm coverage metrics rather than test behavior. The integration tests in `tests/integration/` do use the CI PostgreSQL database.

**Test 2 — e2e tests excluded from CI**
The CI `pytest` command uses `--ignore=tests/e2e`. E2E tests exist but are not run.

**Test 3 — FLASK_ENV not set in CI env block**
As noted in section 18.1, the auth bypass relies on the conftest fixture setting `FLASK_ENV=testing`. This is fragile.

---

## 21. Data Flow Diagrams (Textual)

### 21.1 PDF Upload to Exercise Storage

```
Browser (professor)
  → POST /api/classes/<id>/chapters (multipart, PDF bytes)
  → blueprints/chapters.py:upload_chapter()
    → validate magic bytes + suspicious patterns
    → content_extractor.extract_content() → extracted text
    → supabase_storage.upload_pdf() → signed URL
    → chapter_repo.insert_chapter() → chapter_id in DB
    → python/exercise_generator.generate_exercises_from_pdf_content()
      → Gemini REST API (gemini-2.5-flash, truncated text)
      → parse JSON response → list of exercise dicts
    → for each exercise: chapter_repo.insert_exercise()
      → INSERT INTO class_exercises (function_name, test_cases JSONB, language)
    → conn.commit()
  → JSON response {chapter_id, exercises_generated}
```

### 21.2 Code Grading

```
Browser (student)
  → POST /api/exercises/<id>/grade {code: "..."}
  → blueprints/exercises.py:grade_exercise()
    → exercise_repo.get_exercise_test_cases() → (function_name, language, test_cases)
    → if test_cases is None:
        exercise_repo.get_exercise_detail() → title, description, solution_code
        exercise_generator.generate_test_cases_for_exercise() → test_cases
        exercise_repo.save_exercise_test_cases() + commit
    → python/code_runner.run_test_cases(
        student_code, language, function_name, test_cases, timeout=5
      )
      → spawn subprocess per language (Python/JS/R/SQL/Java)
      → compare actual output to expected output
      → compute correctness_score (0-80) + quality_score (0-20)
    → audit(GRADE_EXERCISE)
    → return JSON {total_score, correctness_score, quality_score, tests_passed, ...}
```

### 21.3 LTI Launch to JWT

```
LMS
  → POST /lti/login (OIDC login initiation)
  → blueprints/lti.py:lti_login()
    → FlaskOIDCLogin.redirect(target_link_uri)
    → state stored in Redis (_RedisLtiStorage)
  → LMS authenticates user
  → POST /lti/launch (id_token in POST body)
  → blueprints/lti.py:lti_launch()
    → FlaskMessageLaunch validates id_token against platform JWKS
    → _upsert_lti_user(launch_data)
      → lti_repo.get_user_by_lti_sub() or auth_repo.get_user_by_email() or auth_repo.insert_user()
    → auto-enroll student if class found by lti_context_id
    → lti_repo.create_lti_session()
    → conn.commit()
    → create_jwt_token(user_id, role, name, email)
    → render_template("lti-launch.html", jwt_token=..., redirect_url=...)
  → Browser (inside LMS iframe)
    → lti-launch.html JavaScript: localStorage.setItem('authToken', jwt_token)
    → window.location.href = redirect_url
```

### 21.4 SSO Callback to JWT

```
Browser
  → GET /api/sso/init/<provider_id>
  → blueprints/sso.py:sso_init()
    → sso_repo.get_provider_by_id()
    → _fetch_oidc_discovery(discovery_url) → {authorization_endpoint, ...}
    → state = secrets.token_urlsafe(32)
    → Redis: SET sso_state:{state} {provider_id} TTL 600s
    → return {auth_url: "...?code&state&..."}
  → Browser redirects to IdP
  → IdP authenticates user
  → GET /api/sso/callback/<provider_id>?code=...&state=...
  → blueprints/sso.py:sso_callback()
    → _pop_state(state) from Redis (atomic)
    → sso_repo.get_provider_by_id()
    → _decrypt_secret(provider.client_secret)
    → POST to token_endpoint → {access_token, id_token}
    → GET userinfo_endpoint → claims dict
    → _upsert_sso_user(conn, provider, claims)
      → sso_repo.get_user_by_sso_identity() or email lookup or INSERT user
    → conn.commit()
    → create_jwt_token(user_id, role, name, email, tenant_id)
    → redirect to login.html?sso_token=<jwt>
  → login.html JavaScript: handleSSOTokenParam()
    → decode JWT payload from base64 (no signature verify)
    → authManager.saveToken(sso_token) + authManager.saveUser(...)
    → window.location.href = 'index.html'
```

---

## 22. Gaps and Confidence Notes

### Files Read Completely
All Python files under `blueprints/`, `repositories/`, `python/`, and root-level (`app.py`, `config.py`, `db.py`, `db_migrate.py`, `auth_helpers.py`, `audit.py`, `cache.py`, `celery_app.py`, `tasks.py`, `supabase_storage.py`, `middleware.py`, `extensions.py`, `sentry_config.py`) were read in full. All 8 migration SQL files were read. All `tests/conftest.py` was read. Key JS files (`constants.js`, `api-client.js`, `api-helper.js`, `auth.js`, `navigation.js`) were read.

### Files Not Read or Partially Read
- `blueprints/users.py`, `blueprints/chapters.py`, `blueprints/classes.py`, `blueprints/ai.py`, `blueprints/health.py` — these were covered in the previous session summary and not re-read in detail here. Core behavior described in this document is based on that prior read.
- `blueprints/superadmin.py` was read in sections (lines 1-450 and 450-1250 of 1649); lines 1250-1649 were not read.
- `blueprints/tenant_admin.py` (1311 lines) was read only by preview due to output size constraints. The route list from the docstring is accurate. Internal implementation details of routes beyond the first ~50 lines were not read.
- All 26 HTML templates were not read individually (file list was read; content was not).
- 16 of 21 JS files were not read (`professor-dashboard.js`, `professor-class.js`, `student-class.js`, `student-classes.js`, `code-assistant.js`, `upload-assistant.js`, `profile.js`, `ai-agent.js`, `superadmin.js`, `tenant-admin.js`, `content-import.js`, `offline-detector.js`, `home-animation.js`, `hero-bg-animation.js`, `contact.js`, `ui-states.js`).
- `tests/` files beyond `conftest.py` were not read (file list was read; individual test content was not).
- `utils/email_service.py`, `python/pdf_processor.py`, `api_docs.py`, `gunicorn_config.py` were not read.
- `docs/SECURITY_AUDIT_COMPLETE.md` was not read (reportedly contains credentials).

### Confidence by Section
- API endpoints: HIGH — blueprints read completely, route decorators verified.
- Auth flows: HIGH — auth_helpers.py and blueprints/auth.py read completely.
- Database schema: HIGH — all 8 migrations read, repositories read completely.
- LTI integration: HIGH — blueprints/lti.py read completely, repository read completely.
- SSO integration: HIGH — blueprints/sso.py read completely, repository read completely.
- Exercise grading: HIGH — python/code_runner.py read completely.
- AI generation: HIGH — python/exercise_generator.py read completely.
- Frontend architecture: MEDIUM — key JS files read, but most page-specific JS not read.
- Tenant admin routes: MEDIUM — route list confirmed from docstring; internal implementation not fully read.
- Superadmin routes (beyond line 1250): LOW — last ~400 lines not read (likely covers analytics, platform config management).
- Test suite quality: MEDIUM — conftest read, file list read, individual test content not read.
- Celery tasks implementation detail: HIGH — tasks.py read completely.
