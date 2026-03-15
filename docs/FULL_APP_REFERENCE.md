# AnalytIQ — Full Application Reference

> **Generated:** 2026-03-06
> **Status:** Authoritative single-source-of-truth for the entire codebase. Every section is derived from reading the actual source files — nothing is fabricated.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [File and Folder Structure](#2-file-and-folder-structure)
3. [Tech Stack](#3-tech-stack)
4. [Database Schema](#4-database-schema)
5. [Authentication and Authorization](#5-authentication-and-authorization)
6. [Complete API Endpoints Reference](#6-complete-api-endpoints-reference)
7. [Frontend Pages](#7-frontend-pages)
8. [JavaScript Modules](#8-javascript-modules)
9. [Feature Deep Dives](#9-feature-deep-dives)
10. [Security](#10-security)
11. [Configuration and Environment Variables](#11-configuration-and-environment-variables)
12. [Background Tasks](#12-background-tasks)
13. [Testing](#13-testing)
14. [CI/CD Pipeline](#14-cicd-pipeline)
15. [Deployment](#15-deployment)
16. [Key Architectural Decisions](#16-key-architectural-decisions)
17. [Known Limitations and Future Work](#17-known-limitations-and-future-work)

---

## 1. Project Overview

AnalytIQ is a data analytics education platform built for university courses. Professors upload PDF chapters, the platform uses Google Gemini AI to auto-generate Python coding exercises from the content, and students practice in a browser-based code environment with live leaderboards.

**Live URL:** https://myanalytiq.org
**Backend:** Flask 3.0.0 (Python 3.9), deployed on Render.com
**Database:** PostgreSQL via Supabase
**Storage:** Supabase Storage (PDFs)
**Cache/Queue:** Redis + Celery
**AI:** Google Gemini API (gemini-2.5-flash for exercise generation, configurable model for chat)

### Role Hierarchy

| Role | Description |
|---|---|
| `superadmin` | Platform-wide administrator. Full access to all tenants, users, and platform configuration. Auto-assigned to `@myanalytiq.org` email addresses at signup. |
| `tenant_admin` | Organization-scoped administrator. Same capabilities as superadmin but limited to their assigned tenant. NEVER auto-assigned — superadmin must set it explicitly via API. |
| `professor` | Creates and manages classes, uploads chapters, generates exercises, views student progress. Auto-assigned to `@hult.edu` and `@faculty.hult.edu` email addresses. |
| `student` | Enrolls in classes, completes exercises, appears in leaderboards. Default role for all other email addresses. |

### Platform Concepts

- **Tenant:** An organization (university, department). Each tenant has its own users, SSO providers, and admin. A user belongs to at most one tenant.
- **Class:** A course created by a professor. Students enroll via a class code.
- **Chapter:** A PDF (or other document) uploaded to a class. Stored as binary in PostgreSQL and optionally in Supabase Storage.
- **Exercise:** A coding problem auto-generated from chapter PDF content via Gemini AI, or manually created by a professor.
- **Practice Progress:** Per-user, per-exercise record of best score, accuracy, attempts, and completion.

---

## 2. File and Folder Structure

```
AnalytIQ/
├── app.py                          # Flask app factory (484 lines)
├── config.py                       # All environment variables with defaults (304 lines)
├── db.py                           # PostgreSQL connection pool (253 lines)
├── auth_helpers.py                 # JWT, bcrypt, role decorators (385 lines)
├── audit.py                        # FERPA audit log writer (189 lines)
├── cache.py                        # Redis cache wrapper + decorator (239 lines)
├── celery_app.py                   # Celery configuration (48 lines)
├── tasks.py                        # Async Celery tasks (294 lines)
├── extensions.py                   # Flask-Limiter, csrf_exempt helper
├── middleware.py                   # IP blocklist + maintenance mode (140 lines)
├── response_helpers.py             # api_success / api_error / api_list helpers
├── supabase_storage.py             # Supabase Storage client wrappers
├── sentry_config.py                # Sentry SDK initialization
├── gunicorn.conf.py                # Gunicorn server configuration
├── db_migrate.py                   # Idempotent SQL migration runner
├── api_docs.py                     # OpenAPI / Swagger spec generator
│
├── blueprints/
│   ├── __init__.py                 # Empty (package marker)
│   ├── auth.py                     # Signup, signin, password reset
│   ├── users.py                    # Profile, settings, conversations, AI digest/memory
│   ├── classes.py                  # Classes, enrollments, progress, leaderboards, resources
│   ├── chapters.py                 # Chapter upload, PDF serving, exercise generation
│   ├── exercises.py                # Exercise CRUD, leaderboards, progress submission
│   ├── ai.py                       # Gemini AI chat proxy with circuit breaker
│   ├── health.py                   # Health check, CSRF token, Celery task status, contact
│   ├── platform.py                 # Platform status, maintenance mode, announcements
│   ├── superadmin.py               # Full platform administration
│   ├── tenant_admin.py             # Tenant-scoped administration
│   ├── lti.py                      # LTI 1.3 integration (JWKS, login, launch, AGS, NRPS)
│   ├── sso.py                      # OAuth2/OIDC SSO (Google, Microsoft, generic OIDC)
│   └── content_import.py           # Import chapters from OpenStax, LibreTexts, OER, URLs
│
├── repositories/
│   ├── __init__.py
│   ├── auth_repository.py          # SQL for user registration, password reset tokens
│   ├── user_repository.py          # Profile, settings, conversations, digest, memory, progress
│   ├── class_repository.py         # Classes, enrollments, progress, leaderboards, resources
│   ├── chapter_repository.py       # Chapters, PDF data, exercise inserts
│   ├── exercise_repository.py      # Exercise CRUD, progress queries, leaderboards
│   ├── lti_repository.py           # LTI configurations and sessions
│   └── sso_repository.py           # SSO provider records, SSO user identity linking
│
├── python/
│   ├── exercise_generator.py       # Gemini REST call → structured exercise list
│   ├── pdf_processor.py            # PyPDF2 text extraction from bytes
│   └── content_extractor.py        # Multi-format text extractor (PDF, DOCX, CSV, ipynb, TXT)
│
├── utils/
│   ├── __init__.py                 # Pagination helpers
│   └── email_service.py            # Resend API email wrapper
│
├── migrations/
│   ├── 001_lti_tables.sql          # LTI user fields, lti_configurations, lti_sessions
│   ├── 002_superadmin_tenants.sql  # tenants table, tenant_id/account_status/is_super_admin on users
│   ├── 003_platform_features.sql   # platform_config, announcements, ip_blocklist
│   └── 004_sso_and_tenant_admin.sql# tenant_sso_providers, sso_provider_id/sso_subject on users
│
├── scripts/
│   ├── create_tables.py            # One-time base schema creation script
│   └── generate_lti_keys.py        # RSA key pair generator for LTI
│
├── templates/                      # Jinja2 HTML templates (Flask serves them)
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── autologin.html
│   ├── contact.html
│   ├── privacy.html
│   ├── terms.html
│   ├── security-compliance.html
│   ├── profile.html
│   ├── reset-password.html
│   ├── modules.html
│   ├── chapter-view.html
│   ├── code-assistant.html
│   ├── practice-playground.html
│   ├── upload-assistant.html
│   ├── resources.html
│   ├── professor-dashboard.html
│   ├── professor-class.html
│   ├── student-classes.html
│   ├── student-class.html
│   ├── superadmin-dashboard.html
│   ├── tenant-admin-dashboard.html
│   ├── lti-launch.html
│   ├── lti-launch-error.html
│   ├── lti-deep-link.html
│   └── lti-setup.html
│
├── js/                             # Vanilla JS modules (ES module-style, no bundler)
│   ├── constants.js
│   ├── api-client.js
│   ├── api-helper.js
│   ├── auth.js
│   ├── navigation.js
│   ├── ui-states.js
│   ├── offline-detector.js
│   ├── hero-bg-animation.js
│   ├── home-animation.js
│   ├── contact.js
│   ├── ai-agent.js
│   ├── code-assistant.js
│   ├── content-import.js
│   ├── upload-assistant.js
│   ├── professor-dashboard.js
│   ├── professor-class.js
│   ├── student-classes.js
│   ├── student-class.js
│   ├── profile.js
│   ├── superadmin.js
│   └── tenant-admin.js
│
├── css/
│   └── styles.css
│
├── tests/
│   ├── conftest.py                 # Shared fixtures (app, client, mock_db, redis, celery)
│   ├── test_auth.py
│   ├── test_api.py
│   ├── test_ai_routes.py
│   ├── test_chapters_routes.py
│   ├── test_classes_routes.py
│   ├── test_exercises_routes.py
│   ├── test_users_routes.py
│   ├── test_security.py
│   ├── test_tasks.py
│   ├── test_cache.py
│   ├── test_sso_routes.py
│   ├── test_tenant_admin.py
│   ├── test_superadmin_extended.py
│   ├── test_utils.py
│   ├── test_config_deep.py
│   ├── test_content_extractor.py
│   ├── test_exercise_generator.py
│   ├── test_pdf_processor.py
│   ├── test_sentry_config.py
│   ├── test_sso_repository.py
│   ├── test_supabase_storage.py
│   ├── test_supabase_deep.py
│   ├── test_tasks_comprehensive.py
│   ├── test_tasks_deep.py
│   ├── test_tasks_email.py
│   ├── test_cache_comprehensive.py
│   ├── test_integration_stress.py
│   ├── test_api_docs_coverage.py
│   ├── test_module_init.py
│   ├── test_zz_app_reload.py
│   ├── integration/
│   └── e2e/
│
├── .github/
│   └── workflows/
│       └── ci.yml                  # GitHub Actions CI pipeline
│
├── requirements.txt
├── render.yaml                     # Render.com service definitions
├── Procfile                        # Process declarations
├── gunicorn.conf.py
├── pytest.ini
├── pyproject.toml
├── .flake8
├── .pre-commit-config.yaml
└── .env.example
```

---

## 3. Tech Stack

### Backend

| Component | Version / Details |
|---|---|
| Python | 3.9 |
| Flask | 3.0.0 |
| psycopg2-binary | >=2.9.10 — PostgreSQL driver, ThreadedConnectionPool |
| gunicorn | 21.2.0 — WSGI server, 4 workers, port 10000, 300s timeout |
| PyJWT | >=2.10.1 — JWT creation and verification, HS256 algorithm |
| bcrypt | 4.1.2 — Password hashing, 12 rounds |
| Flask-Limiter | 3.5.0 — Rate limiting backed by Redis |
| Flask-WTF | — CSRF protection (disabled by default via FEATURE_CSRF flag) |
| celery | 5.3.4 — Async task queue |
| redis | 5.0.1 — Cache + Celery broker/backend |
| supabase | >=2.12.0 — Supabase Storage client |
| PyLTI1p3 | >=2.0.0 — LTI 1.3 protocol library |
| cryptography | >=41.0.0 — Fernet encryption for SSO client secrets |
| beautifulsoup4 | >=4.12.0 — HTML parsing for content import |
| resend | >=1.0.0 — Transactional email via Resend API |
| sentry-sdk[flask] | >=1.40.0 — Error monitoring |
| python-docx | >=1.1.0 — DOCX text extraction |
| markdown | >=3.5.0 — Markdown processing |
| python-dotenv | — .env file loading |
| werkzeug | — ProxyFix middleware, routing |
| python-json-logger | — Structured JSON logging |
| flask-swagger-ui | — Swagger UI at /api/docs |
| PyPDF2 | — PDF text extraction |

### Frontend

| Component | Details |
|---|---|
| HTML | 26 Jinja2 templates served by Flask |
| JavaScript | 21 vanilla JS modules (no framework, no bundler) |
| CSS | Single `styles.css` file |

### Infrastructure

| Component | Details |
|---|---|
| Hosting | Render.com (web service + worker service) |
| Database | Supabase (PostgreSQL with SSL) |
| File Storage | Supabase Storage bucket (`pdfs`) |
| Cache | Redis (rate limiting, Celery broker, SSO OAuth2 state) |
| CI/CD | GitHub Actions |
| Error Monitoring | Sentry SDK |
| DNS / CDN | Cloudflare (proxied, ProxyFix configured for x_for=1) |

---

## 4. Database Schema

### Base Tables (created by `scripts/create_tables.py`)

#### `users`

| Column | Type | Notes |
|---|---|---|
| `user_id` | VARCHAR(255) PK | UUID generated at signup (`uuid.uuid4()`) |
| `name` | VARCHAR(255) | Display name |
| `email` | VARCHAR(255) UNIQUE | Lowercase, validated against RFC 5321 pattern |
| `password_hash` | TEXT | bcrypt hash (starts with `$2`), or NULL for SSO-only users |
| `role` | VARCHAR(50) | `superadmin`, `tenant_admin`, `professor`, `student` |
| `created_at` | TIMESTAMP | Default CURRENT_TIMESTAMP |
| `updated_at` | TIMESTAMP | Updated on profile/password changes |
| `last_login` | TIMESTAMP | Set on successful signin (migration 003) |
| `requires_password_reset` | BOOLEAN | Set by admins for forced resets (migration 003) |
| `account_status` | VARCHAR(50) | `active`, `disabled`, `pending_approval` (migration 002) |
| `is_super_admin` | BOOLEAN | Legacy flag (superseded by `role = 'superadmin'`) |
| `tenant_id` | VARCHAR(255) FK → tenants | NULL for platform-level users (migration 002) |
| `lti_sub` | TEXT | LTI subject identifier (migration 001) |
| `lti_issuer` | TEXT | LTI issuer URL (migration 001) |
| `sso_provider_id` | VARCHAR(255) FK → tenant_sso_providers | (migration 004) |
| `sso_subject` | TEXT | OIDC sub/oid from the IdP (migration 004) |

#### `user_profiles`

| Column | Type | Notes |
|---|---|---|
| `user_id` | VARCHAR(255) PK/FK → users | One-to-one with users |
| `full_name` | TEXT | Extended name |
| `bio` | TEXT | User biography |
| `profile_picture` | TEXT | URL to profile image |
| `updated_at` | TIMESTAMP | |

#### `user_settings`

| Column | Type | Notes |
|---|---|---|
| `user_id` | VARCHAR(255) PK/FK → users | |
| `email_notifications` | BOOLEAN | Default true |
| `updated_at` | TIMESTAMP | |

#### `user_preferences`

| Column | Type | Notes |
|---|---|---|
| `user_id` | VARCHAR(255) PK/FK → users | |
| `current_language` | VARCHAR(50) | Preferred programming language (e.g., `python`) |
| `gemini_model` | VARCHAR(100) | Preferred Gemini model string |
| `ai_provider` | VARCHAR(50) | AI provider preference |
| `updated_at` | TIMESTAMP | |

#### `password_reset_tokens`

| Column | Type | Notes |
|---|---|---|
| `token` | VARCHAR(255) PK | `secrets.token_urlsafe(32)`, hashed for storage |
| `user_id` | VARCHAR(255) FK → users | |
| `expires_at` | TIMESTAMP | 1-hour TTL |
| `created_at` | TIMESTAMP | |

### Class Tables

#### `classes`

| Column | Type | Notes |
|---|---|---|
| `class_id` | VARCHAR(255) PK | User-supplied class code (e.g., `DATA101`) |
| `professor_id` | VARCHAR(255) FK → users | |
| `name` | VARCHAR(255) | Class display name |
| `description` | TEXT | |
| `created_at` | TIMESTAMP | |
| `updated_at` | TIMESTAMP | |
| `tenant_id` | VARCHAR(255) FK → tenants | Set when professor belongs to a tenant (migration 002) |
| `lti_context_id` | TEXT | LTI course context identifier (migration 001) |
| `ags_enabled` | BOOLEAN | Whether Assignment and Grade Services are enabled (migration 001) |

#### `class_enrollments`

| Column | Type | Notes |
|---|---|---|
| `class_id` | VARCHAR(255) FK → classes | Composite PK |
| `student_id` | VARCHAR(255) FK → users | Composite PK |
| `enrolled_at` | TIMESTAMP | Default CURRENT_TIMESTAMP |

#### `class_chapters`

| Column | Type | Notes |
|---|---|---|
| `chapter_id` | VARCHAR(255) PK | UUID |
| `class_id` | VARCHAR(255) FK → classes | |
| `title` | VARCHAR(300) | |
| `description` | TEXT | |
| `chapter_number` | INTEGER | Sequential within class, auto-incremented |
| `pdf_url` | TEXT | Supabase Storage URL (if uploaded there) |
| `pdf_filename` | VARCHAR(255) | Original filename |
| `pdf_data` | BYTEA | Binary PDF stored in database |
| `created_at` | TIMESTAMP | |
| `updated_at` | TIMESTAMP | |

#### `class_exercises`

| Column | Type | Notes |
|---|---|---|
| `exercise_id` | VARCHAR(255) PK | UUID |
| `chapter_id` | VARCHAR(255) FK → class_chapters | |
| `class_id` | VARCHAR(255) FK → classes | |
| `title` | VARCHAR(300) | |
| `description` | TEXT | Problem statement |
| `difficulty` | VARCHAR(50) | `easy`, `medium`, `hard` |
| `solution_code` | TEXT | Reference solution (shown after completion) |
| `exercise_number` | INTEGER | Sequential within chapter |
| `created_by` | VARCHAR(255) | user_id of professor (for manually created exercises) |
| `created_at` | TIMESTAMP | |

#### `class_resources`

| Column | Type | Notes |
|---|---|---|
| `resource_id` | VARCHAR(255) PK | UUID |
| `class_id` | VARCHAR(255) FK → classes | |
| `user_id` | VARCHAR(255) | Uploader's user_id |
| `title` | VARCHAR(255) | |
| `description` | TEXT | |
| `resource_type` | VARCHAR(50) | `link`, `file`, `video`, etc. |
| `resource_url` | TEXT | External URL for link resources |
| `file_data` | BYTEA | Binary file for uploaded resources |
| `filename` | VARCHAR(255) | Original filename |
| `created_at` | TIMESTAMP | |
| `updated_at` | TIMESTAMP | |

### Progress Tables

#### `practice_progress`

| Column | Type | Notes |
|---|---|---|
| `user_id` | VARCHAR(255) FK → users | Composite PK with `exercise_id` |
| `exercise_id` | VARCHAR(255) | Composite PK |
| `exercise_title` | TEXT | Denormalized for display |
| `best_score` | NUMERIC | Highest score achieved (0–100) |
| `best_accuracy` | NUMERIC | Accuracy at time of best score |
| `best_time` | NUMERIC | Time in seconds at best score run |
| `total_attempts` | INTEGER | Auto-incremented on each submission |
| `last_attempt_score` | NUMERIC | Score from the most recent attempt |
| `last_attempt_accuracy` | NUMERIC | |
| `last_attempt_time` | NUMERIC | |
| `completed` | BOOLEAN | True when `best_score >= 50` |
| `last_completed_at` | TIMESTAMP | When score first reached 50+ |
| `class_id` | VARCHAR(255) | Class context of completion |
| `class_exercise_id` | VARCHAR(255) | Maps to `class_exercises.exercise_id` |
| `updated_at` | TIMESTAMP | |

#### `exercise_attempts`

| Column | Type | Notes |
|---|---|---|
| `attempt_id` | SERIAL PK | |
| `user_id` | VARCHAR(255) FK → users | |
| `exercise_id` | VARCHAR(255) | |
| `score` | NUMERIC | |
| `accuracy` | NUMERIC | |
| `time_spent` | NUMERIC | Seconds |
| `attempt_number` | INTEGER | |
| `created_at` | TIMESTAMP | |

### AI / Conversation Tables

#### `conversations`

| Column | Type | Notes |
|---|---|---|
| `conversation_id` | VARCHAR(255) PK | UUID |
| `user_id` | VARCHAR(255) FK → users | |
| `title` | TEXT | |
| `archived` | BOOLEAN | Default false |
| `deleted` | BOOLEAN | Soft-delete flag, default false |
| `created_at` | TIMESTAMP | |
| `updated_at` | TIMESTAMP | |

#### `conversation_messages`

| Column | Type | Notes |
|---|---|---|
| `message_id` | SERIAL PK | |
| `conversation_id` | VARCHAR(255) FK → conversations | |
| `role` | VARCHAR(50) | `user` or `model` |
| `content` | TEXT | Message text |
| `message_order` | INTEGER | 0-indexed ordering within conversation |
| `created_at` | TIMESTAMP | |

#### `ai_agent_digest`

| Column | Type | Notes |
|---|---|---|
| `user_id` | VARCHAR(255) PK/FK → users | |
| `goal` | TEXT | User's current project goal |
| `constraints` | TEXT | Known constraints |
| `decisions` | TEXT | Decisions made |
| `current_state` | TEXT | Current project state |
| `open_questions` | TEXT | Outstanding questions |
| `updated_at` | TIMESTAMP | |

#### `ai_agent_memory`

| Column | Type | Notes |
|---|---|---|
| `memory_id` | SERIAL PK | |
| `user_id` | VARCHAR(255) FK → users | |
| `memory_item` | TEXT | A single stored memory string |
| `created_at` | TIMESTAMP | |

### Admin / Platform Tables

#### `tenants` (migration 002)

| Column | Type | Notes |
|---|---|---|
| `tenant_id` | VARCHAR(255) PK | UUID |
| `name` | VARCHAR(255) | Organization name |
| `domain` | VARCHAR(255) | Email domain for auto-assignment |
| `created_at` | TIMESTAMP | |
| `updated_at` | TIMESTAMP | |

#### `platform_config` (migration 003)

| Column | Type | Notes |
|---|---|---|
| `key` | VARCHAR(255) PK | Configuration key (e.g., `maintenance_mode`) |
| `value` | TEXT | Configuration value |
| `updated_at` | TIMESTAMP | |
| `updated_by` | VARCHAR(255) | user_id of last updater |

Notable keys:
- `maintenance_mode` — `"true"` or `"false"`
- `maintenance_message` — Display text shown during maintenance

#### `announcements` (migration 003)

| Column | Type | Notes |
|---|---|---|
| `announcement_id` | VARCHAR(255) PK | UUID |
| `title` | TEXT | |
| `message` | TEXT | |
| `type` | VARCHAR(50) | `info`, `warning`, `error` |
| `target_role` | VARCHAR(50) | Role to target (NULL = all) |
| `tenant_id` | VARCHAR(255) | Tenant to target (NULL = all) |
| `is_active` | BOOLEAN | |
| `created_at` | TIMESTAMP | |
| `expires_at` | TIMESTAMP | |

#### `ip_blocklist` (migration 003)

| Column | Type | Notes |
|---|---|---|
| `ip_address` | VARCHAR(50) PK | |
| `reason` | TEXT | |
| `created_at` | TIMESTAMP | |
| `created_by` | VARCHAR(255) | user_id of creator |

#### `audit_log`

| Column | Type | Notes |
|---|---|---|
| `log_id` | SERIAL PK | |
| `action` | VARCHAR(100) | Action type (see audit.py ACTIONS set) |
| `performed_by` | VARCHAR(255) | user_id of actor |
| `resource_type` | VARCHAR(100) | `user`, `class`, `chapter`, etc. |
| `resource_id` | VARCHAR(255) | ID of affected resource |
| `details` | JSONB | Additional context |
| `created_at` | TIMESTAMP | |

#### `contact_submissions`

| Column | Type | Notes |
|---|---|---|
| `id` | SERIAL PK | |
| `name` | TEXT | |
| `email` | TEXT | |
| `subject` | TEXT | |
| `message` | TEXT | |
| `created_at` | TIMESTAMP | |

#### `schema_migrations`

| Column | Type | Notes |
|---|---|---|
| `filename` | VARCHAR(255) PK | Migration filename (e.g., `001_lti_tables.sql`) |
| `applied_at` | TIMESTAMP | When migration ran |

### LTI Tables (migration 001)

#### `lti_configurations`

| Column | Type | Notes |
|---|---|---|
| `config_id` | VARCHAR(255) PK | UUID |
| `platform_name` | VARCHAR(255) | Human-readable LMS name |
| `issuer` | TEXT | LMS OIDC issuer URL |
| `client_id` | TEXT | OAuth2 client ID |
| `auth_login_url` | TEXT | OIDC initiation URL |
| `auth_token_url` | TEXT | Token endpoint |
| `key_set_url` | TEXT | JWKS URI |
| `deployment_ids` | JSONB | List of deployment ID strings |
| `tenant_id` | VARCHAR(255) | (migration 002) |
| `created_by` | VARCHAR(255) | professor or superadmin user_id |
| `created_at` | TIMESTAMP | |

#### `lti_sessions`

| Column | Type | Notes |
|---|---|---|
| `session_id` | VARCHAR(255) PK | UUID |
| `user_id` | VARCHAR(255) | |
| `class_id` | VARCHAR(255) | |
| `launch_data` | JSONB | Full LTI launch payload |
| `created_at` | TIMESTAMP | |
| `expires_at` | TIMESTAMP | Based on `LTI_SESSION_TTL` config |

### SSO Tables (migration 004)

#### `tenant_sso_providers`

| Column | Type | Notes |
|---|---|---|
| `provider_id` | VARCHAR(255) PK | UUID |
| `tenant_id` | VARCHAR(255) FK → tenants | |
| `provider_name` | VARCHAR(100) | Human-readable (e.g., "Google Workspace") |
| `provider_type` | VARCHAR(50) | `google`, `microsoft`, `oidc` |
| `client_id` | TEXT | OAuth2 client ID |
| `client_secret_enc` | TEXT | Fernet-encrypted OAuth2 client secret |
| `discovery_url` | TEXT | OIDC discovery endpoint |
| `allowed_domains` | JSONB | List of email domains allowed to use this provider |
| `role_mapping_attribute` | TEXT | OIDC claim to use for role mapping |
| `role_mapping` | JSONB | Dict mapping claim values to AnalytIQ roles |
| `default_role` | VARCHAR(50) | Fallback role if no mapping matches |
| `is_enabled` | BOOLEAN | |
| `created_at` | TIMESTAMP | |
| `updated_at` | TIMESTAMP | |

---

## 5. Authentication and Authorization

### JWT Token Structure

Tokens are created with `auth_helpers.create_jwt_token()` and verified by `auth_helpers.decode_jwt_token()`.

**Algorithm:** HS256
**Default TTL:** 168 hours (7 days), configurable via `JWT_EXPIRY_HOURS`
**Impersonation TTL:** 1 hour (short-lived, set with `expires_hours=1`)

**Payload fields:**

| Field | Always Present | Description |
|---|---|---|
| `user_id` | Yes | The authenticated user's UUID |
| `role` | Yes | One of `superadmin`, `tenant_admin`, `professor`, `student` |
| `iat` | Yes | Issued-at timestamp |
| `exp` | Yes | Expiry timestamp |
| `name` | Optional | User's display name |
| `email` | Optional | User's email address |
| `impersonator_id` | Optional | Set when a superadmin/tenant_admin is impersonating another user |
| `tenant_id` | Optional | Set for `tenant_admin` users to scope their access |

### Auth Decorators (auth_helpers.py)

#### `@require_auth`

Applied to every protected route. Execution flow:

1. Always allow `OPTIONS` requests through (preflight).
2. If `TESTING=True` AND `FLASK_ENV != production`: check for `X-Test-User-ID` header, `user_id` in query params, JSON body, or form data. If found, bypass JWT and set `g.user_id` + `g.user_role` from headers.
3. Extract `Bearer <token>` from `Authorization` header.
4. Decode and verify JWT. On success, set:
   - `g.user_id` (str)
   - `g.user_role` (str)
   - `g.user_email` (str)
   - `g.impersonator_id` (str or None)
   - `g.tenant_id` (str or None)
5. Query DB for `account_status`. Return 403 if `disabled` or `pending_approval`. Fail open on DB error.

#### `@require_role(*roles)`

Must follow `@require_auth`. Checks `g.user_role in roles`. Returns 403 if not.

```python
@require_auth
@require_role('professor', 'superadmin')
def create_class():
    ...
```

#### `@require_super_admin`

Checks `g.user_role == 'superadmin'`. Returns 403 otherwise.

#### `@require_tenant_admin`

Checks `g.user_role in ('tenant_admin', 'superadmin')`. Returns 403 otherwise.

### Password Handling

**Hashing:** `bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))`
**Verification:** `verify_password(password, hashed_password)` returns `(is_valid, needs_rehash)`.

Legacy passwords (non-bcrypt, computed via a simple integer hash) are detected by the absence of a `$2` prefix. If a legacy password is verified successfully, `needs_rehash=True` is returned and the auth blueprint automatically upgrades to bcrypt on next signin.

**Constraints:**
- Minimum length: 8 characters (`MIN_PASSWORD_LENGTH`)
- Maximum length: 72 characters (`MAX_PASSWORD_LENGTH`, bcrypt hard limit)

### Role Detection at Signup

`detect_role_from_email(email)` is called during signup:

| Email Pattern | Assigned Role |
|---|---|
| `*@myanalytiq.org` | `superadmin` |
| `*@hult.edu` | `professor` |
| `*@faculty.hult.edu` | `professor` |
| `*@student.hult.edu` | `student` |
| Everything else | `student` |

`tenant_admin` is NEVER auto-assigned. A superadmin must explicitly set it via `PATCH /api/superadmin/users/<id>/role` with `{"role": "tenant_admin", "tenant_id": "<id>"}`.

### Superadmin Account Status on Signup

When a user with `@myanalytiq.org` email signs up, their `account_status` is set to `pending_approval`. The platform owner must manually approve them in the superadmin dashboard before they can sign in.

---

## 6. Complete API Endpoints Reference

All routes support `/api/v1/` aliases automatically generated at startup by `register_api_v1_aliases()`.

Rate limiting defaults (production): 200 requests/day, 50 requests/hour.

### Auth Blueprint (`blueprints/auth.py`)

| Method | Path | Auth | Rate Limit | Description |
|---|---|---|---|---|
| POST | `/api/users/signup` | None | 5/hr | Create account. Auto-detects role from email. Superadmin signups set `pending_approval`. |
| POST | `/api/users/signin` | None | 10/min | Authenticate. Returns JWT. Migrates legacy hashes on success. |
| POST | `/api/users/forgot-password` | None | 3/hr | Generate and email password reset token (1hr TTL). |
| POST | `/api/users/reset-password` | None | 5/hr | Verify token, update password hash, delete token. |

**POST `/api/users/signup` — Request body:**
```json
{
  "name": "Alice Smith",
  "email": "alice@example.com",
  "password": "securepassword123"
}
```

**POST `/api/users/signin` — Request body:**
```json
{
  "email": "alice@example.com",
  "password": "securepassword123"
}
```
**Response:** `{"token": "<jwt>", "role": "student", "name": "Alice Smith", "user_id": "<uuid>"}`

**POST `/api/users/forgot-password` — Request body:**
```json
{"email": "alice@example.com"}
```

**POST `/api/users/reset-password` — Request body:**
```json
{
  "token": "<reset_token>",
  "new_password": "newsecurepassword"
}
```

### Users Blueprint (`blueprints/users.py`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/users/profile` | Required | Get own profile (name, email, full_name, bio, picture) |
| PUT | `/api/users/profile` | Required | Update profile fields |
| GET | `/api/users/settings` | Required | Get notification settings |
| PUT | `/api/users/settings` | Required | Update notification settings |
| PUT | `/api/users/password` | Required | Change password (requires current password) |
| DELETE | `/api/users/delete` | Required | Delete own account |
| GET | `/api/users/conversations` | Required | List conversations (paginated, supports `?archived=true`) |
| POST | `/api/users/conversations` | Required | Create or update a conversation |
| GET | `/api/users/conversations/<id>` | Required | Get conversation with messages |
| PUT | `/api/users/conversations/<id>` | Required | Update conversation (title, archived) |
| DELETE | `/api/users/conversations/<id>` | Required | Soft-delete conversation |
| POST | `/api/users/conversations/<id>/messages` | Required | Append a message to conversation |
| GET | `/api/users/ai-digest` | Required | Get AI agent digest (goal, constraints, decisions, state, questions) |
| PUT | `/api/users/ai-digest` | Required | Update AI agent digest |
| GET | `/api/users/ai-memory` | Required | Get AI memory items list |
| PUT | `/api/users/ai-memory` | Required | Replace AI memory items |
| GET | `/api/users/preferences` | Required | Get user preferences (language, model, provider) |
| PUT | `/api/users/preferences` | Required | Update user preferences |
| GET | `/api/users/practice-progress` | Required | Get all practice progress for authenticated user |
| PUT | `/api/users/practice-progress` | Required | Submit exercise attempt and update progress |

### Classes Blueprint (`blueprints/classes.py`)

| Method | Path | Auth | Role | Description |
|---|---|---|---|---|
| POST | `/api/classes` | Required | professor | Create a new class |
| GET | `/api/classes` | Required | professor/student | List classes (professor sees own, student sees enrolled) |
| GET | `/api/classes/<id>` | Required | Any | Get class details |
| PUT | `/api/classes/<id>` | Required | professor (owner) | Update class name/description |
| DELETE | `/api/classes/<id>` | Required | professor (owner) | Delete class |
| POST | `/api/classes/enroll` | Required | student | Enroll in class by class code |
| GET | `/api/classes/enrolled` | Required | student | Get enrolled classes with professor info |
| GET | `/api/classes/<id>/students` | Required | professor | List enrolled students |
| GET | `/api/classes/<id>/progress` | Required | professor | Get all students' progress for all exercises |
| GET | `/api/progress` | Required | student | Get own progress across all exercises |
| GET | `/api/students/<id>/progress` | Required | professor | Get specific student's progress for professor's classes |
| GET | `/api/classes/<id>/leaderboard/average` | Required | Any | Class average score leaderboard |
| GET | `/api/classes/<id>/leaderboard/exercise/<ex_id>` | Required | Any | Per-exercise leaderboard |
| GET | `/api/classes/<id>/resources` | Required | Any | List class resources (chapters + other) |
| POST | `/api/classes/<id>/resources` | Required | professor | Add a link resource |
| POST | `/api/classes/<id>/resources/upload` | Required | professor | Upload a file resource |
| GET | `/api/resources/<id>/download` | Required | Any | Download a resource file |
| PUT | `/api/classes/<id>/resources/<res_id>` | Required | professor | Update resource metadata |
| DELETE | `/api/classes/<id>/resources/<res_id>` | Required | professor | Delete resource |

**POST `/api/classes` — Request body:**
```json
{
  "class_id": "DATA101",
  "name": "Introduction to Data Analytics",
  "description": "Fundamentals of analytics using Python"
}
```

**POST `/api/classes/enroll` — Request body:**
```json
{"class_id": "DATA101"}
```

### Chapters Blueprint (`blueprints/chapters.py`)

| Method | Path | Auth | Role | Description |
|---|---|---|---|---|
| GET | `/api/chapters/upload-url` | Required | professor | Get presigned Supabase Storage upload URL |
| POST | `/api/classes/<id>/chapters` | Required | professor | Upload chapter (PDF/file). Optionally auto-generates exercises if `generate_exercises=true`. |
| GET | `/api/classes/<id>/chapters` | Required | Any | List chapters for a class |
| PUT | `/api/chapters/<id>` | Required | professor (owner) | Update chapter title/description |
| DELETE | `/api/chapters/<id>` | Required | professor (owner) | Delete chapter and its exercises |
| POST | `/api/chapters/<id>/generate-exercises` | Required | professor | Trigger AI exercise generation for existing chapter |
| GET | `/api/chapters/<id>/exercises` | Required | Any | List exercises for a chapter |
| POST | `/api/classes/<id>/chapters/<ch_id>/exercises` | Required | professor | Manually create an exercise |
| GET | `/api/chapters/<id>/pdf` | Required | Any | Serve PDF: returns binary if in DB, redirects to Supabase URL if stored there |

**POST `/api/classes/<id>/chapters` — Multipart form data:**
- `file`: PDF/document file (required)
- `title`: Chapter title
- `description`: Chapter description
- `generate_exercises`: `"true"` or `"false"`

**POST `/api/classes/<id>/chapters/<ch_id>/exercises` — Request body:**
```json
{
  "title": "Pandas DataFrame Filtering",
  "description": "Write a function that filters rows...",
  "difficulty": "medium",
  "solution_code": "def solution(df): return df[df['score'] > 80]"
}
```

### Exercises Blueprint (`blueprints/exercises.py`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/exercises/progress` | Required | Get all practice progress for authenticated user |
| GET | `/api/exercises/<id>/leaderboard` | Required | Get leaderboard for a specific exercise (top N by best_score) |
| GET | `/api/leaderboard/grand` | Required | Cross-platform grand leaderboard (avg score, exercises completed) |
| GET | `/api/exercises/<id>` | Required | Get exercise details |
| PUT | `/api/exercises/<id>` | Required (professor owner) | Update exercise fields |
| DELETE | `/api/exercises/<id>` | Required (professor owner) | Delete exercise |

### AI Blueprint (`blueprints/ai.py`)

| Method | Path | Auth | Rate Limit | Description |
|---|---|---|---|---|
| POST | `/api/ai/chat` | Required | 20/min, 100/hr (per user) | Proxy chat message to Gemini API with circuit breaker |

**POST `/api/ai/chat` — Request body:**
```json
{
  "messages": [
    {"role": "user", "content": "Explain pandas groupby"}
  ],
  "model": "gemini-2.5-flash",
  "conversation_id": "optional-uuid"
}
```

**Validation:**
- Payload must be under 50KB (`MAX_AI_MESSAGE_LENGTH`)
- Maximum 100 messages in `messages` array (`MAX_AI_CONVERSATION_MESSAGES`)
- Model must be in allowlist: `gemini-3-pro-preview`, `gemini-3-flash-preview`, `gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-3-pro-image-preview`

**Circuit Breaker:** After 5 consecutive Gemini API failures, the circuit opens for 60 seconds. All requests during open state return 503 immediately without calling Gemini.

### Health Blueprint (`blueprints/health.py`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/health` | None | Public health check with 30s cache. Checks DB (critical), Gemini, email, Redis, Supabase storage. |
| GET | `/api/health/detail` | Required | Full diagnostic details (all service statuses with latencies) |
| GET | `/api/csrf-token` | None | Returns CSRF token if enabled, or `{"csrf_enabled": false}` |
| GET | `/api/tasks/<task_id>` | Required | Get Celery task status and result |
| POST | `/api/contact` | None | Submit contact form (saves to `contact_submissions` table) |

**GET `/api/health` — Response:**
```json
{
  "status": "healthy",
  "services": {
    "database": "healthy",
    "gemini_api": "healthy",
    "email": "healthy",
    "cache": "healthy",
    "storage": "healthy"
  },
  "timestamp": "2026-03-06T10:00:00Z"
}
```

### Platform Blueprint (`blueprints/platform.py`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/platform/status` | None | Returns maintenance mode status and active announcements (filtered by role and tenant). Exempt from maintenance mode check itself. |

**GET `/api/platform/status` — Response:**
```json
{
  "maintenance_mode": false,
  "maintenance_message": null,
  "announcements": [
    {
      "announcement_id": "...",
      "title": "Scheduled downtime",
      "message": "...",
      "type": "warning"
    }
  ]
}
```

### Superadmin Blueprint (`blueprints/superadmin.py`)

All routes require `@require_auth + @require_super_admin` unless noted.

| Method | Path | Description |
|---|---|---|
| GET | `/api/superadmin/tenants` | List all tenants (paginated) |
| POST | `/api/superadmin/tenants` | Create a new tenant |
| PATCH | `/api/superadmin/tenants/<id>` | Update tenant name/domain |
| GET | `/api/superadmin/users` | Search/filter all users (by email, role, tenant, status). Paginated. |
| PATCH | `/api/superadmin/users/<id>/status` | Enable or disable a user account |
| PATCH | `/api/superadmin/users/<id>/role` | Set user role (and optionally tenant_id for tenant_admin) |
| DELETE | `/api/superadmin/users/<id>` | Delete user and all associated data |
| GET | `/api/superadmin/users/<id>/export` | Export user data as JSON |
| POST | `/api/superadmin/users/<id>/impersonate` | Issue 1-hour JWT impersonation token. Rate limited 10/min. |
| POST | `/api/superadmin/users/<id>/force-reset` | Force user to reset password on next login |
| GET | `/api/superadmin/contact-submissions` | List all contact form submissions |
| GET | `/api/superadmin/announcements` | List all announcements |
| POST | `/api/superadmin/announcements` | Create announcement |
| PUT | `/api/superadmin/announcements/<id>` | Update announcement |
| DELETE | `/api/superadmin/announcements/<id>` | Delete announcement |
| GET | `/api/superadmin/platform-config` | Get all platform config key-value pairs |
| POST | `/api/superadmin/platform-config` | Set a platform config value |
| GET | `/api/superadmin/ip-blocklist` | List blocked IPs |
| POST | `/api/superadmin/ip-blocklist` | Add IP to blocklist |
| DELETE | `/api/superadmin/ip-blocklist/<ip>` | Remove IP from blocklist |
| GET | `/api/superadmin/audit-log` | Get audit log (paginated, filterable) |
| GET | `/api/superadmin/classes` | List all classes across all tenants |
| PATCH | `/api/superadmin/classes/<id>/transfer` | Transfer class to different professor |
| DELETE | `/api/superadmin/classes/<id>` | Delete any class |

**POST `/api/superadmin/users/<id>/impersonate` — Response:**
```json
{
  "token": "<1-hour JWT>",
  "user_id": "<target_user_id>",
  "role": "<target_user_role>",
  "impersonator_id": "<superadmin_user_id>"
}
```

### Tenant Admin Blueprint (`blueprints/tenant_admin.py`)

All routes require `@require_auth + @require_tenant_admin`. Superadmin can browse any tenant by passing `?tenant_id=<id>` query param.

The `_scoped_tenant_id()` helper function resolves the effective tenant:
- If caller is `tenant_admin`: returns `g.tenant_id`
- If caller is `superadmin`: returns `request.args.get('tenant_id')` or requires it

| Method | Path | Description |
|---|---|---|
| GET | `/api/tenant-admin/overview` | Dashboard overview stats (user counts, class counts, pending approvals) |
| GET | `/api/tenant-admin/analytics` | Engagement analytics for the tenant |
| GET | `/api/tenant-admin/users` | List users in scoped tenant (paginated, searchable) |
| PATCH | `/api/tenant-admin/users/<id>/status` | Enable/disable user within tenant |
| PATCH | `/api/tenant-admin/users/<id>/role` | Change user role within tenant |
| POST | `/api/tenant-admin/users/<id>/force-reset` | Force password reset for user |
| GET | `/api/tenant-admin/users/<id>/export` | Export user data as JSON |
| DELETE | `/api/tenant-admin/users/<id>` | Delete user within tenant |
| POST | `/api/tenant-admin/users/<id>/impersonate` | Issue 1-hour impersonation JWT |
| GET | `/api/tenant-admin/pending-approvals` | List users with `pending_approval` status |
| PATCH | `/api/tenant-admin/pending-approvals/<id>/approve` | Approve pending user |
| PATCH | `/api/tenant-admin/pending-approvals/<id>/deny` | Deny and disable pending user |
| GET | `/api/tenant-admin/classes` | List all classes for the tenant |
| PATCH | `/api/tenant-admin/classes/<id>/transfer` | Transfer class to different professor |
| DELETE | `/api/tenant-admin/classes/<id>` | Delete a class |
| GET | `/api/tenant-admin/audit` | Audit log for tenant (paginated) |

### LTI Blueprint (`blueprints/lti.py`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/lti/jwks` | None | Tool's RSA public key as JWKS for LMS verification |
| GET | `/lti/login` | None | OIDC initiation endpoint (LMS redirects here first) |
| POST | `/lti/login` | None | OIDC initiation endpoint (POST variant) |
| POST | `/lti/launch` | None | Main LTI launch. Validates JWT, upserts user, auto-enrolls in class, stores session, renders `lti-launch.html` with JWT token. Handles deep-link launches separately. |
| GET | `/lti/setup` | professor/superadmin | Render LTI setup UI |
| GET | `/lti/config` | professor/superadmin | List all LTI platform registrations |
| POST | `/lti/config` | professor/superadmin | Register a new LMS platform |
| DELETE | `/lti/config/<id>` | professor/superadmin | Delete LTI configuration |
| GET | `/lti/config/<id>` | professor/superadmin | Get single LTI configuration details |
| POST | `/lti/deep-link/return` | None | Return signed deep-link JWT to LMS after professor selects content |
| POST | `/api/lti/sync-roster/<class_id>` | professor | Sync student roster via LTI NRPS (Names and Role Provisioning Services) |
| POST | `/api/lti/ags/<class_id>/<ex_id>` | Required | Submit grade via LTI AGS (Assignment and Grade Services) |
| POST | `/api/lti/link-class/<class_id>` | professor | Link a class to an LTI course context |
| PUT | `/api/lti/ags-toggle/<class_id>` | professor | Toggle AGS (grade passback) on/off for a class |

**LTI Launch flow:**
1. LMS redirects to `/lti/login` (OIDC initiation)
2. Tool redirects back to LMS with OIDC parameters
3. LMS POSTs signed JWT to `/lti/launch`
4. PyLTI1p3 validates the JWT signature using the JWKS from the LMS
5. User is upserted (matched by `lti_sub` + `lti_issuer`, then email, then created fresh)
6. If a class is linked to the LTI context, student is auto-enrolled
7. An LTI session is stored in DB
8. Browser renders `lti-launch.html` which stores the JWT and redirects

### SSO Blueprint (`blueprints/sso.py`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/sso/providers` | None | List enabled SSO providers for login page (safe fields only) |
| GET | `/api/sso/init/<provider_id>` | None | Begin OAuth2/OIDC flow. Rate limited 30/min. Returns `{"auth_url": "..."}`. |
| GET | `/api/sso/callback/<provider_id>` | None | OAuth2 callback. On success: redirect to `login.html?sso_token=<jwt>`. On error: redirect to `login.html?sso_error=<msg>`. |
| GET | `/api/sso/admin/providers` | tenant_admin | List SSO providers for the current tenant |
| POST | `/api/sso/admin/providers` | tenant_admin | Create SSO provider (client_secret is Fernet-encrypted before DB write) |
| PUT | `/api/sso/admin/providers/<id>` | tenant_admin | Update SSO provider |
| DELETE | `/api/sso/admin/providers/<id>` | tenant_admin | Delete SSO provider |

**SSO OAuth2 Flow:**
1. Frontend calls `GET /api/sso/init/<provider_id>`
2. Backend generates `state` token (`secrets.token_urlsafe(32)`), stores in Redis with 10-minute TTL
3. Backend returns `auth_url` with `state`, `client_id`, `redirect_uri`, scope=`openid email profile`
4. Frontend redirects browser to `auth_url`
5. IdP authenticates user, redirects to `/api/sso/callback/<provider_id>?code=...&state=...`
6. Backend validates `state` (CSRF protection), exchanges code for tokens, fetches userinfo
7. User is resolved: match by `(sso_provider_id, sso_subject)`, then by email, then created fresh
8. JWT token issued, browser redirected to `login.html?sso_token=<jwt>`

**SSO User Resolution:**
1. Lookup by `(sso_provider_id, sso_subject)` — returning user
2. Lookup by email — link SSO identity to existing account
3. Create new SSO-only user (password_hash=NULL, role from provider's role_mapping)

### Content Import Blueprint (`blueprints/content_import.py`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/import/openstax/books` | Required | List available OpenStax textbooks |
| GET | `/api/import/openstax/books/<slug>/toc` | Required | Get table of contents for an OpenStax book |
| GET | `/api/import/libretexts/libraries` | Required | List LibreTexts libraries |
| GET | `/api/import/libretexts/search` | Required | Search LibreTexts content |
| GET | `/api/import/oer/search` | Required | Search OER Commons content |
| POST | `/api/import/preview` | Required | Fetch and preview content from a URL (5MB cap) |
| POST | `/api/classes/<id>/chapters/import` | Required (professor) | Import content as a chapter. Supports sources: `openstax`, `libretexts`, `oer`, `pypi`, `github`, `url` |

Content import supports these source types:
- `openstax`: OpenStax textbook sections (fetches HTML, converts to text)
- `libretexts`: LibreTexts content pages
- `oer`: OER Commons resources
- `pypi`: Python package documentation from PyPI
- `github`: GitHub repository README or file content
- `url`: Any web URL (fetches HTML, extracts text via BeautifulSoup)

All external fetches are capped at 5MB. HTML is parsed with BeautifulSoup and converted to plain text before storage.

### Static File and Template Serving (app.py)

| Method | Path | Description |
|---|---|---|
| GET | `/` | Serve `index.html` |
| GET | `/<path>` | Serve HTML via Jinja2, static assets directly from filesystem. Excludes `/api/*` paths. |
| GET | `/api/docs` | Swagger UI (requires flask-swagger-ui) |
| GET | `/api/docs/spec.json` | OpenAPI spec JSON |

---

## 7. Frontend Pages

All pages are Jinja2 templates served by Flask. There is no client-side routing — each page is a full HTML file.

| Template File | URL Path | Description |
|---|---|---|
| `index.html` | `/` | Marketing landing page with hero animation |
| `login.html` | `/login.html` | Sign in / sign up form. Also handles `?sso_token=` param for SSO logins and `?sso_error=` for failed SSO. |
| `autologin.html` | `/autologin.html` | Auto-login page for LTI launches (reads JWT from URL, stores in localStorage) |
| `contact.html` | `/contact.html` | Contact form |
| `privacy.html` | `/privacy.html` | Privacy policy |
| `terms.html` | `/terms.html` | Terms of service |
| `security-compliance.html` | `/security-compliance.html` | Security and compliance information |
| `profile.html` | `/profile.html` | User profile, settings, preferences |
| `reset-password.html` | `/reset-password.html` | Password reset form (reads token from URL) |
| `modules.html` | `/modules.html` | Student's list of enrolled classes (redirects to student-classes for students) |
| `chapter-view.html` | `/chapter-view.html` | View a chapter's PDF and its exercises |
| `code-assistant.html` | `/code-assistant.html` | Gemini-powered coding assistant with conversation history |
| `practice-playground.html` | `/practice-playground.html` | Exercise practice environment with code editor |
| `upload-assistant.html` | `/upload-assistant.html` | AI-assisted chapter upload flow |
| `resources.html` | `/resources.html` | Class resource library |
| `professor-dashboard.html` | `/professor-dashboard.html` | Professor's dashboard: class list, analytics |
| `professor-class.html` | `/professor-class.html` | Professor's class management: chapters, exercises, students, progress |
| `student-classes.html` | `/student-classes.html` | Student's enrolled classes list |
| `student-class.html` | `/student-class.html` | Student's view of a class: chapters, exercises, leaderboard |
| `superadmin-dashboard.html` | `/superadmin-dashboard.html` | Full platform administration UI |
| `tenant-admin-dashboard.html` | `/tenant-admin-dashboard.html` | Tenant-scoped administration UI |
| `lti-launch.html` | `/lti-launch.html` | Post-LTI-launch redirect page (stores JWT, redirects to target) |
| `lti-launch-error.html` | `/lti-launch-error.html` | LTI error display page |
| `lti-deep-link.html` | `/lti-deep-link.html` | Content selection UI for LTI deep linking |
| `lti-setup.html` | `/lti-setup.html` | LTI platform configuration UI for professors |

---

## 8. JavaScript Modules

All JS is plain vanilla JavaScript. No framework (no React, Vue, Angular). No bundler (no Webpack, Vite). Files are loaded via `<script>` tags in HTML templates.

### Core / Utility Modules

#### `js/constants.js`
Defines application-wide constants: API base URL, role names, status codes, feature flags reflected from the server.

#### `js/api-client.js`
Core HTTP client. Wraps `fetch()` with:
- Automatic `Authorization: Bearer <token>` header injection from localStorage
- JSON request/response handling
- Error normalization (extracts `error` field from response JSON)
- 401 handling: clears token and redirects to login

#### `js/api-helper.js`
Higher-level API wrapper built on `api-client.js`. Provides named functions for each endpoint group (auth, classes, chapters, exercises, users, AI, etc.).

#### `js/auth.js`
Authentication utilities:
- `getToken()` / `setToken()` / `clearToken()`: localStorage management
- `getUser()`: Decodes JWT payload from stored token
- `requireAuth()`: Redirects to login if not authenticated
- `requireRole(role)`: Redirects if user's role doesn't match

#### `js/navigation.js`
Shared navigation bar rendering. Inserts nav HTML based on current role. Handles logout (clears token, redirects to login).

#### `js/ui-states.js`
Reusable loading, error, and empty state HTML generators. Used by all page modules to show consistent feedback.

#### `js/offline-detector.js`
Monitors `navigator.onLine` and shows/hides an offline banner.

#### `js/hero-bg-animation.js`
Canvas-based animated background for the landing page.

#### `js/home-animation.js`
Scroll-triggered animations on the landing page.

### Page-Specific Modules

#### `js/contact.js`
Handles contact form submission to `POST /api/contact`.

#### `js/ai-agent.js`
Implements the AI code assistant (`code-assistant.html`):
- Maintains conversation history
- Calls `POST /api/ai/chat`
- Saves/loads conversations from `GET/POST /api/users/conversations`
- Handles AI digest and memory panel

#### `js/code-assistant.js`
Practice playground (`practice-playground.html`):
- Code editor (likely CodeMirror or textarea)
- Runs code (client-side or via API)
- Submits score via `PUT /api/users/practice-progress`

#### `js/content-import.js`
Chapter import UI (`upload-assistant.html`):
- Calls content import APIs for OpenStax, LibreTexts, OER, URL sources
- Previews content before import
- Triggers `POST /api/classes/<id>/chapters/import`

#### `js/upload-assistant.js`
AI-guided PDF upload flow. Handles file selection, chapter metadata, and `POST /api/classes/<id>/chapters`.

#### `js/professor-dashboard.js`
Professor dashboard (`professor-dashboard.html`):
- Loads class list via `GET /api/classes`
- Shows class creation modal
- Displays class counts, student counts, chapter counts

#### `js/professor-class.js`
Professor class management (`professor-class.html`):
- Tab-based UI: Chapters, Exercises, Students, Progress, Resources
- Chapter upload and AI exercise generation
- Student progress visualization
- Resource management

#### `js/student-classes.js`
Student's class list (`student-classes.html`):
- Lists enrolled classes via `GET /api/classes/enrolled`
- Shows progress summary per class

#### `js/student-class.js`
Student's class view (`student-class.html`):
- Lists chapters and exercises
- Shows personal progress and leaderboard
- Links to practice playground

#### `js/profile.js`
Profile page (`profile.html`):
- Loads and updates profile, settings, preferences
- Password change form

#### `js/superadmin.js`
Superadmin dashboard (`superadmin-dashboard.html`):
- Tab-based UI: Users, Tenants, Classes, Announcements, Platform Config, IP Blocklist, Audit Log, Contact Submissions
- User management (search, filter, enable/disable, role change, impersonate, delete, export)
- Tenant CRUD
- Announcement management
- Platform maintenance mode toggle

#### `js/tenant-admin.js`
Tenant admin dashboard (`tenant-admin-dashboard.html`):
- Tab-based UI: Overview, Users, Classes, Pending Approvals, Audit Log, SSO Config
- Mirrors superadmin but scoped to tenant
- SSO provider configuration via `/api/sso/admin/providers`

---

## 9. Feature Deep Dives

### 9.1 Exercise Generation Pipeline

The exercise generation pipeline converts a PDF chapter into coding exercises using Google Gemini AI.

**Trigger paths:**
1. **Sync (at upload):** `POST /api/classes/<id>/chapters` with `generate_exercises=true`
2. **Sync (existing chapter):** `POST /api/chapters/<id>/generate-exercises`
3. **Async (Celery):** `process_chapter_upload` task calls `generate_exercises_async` sub-task when `FEATURE_ASYNC_TASKS=true`

**Step-by-step (sync path):**

1. File bytes extracted from multipart form upload
2. `content_extractor.extract_text()` dispatches to the correct extractor by file extension:
   - `.pdf` → `pdf_processor.extract_text_from_pdf_bytes()` (PyPDF2)
   - `.docx` → `python-docx` text extraction
   - `.csv` → raw text
   - `.ipynb` → cell source concatenation
   - `.txt` → raw UTF-8
3. Extracted text is passed to `exercise_generator.generate_exercises_from_pdf_content()`
4. Text is truncated to 10,000 characters before sending to Gemini
5. Gemini `gemini-2.5-flash` is called with a structured prompt requesting 5–8 exercises
6. Response is parsed as JSON array of `{title, description, difficulty, solution_code}` objects
7. Each exercise is inserted into `class_exercises` with a UUID and auto-incremented `exercise_number`

**Gemini prompt contract:**

```
Generate 5-8 Python data analytics coding exercises based on this content.
Return ONLY a JSON array. Each object must have:
- title (string)
- description (string, the exercise problem statement)
- difficulty (string: "easy", "medium", or "hard")
- solution_code (string, working Python solution)
```

**Gemini API call parameters:**
- Model: `gemini-2.5-flash`
- `temperature`: 0.7
- `maxOutputTokens`: 8192
- Input text: truncated to 10,000 characters

### 9.2 AI Chat Proxy with Circuit Breaker

`POST /api/ai/chat` proxies messages to the Gemini API with several protective layers.

**Rate limiting (per user, not per IP):**
- 20 requests per minute
- 100 requests per hour

**Input validation:**
- Total payload size checked against 50KB limit
- Messages array limited to 100 items

**Model allowlist:**
Requests for disallowed models are rejected with 400 before hitting the Gemini API.

Allowed: `gemini-3-pro-preview`, `gemini-3-flash-preview`, `gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-3-pro-image-preview`

**Circuit breaker:**

```python
_FAILURE_THRESHOLD = 5      # consecutive failures before opening
_RECOVERY_TIMEOUT = 60.0    # seconds to wait before trying again
```

State machine: `closed → open → half-open → closed/open`

When open: Returns 503 immediately without calling Gemini. After `_RECOVERY_TIMEOUT` seconds, transitions to half-open and allows one test request. On success: closes. On failure: opens again.

### 9.3 LTI 1.3 Integration

LTI 1.3 allows LMS platforms (Canvas, Moodle, Blackboard) to embed AnalytIQ content and pass grades back.

**Prerequisites:**
1. Generate RSA key pair: `python3 scripts/generate_lti_keys.py`
2. Set `LTI_PRIVATE_KEY`, `LTI_PUBLIC_KEY`, `LTI_KEY_ID`, `LTI_TOOL_URL` in env
3. Professor registers the LMS in the LTI setup UI (`/lti/setup`)

**JWKS Endpoint:** `GET /lti/jwks`
Returns the tool's RSA public key as a JSON Web Key Set. LMS uses this to verify the tool's JWTs in deep linking.

**Launch Flow:**
1. LMS fetches JWKS from `/lti/jwks`
2. Student clicks assignment in LMS → LMS redirects to `/lti/login`
3. PyLTI1p3 initiates OIDC flow, LMS redirects back
4. LMS POSTs signed JWT to `/lti/launch`
5. PyLTI1p3 validates signature, extracts claims
6. User upsert: match by `(lti_sub, lti_issuer)` → match by email → create new
7. Auto-enroll student in linked class (if class linked via `lti_context_id`)
8. Store LTI session in DB with TTL
9. Render `lti-launch.html` with JWT, which stores token in localStorage and redirects

**Deep Linking:** Allows professors to select specific chapters/exercises to embed in LMS course pages. Flow uses `POST /lti/deep-link/return` to sign the content reference.

**Grade Passback (AGS):**
`POST /api/lti/ags/<class_id>/<ex_id>` submits a student's score back to the LMS gradebook.
- Requires `ags_enabled=true` on the class
- Uses the LTI session's AGS endpoint

**Roster Sync (NRPS):**
`POST /api/lti/sync-roster/<class_id>` fetches enrolled students from the LMS via NRPS and enrolls them in the AnalytIQ class.

### 9.4 SSO (Single Sign-On)

SSO is gated by `FEATURE_SSO=true` environment variable.

**Supported providers:**
- `google`: Google Workspace (discovery URL: `https://accounts.google.com/.well-known/openid-configuration`)
- `microsoft`: Azure AD / Microsoft Entra (discovery URL includes tenant ID)
- `oidc`: Any OpenID Connect-compatible IdP

**Client secret encryption:**
SSO provider `client_secret` is encrypted with `cryptography.fernet.Fernet` before DB storage. The encryption key must be set in the environment. The `sso_repository.py` handles transparent encrypt/decrypt.

**Domain allowlist:**
Each SSO provider can have a list of `allowed_domains`. OIDC users whose email domain is not in the list are rejected with a `PermissionError`.

**Role mapping:**
Providers can specify:
- `role_mapping_attribute`: OIDC claim to check (e.g., `groups`, `department`)
- `role_mapping`: Dict mapping claim values to roles (e.g., `{"Faculty": "professor", "Student": "student"}`)
- `default_role`: Fallback if no mapping matches

**OIDC discovery caching:**
Discovery documents (from `/.well-known/openid-configuration`) are cached in-process to avoid repeated network calls.

**OAuth2 state:**
State tokens are stored in Redis with key `sso_state:{state}` and 600-second TTL (`SSO_STATE_TTL`). Validated in the callback to prevent CSRF.

### 9.5 Tenant System

Tenants represent organizations (universities, departments).

**Data isolation:**
- Users have `tenant_id` set at signup (if SSO-created) or when assigned `tenant_admin` role
- Classes have `tenant_id` inherited from the professor's tenant
- `tenant_admin` users can only manage users and classes within their `tenant_id`
- Superadmins can manage any tenant by passing `?tenant_id=<id>` to tenant-admin endpoints

**Tenant admin capabilities (scoped to their tenant):**
- View users, enable/disable, change roles, force password reset, delete, export
- Manage pending approvals
- View and manage classes
- Configure SSO providers
- View audit log
- Impersonate users within their tenant

**Impersonation:**
Both `superadmin` and `tenant_admin` can impersonate users. The impersonation JWT has:
- `user_id`: target user's ID
- `role`: target user's role
- `impersonator_id`: the admin's ID
- `exp`: 1 hour from now

The frontend can detect impersonation by checking if `impersonator_id` is present in the decoded JWT.

### 9.6 Maintenance Mode and Platform Controls

**Platform Config** (`platform_config` table) is a generic key-value store for runtime platform settings:
- `maintenance_mode`: `"true"` / `"false"`
- `maintenance_message`: Text shown during maintenance

**Middleware check (`middleware.py`):**
`check_maintenance_mode()` runs as a `before_request` hook. It:
1. Reads `platform_config` (cached in-process for 30 seconds)
2. If maintenance_mode is true:
   - Exempt paths: `/api/users/signin`, `/api/users/forgot-password`, `/api/users/reset-password`, `/api/platform/status`, `/api/health`
   - If the request has a valid JWT with `role=superadmin`, the request is allowed through
   - All others get 503

**IP Blocklist:**
`check_ip_blocklist()` runs before maintenance check. Reads `ip_blocklist` table (cached 30s). Blocked IPs get 403.

### 9.7 Audit Logging

`audit.py` provides `audit(conn, action, *, resource_type, resource_id, details)`.

**Design principles:**
- Never raises exceptions (fails silently to avoid breaking the main request)
- Lazy table creation (creates `audit_log` if it doesn't exist)
- Shares the caller's database transaction (no separate connection needed)
- Called before `conn.commit()` so audit entry is part of the same atomic transaction

**Audited actions:**

| Action | Description |
|---|---|
| `CREATE_USER` | New user signup |
| `RESET_PASSWORD` | Password reset |
| `UPDATE_PROFILE` | Profile update |
| `UPDATE_PASSWORD` | Password change |
| `DELETE_USER` | User deletion |
| `CREATE_CLASS` | Class creation |
| `DELETE_CLASS` | Class deletion |
| `ENROLL_CLASS` | Student enrollment |
| `CREATE_CHAPTER` | Chapter upload |
| `DELETE_CHAPTER` | Chapter deletion |
| `CREATE_EXERCISE` | Exercise creation |
| `DELETE_EXERCISE` | Exercise deletion |
| `EXERCISE_SUBMISSION` | Exercise attempt submitted |
| `IMPERSONATE_USER` | Admin impersonation |
| `CREATE_TENANT` | Tenant created |
| `UPDATE_TENANT` | Tenant updated |
| `DELETE_TENANT` | Tenant deleted |
| `DISABLE_USER` | Account disabled |
| `ENABLE_USER` | Account enabled |
| `UPDATE_USER_ROLE` | Role changed |
| `FORCE_PASSWORD_RESET` | Forced reset set |
| `TRANSFER_CLASS` | Class transferred |
| `IMPORT_CHAPTER` | Content imported as chapter |
| `SSO_CREATE_USER` | User created via SSO |

### 9.8 Caching Layer

Redis-backed caching controlled by `FEATURE_CACHING=true`.

**Core functions (`cache.py`):**

```python
get_cached(key)              # Returns None if key missing or cache disabled
set_cached(key, value, ttl)  # No-op if cache disabled
invalidate_cache(pattern)    # Deletes all keys matching Redis glob pattern
```

**`@cache_response(ttl, key_prefix)` decorator:**
- Key format: `{prefix}:{user_id}:{sorted_args_hash}`
- Only caches responses with HTTP 200 status
- Silently skips caching in test mode

**Health check cache:**
`GET /api/health` uses a 30-second in-process cache to avoid overloading downstream services with repeated health checks.

**Maintenance mode / IP blocklist cache:**
Both middleware checks use a 30-second in-process dict cache (not Redis) to avoid per-request DB queries.

### 9.9 Database Connection Management

**Pool configuration:**
```python
ThreadedConnectionPool(
    minconn=DB_POOL_MIN_CONNECTIONS,   # Default: 2
    maxconn=DB_POOL_MAX_CONNECTIONS,   # Default: cpu_count * 2
    dsn=DATABASE_URL,
    connect_timeout=10,                 # seconds
    options="-c statement_timeout=30000"  # 30s statement timeout
)
```

**Per-request lifecycle:**
1. `get_db_connection()`: Retrieves connection from pool, stores in `g.db_conn`. Retries 3x on failure. On penultimate retry, calls `init_db_pool()` to reinitialize the entire pool.
2. Business logic commits/rolls back as needed
3. `close_db_connection()`: Registered as `teardown_appcontext` handler. Returns `g.db_conn` to the pool.

**SSL:** Required in production (`sslmode=require` in connection string).

**Gunicorn `post_fork` hook:** After forking worker processes, `post_fork()` in `gunicorn.conf.py` calls `init_db_pool()` to create per-process pools, preventing connection sharing across processes.

### 9.10 Content Extraction

`python/content_extractor.py` provides `extract_text(file_bytes, filename, max_size_mb)`.

**Supported formats:**

| Extension | Method |
|---|---|
| `.pdf` | PyPDF2 page text concatenation |
| `.txt` | UTF-8 decode |
| `.csv` | Raw text (decoded as UTF-8) |
| `.ipynb` | Concatenate source cells (code + markdown) |
| `.docx` | python-docx paragraph extraction |

**Max size enforcement:** Files exceeding `max_size_mb` raise an error before extraction.

### 9.11 PDF Security Validation

Uploaded PDFs are validated in the chapters blueprint before storage:
1. **Header check:** First 1,024 bytes must contain `%PDF-` signature
2. **Extension check:** Only `ALLOWED_EXTENSIONS` are accepted
3. **Malicious content scan:** First 10,240 bytes scanned for suspicious patterns:
   - `/JavaScript` — embedded scripts
   - `/JS` — JavaScript shorthand
   - `/Launch` — launch external programs
   - `/EmbeddedFile` — embedded executables

### 9.12 Pagination

`utils/__init__.py` provides three functions used throughout the API:

```python
get_pagination_params(request)
# Reads ?limit= and ?offset= from request.args
# Enforces DEFAULT_PAGE_SIZE=20, MAX_PAGE_SIZE=100

build_pagination_metadata(total, limit, offset)
# Returns {total, limit, offset, has_more, current_page, total_pages}

build_paginated_response(items, total, limit, offset, key='items')
# Returns {items: [...], pagination: {...}}
```

### 9.13 Structured Logging

All logging uses `python-json-logger` with `JsonFormatter`. Every log record includes:
- `timestamp`: ISO 8601
- `level`: INFO/WARNING/ERROR
- `service`: `analytiq`
- `request_id`: Per-request UUID (from `g.request_id`)
- `message`: Log message

The `X-Request-ID` header on every response echoes `g.request_id` for client-side correlation.

### 9.14 Email Notifications

**Provider:** Resend API
**From address:** `techsupport@myanalytiq.org`
**Gated by:** `FEATURE_EMAIL_NOTIFICATIONS=true`

**Celery task `send_email_async`:**
```python
send_email_async.delay(
    to_email="user@example.com",
    subject="Password Reset",
    html_content="<h1>Click here to reset...</h1>"
)
```

**Direct call (`utils/email_service.py`):**
```python
send_email(to_email, subject, html_content)
```

Current email triggers:
- Password reset: `POST /api/users/forgot-password`

### 9.15 API Versioning

`register_api_v1_aliases(app)` runs at startup and creates `/api/v1/` mirrors for all `/api/` routes:

```
/api/classes          → /api/v1/classes
/api/users/profile    → /api/v1/users/profile
... (all routes)
```

This is done programmatically by iterating `app.url_map.iter_rules()` and calling `app.add_url_rule()` for each rule that starts with `/api/` but not `/api/v1/`. Errors during registration are silently swallowed.

---

## 10. Security

### CORS

Controlled by `CORS_ORIGINS` environment variable (comma-separated list of allowed origins).

**Behavior:**
- `*` in origins: allow everything (development mode)
- Specific origins: reflect the requesting origin if it matches
- `file://` or null origin: allowed only in debug mode
- All other origins: CORS headers omitted (browser blocks the request)

`OPTIONS` requests are handled by a `before_request` hook, returning 200 with CORS headers. This replaces per-route OPTIONS handling.

### Security Headers (applied to all API responses)

| Header | Value |
|---|---|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` (production only) |
| `Cache-Control` | `no-store, no-cache, must-revalidate, max-age=0` |
| `Content-Security-Policy-Report-Only` | `default-src 'self'; script-src 'self' 'unsafe-inline' CDNs; ...` |

### CSRF Protection

`Flask-WTF CSRFProtect` — **disabled by default** (`FEATURE_CSRF=false`).

`extensions.csrf_exempt(f)` is a decorator that degrades gracefully: if CSRF is disabled, it's a no-op; if enabled, it marks the function with `@csrf.exempt`.

All API routes currently use `@csrf_exempt` (or the equivalent) to support stateless JWT API clients.

### Rate Limiting

`Flask-Limiter` backed by Redis in production, memory in development.

| Scope | Default Limit |
|---|---|
| Global (production) | 200/day, 50/hour |
| Global (development) | 50,000/day, 2,000/hour |
| POST /api/users/signup | 5/hour |
| POST /api/users/signin | 10/minute |
| POST /api/users/forgot-password | 3/hour |
| POST /api/users/reset-password | 5/hour |
| GET /api/sso/init/* | 30/minute |
| POST /api/superadmin/*/impersonate | 10/minute |
| POST /api/ai/chat | 20/minute, 100/hour (per user) |

### Sentry Error Monitoring

Configured in `sentry_config.py` with `init_sentry(app)`:
- Flask, Redis, and Celery integrations enabled
- **Error sample rate:** 100% (all errors)
- **Traces sample rate:** 10%
- **PII:** `send_default_pii=False`
- **Filtered request headers:** `Authorization`, `Cookie`
- **Filtered event data:** fields matching `password`, `api_key`, `secret`, `token`

### ProxyFix Middleware

```python
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
```

Trusts exactly one proxy hop (Cloudflare) for `X-Forwarded-For`, `X-Forwarded-Proto`, `X-Forwarded-Host`, `X-Forwarded-Prefix`.

### PDF Security

See Section 9.11. Suspicious PDFs are rejected before storage.

### Account Status Checks

Every authenticated request (via `@require_auth`) queries the database to confirm `account_status != 'disabled'` and `!= 'pending_approval'`. This ensures disabled accounts are blocked even if they hold a valid unexpired JWT.

### Password Security

- Minimum 8 characters, maximum 72 characters (bcrypt limit)
- bcrypt with 12 work factor
- Legacy passwords (pre-bcrypt, simple integer hash) automatically upgraded to bcrypt on successful verification
- Password reset tokens: `secrets.token_urlsafe(32)`, 1-hour TTL, deleted after use

---

## 11. Configuration and Environment Variables

All variables are read in `config.py`. Defaults listed are used if the variable is not set.

### Required Variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string. Must include SSL parameters for production. |
| `SECRET_KEY` | Flask session secret. Must be changed from default in production. |
| `JWT_SECRET_KEY` | JWT signing secret. Defaults to `SECRET_KEY` if not set. |
| `GEMINI_API_KEY` | Google Gemini API key. Required when `FEATURE_AI_EXERCISES=true`. |

### Database Configuration

| Variable | Default | Description |
|---|---|---|
| `DB_POOL_MIN` | `2` | Minimum connections in pool |
| `DB_POOL_MAX` | `cpu_count * 2` | Maximum connections in pool |
| `DB_CONNECTION_TIMEOUT` | `10` | Seconds to wait for a connection |
| `DB_STATEMENT_TIMEOUT` | `30` | PostgreSQL statement timeout in seconds |

### Rate Limiting

| Variable | Default | Description |
|---|---|---|
| `RATE_LIMIT_DAY` | `200` (prod) | Default requests per day |
| `RATE_LIMIT_HOUR` | `50` (prod) | Default requests per hour |
| `RATE_LIMIT_SIGNUP` | `5` | Signups per hour |
| `RATE_LIMIT_SIGNIN` | `10` | Signins per minute |
| `RATE_LIMIT_FORGOT_PW` | `3` | Forgot password per hour |
| `RATE_LIMIT_RESET_PW` | `5` | Password resets per hour |

### Security

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `dev-secret-key-change-in-production` | Flask secret |
| `JWT_SECRET_KEY` | Inherits `SECRET_KEY` | JWT signing key |
| `JWT_EXPIRY_HOURS` | `168` | 7 days |
| `BCRYPT_ROUNDS` | `12` | bcrypt work factor |
| `PLATFORM_OWNER_EMAIL` | `aelharouchi@myanalytiq.org` | Platform owner email (unrestricted superadmin) |

### Feature Flags

| Variable | Default | Description |
|---|---|---|
| `FEATURE_AI_EXERCISES` | `true` | Enable Gemini AI exercise generation |
| `FEATURE_EMAIL` | `false` | Enable email notifications via Resend |
| `FEATURE_ANALYTICS` | `true` | Enable analytics features |
| `FEATURE_CSRF` | `false` | Enable CSRF protection |
| `FEATURE_ASYNC_TASKS` | `false` | Enable Celery async processing |
| `FEATURE_CACHING` | `false` | Enable Redis caching |
| `FEATURE_SSO` | `false` | Enable SSO providers |

### File Upload

| Variable | Default | Description |
|---|---|---|
| `MAX_PDF_SIZE_MB` | `50` | Maximum PDF upload size |

### AI / Gemini

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | — | Google Gemini API key |
| `GEMINI_MODEL` | `gemini-1.5-flash` | Default model for exercise generation |
| `GEMINI_TIMEOUT` | `60` | Gemini API call timeout in seconds |

### Redis / Celery

| Variable | Default | Description |
|---|---|---|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `CACHE_TTL` | `300` | Default cache TTL in seconds |

### Storage (Supabase)

| Variable | Default | Description |
|---|---|---|
| `SUPABASE_URL` | — | Supabase project URL |
| `SUPABASE_KEY` | — | Supabase service role key |
| `SUPABASE_BUCKET` | `pdfs` | Storage bucket name |

### LTI 1.3

| Variable | Default | Description |
|---|---|---|
| `LTI_PRIVATE_KEY` | — | RSA private key in PEM format |
| `LTI_PUBLIC_KEY` | — | RSA public key in PEM format |
| `LTI_KEY_ID` | `analytiq-lti-key-1` | Key ID for JWKS |
| `LTI_TOOL_URL` | `https://myanalytiq.org` | Canonical tool URL for deep linking |
| `LTI_SESSION_TTL` | `3600` | LTI session lifetime in seconds |

### SSO

| Variable | Default | Description |
|---|---|---|
| `SSO_STATE_TTL` | `600` | OAuth2 state token TTL in Redis (seconds) |
| `FRONTEND_URL` | `https://myanalytiq.org` | Used as `SSO_REDIRECT_BASE_URL` for callbacks |

### CORS

| Variable | Default | Description |
|---|---|---|
| `CORS_ORIGINS` | `*` | Comma-separated list of allowed origins |
| `CORS_MAX_AGE` | `3600` | Preflight cache duration in seconds |

### Email (Legacy SMTP — not actively used, Resend is primary)

| Variable | Default | Description |
|---|---|---|
| `MAIL_SERVER` | `smtp.gmail.com` | SMTP server |
| `MAIL_PORT` | `587` | SMTP port |
| `MAIL_USE_TLS` | `true` | Use TLS |
| `MAIL_USERNAME` | — | SMTP username |
| `MAIL_PASSWORD` | — | SMTP password |
| `MAIL_DEFAULT_SENDER` | `noreply@analytiq.com` | Default from address |

### Logging

| Variable | Default | Description |
|---|---|---|
| `LOG_LEVEL` | `INFO` (prod), `DEBUG` (dev) | Log level |
| `LOG_FORMAT` | `json` | `json` or `text` |

### Pagination

| Variable | Default | Description |
|---|---|---|
| `DEFAULT_PAGE_SIZE` | `20` | Default items per page |
| `MAX_PAGE_SIZE` | `100` | Maximum items per page |

### Input Limits

| Variable | Value | Description |
|---|---|---|
| `MAX_EMAIL_LENGTH` | `254` | RFC 5321 |
| `MAX_NAME_LENGTH` | `100` | User name |
| `MIN_PASSWORD_LENGTH` | `8` | Password minimum |
| `MAX_PASSWORD_LENGTH` | `72` | bcrypt hard limit |
| `MAX_CLASS_NAME_LENGTH` | `200` | Class name |
| `MAX_CLASS_DESCRIPTION_LENGTH` | `2000` | Class description |
| `MAX_CHAPTER_TITLE_LENGTH` | `300` | Chapter title |
| `MAX_EXERCISE_TITLE_LENGTH` | `300` | Exercise title |
| `MAX_EXERCISE_DESCRIPTION_LENGTH` | `5000` | Exercise description |
| `MAX_SOLUTION_CODE_LENGTH` | `20000` | Solution code |
| `MAX_AI_MESSAGE_LENGTH` | `50,000` | AI chat single message (50KB) |
| `MAX_AI_CONVERSATION_MESSAGES` | `100` | Max messages in AI chat payload |

### Other

| Variable | Default | Description |
|---|---|---|
| `FLASK_ENV` | `development` | `development`, `testing`, or `production` |
| `PORT` | `5001` | Port for local development |
| `PW_RESET_EXPIRY_HOURS` | `24` | Password reset token TTL |
| `CSRF_TIME_LIMIT` | `3600` | CSRF token lifetime |
| `HEALTH_CHECK_TIMEOUT` | `5` | Health check service probe timeout |

---

## 12. Background Tasks

### Celery Configuration (`celery_app.py`)

```python
broker_url = REDIS_URL
result_backend = REDIS_URL
task_queues = ['pdf_processing', 'ai_tasks', 'emails']
task_time_limit = 300          # 5 minutes hard limit
task_soft_time_limit = 270     # 4.5 minutes soft limit
result_expires = 3600          # Results kept for 1 hour
```

Celery workers are started with:
```
celery -A celery_app.celery_app worker --loglevel=info --concurrency=2
```

### Task: `process_pdf_and_extract_text`

Queue: `pdf_processing`

Extracts text from a PDF stored in the database. Used as a sub-step in the chapter upload pipeline when async tasks are enabled.

**Parameters:** `chapter_id`, `pdf_data` (bytes)
**Returns:** Extracted text string

### Task: `generate_exercises_async`

Queue: `ai_tasks`

Calls `exercise_generator.generate_exercises_from_pdf_content()` and inserts exercises into `class_exercises`.

**Parameters:** `chapter_id`, `class_id`, `pdf_text`, `chapter_title`, `api_key`
**Returns:** Count of exercises generated

### Task: `send_email_async`

Queue: `emails`

Sends a transactional email via the Resend API.

**Parameters:** `to_email`, `subject`, `html_content`
**Returns:** Resend API response dict

### Task: `process_chapter_upload`

Queue: `pdf_processing`

Combined workflow task: extract text then generate exercises. Calls `process_pdf_and_extract_text` and `generate_exercises_async` in sequence.

**Parameters:** `chapter_id`, `class_id`, `pdf_data`, `chapter_title`, `api_key`

### `DatabaseTask` Base Class

All tasks that need database access inherit from `DatabaseTask`, which:
- Creates its own `ThreadedConnectionPool` (not shared with the web process)
- Provides `get_connection()` and `return_connection()` helpers
- Handles connection lifecycle within the task

### Feature Flag

Tasks are only triggered when `FEATURE_ASYNC_TASKS=true`. When disabled (default), the web process handles PDF extraction and exercise generation synchronously within the HTTP request.

---

## 13. Testing

### Test Infrastructure

**Framework:** pytest
**Config:** `pytest.ini`
**Fixtures:** `tests/conftest.py`

### Key Fixtures

#### `app` fixture
Creates a Flask test app with:
- `TESTING=True`
- `WTF_CSRF_ENABLED=False`
- Rate limiter disabled

#### `client` fixture
Returns `app.test_client()`.

#### `mock_db` fixture
Patches `get_db_connection` in the `db` module and in all blueprint modules that import it:
```python
monkeypatch.setattr('db.get_db_connection', mock_get_db)
monkeypatch.setattr('blueprints.auth.get_db_connection', mock_get_db)
# ... all 11 blueprint modules
```

Returns a `MagicMock` connection with `MagicMock` cursor (all `fetchone`, `fetchall`, `execute` pre-configured as Mocks).

#### `mock_redis_client` fixture
`MagicMock` Redis client with `get`, `set`, `setex`, `delete`, `keys`, `ping`, `info` methods.

#### `mock_supabase_client` fixture
`MagicMock` Supabase client with `storage.from_().upload`, `get_public_url`, `create_signed_url`, `remove`, `list`.

#### `mock_celery_app` / `mock_celery_task` fixtures
`MagicMock` Celery app and task objects.

#### Data fixtures
- `sample_user`: `{user_id, email, name, role, created_at}`
- `sample_class`: `{class_id, class_name, class_code, professor_id, created_at}`
- `sample_chapter`: `{chapter_id, class_id, title, pdf_filename, pdf_url, created_at}`
- `sample_pdf_bytes`: Minimal valid PDF header
- `pagination_params`: `{limit: 10, offset: 0}`
- `pagination_metadata`: `{total: 100, limit: 10, offset: 0, has_more: True, ...}`

### Auth Bypass in Tests

When `TESTING=True` and `FLASK_ENV != 'production'`, `@require_auth` checks for test identity in this order:

1. `X-Test-User-ID` request header
2. `user_id` in query params
3. `user_id` in JSON body
4. `user_id` in form data

Role is read from `X-Test-User-Role` header (defaults to `student`).

**Example test request:**
```python
response = client.get(
    '/api/users/profile',
    headers={
        'X-Test-User-ID': 'test-user-123',
        'X-Test-User-Role': 'professor'
    }
)
```

### Test Files Overview

| File | Coverage Area |
|---|---|
| `test_auth.py` | Signup, signin, forgot/reset password flows |
| `test_api.py` | General API endpoint tests |
| `test_ai_routes.py` | AI chat endpoint, circuit breaker, rate limiting |
| `test_chapters_routes.py` | Chapter upload, PDF serving, exercise generation trigger |
| `test_classes_routes.py` | Class CRUD, enrollment, progress, leaderboards, resources |
| `test_exercises_routes.py` | Exercise CRUD, submission, leaderboards |
| `test_users_routes.py` | Profile, settings, conversations, digest, memory, preferences |
| `test_security.py` | Auth bypass, role enforcement, header injection |
| `test_tasks.py` | Celery task execution |
| `test_cache.py` | Cache get/set/invalidate |
| `test_sso_routes.py` | SSO provider listing, init, callback flows |
| `test_tenant_admin.py` | Tenant admin CRUD, scope enforcement |
| `test_superadmin_extended.py` | Superadmin user management, tenant management |
| `test_utils.py` | Pagination helpers |
| `test_config_deep.py` | Config validation, environment variable parsing |
| `test_exercise_generator.py` | Gemini API call mocking, exercise parsing |
| `test_pdf_processor.py` | PDF text extraction |
| `test_content_extractor.py` | Multi-format extraction |
| `test_sentry_config.py` | Sentry initialization |
| `test_sso_repository.py` | SSO repository SQL functions |
| `test_supabase_storage.py` | Supabase storage wrapper |
| `test_tasks_comprehensive.py` | Full task pipeline tests |
| `test_cache_comprehensive.py` | Cache decorator, TTL, invalidation |
| `test_integration_stress.py` | Load and stress testing scenarios |
| `test_api_docs_coverage.py` | API documentation coverage checks |
| `tests/integration/` | Integration tests using real CI postgres (mostly empty) |
| `tests/e2e/` | End-to-end tests |

### Running Tests

```bash
pytest                              # Run all tests
pytest tests/test_auth.py           # Run specific file
pytest -k "test_signin"             # Run matching tests
pytest --cov=. --cov-report=html   # With coverage report
```

### CI Environment Variables for Tests

```
FLASK_ENV=testing
DATABASE_URL=postgresql://test:test@localhost:5432/test_db
REDIS_URL=redis://localhost:6379/1
FEATURE_ASYNC_TASKS=False
FEATURE_CACHING=False
FEATURE_CSRF_PROTECTION=False
```

---

## 14. CI/CD Pipeline

**File:** `.github/workflows/ci.yml`
**Triggers:** Push or PR to `main`, push to `develop`

### Jobs

#### `test` job

**Services:**
- PostgreSQL 14 (`postgres:test@localhost:5432/test_db`)
- Redis 7 (`redis://localhost:6379`)

**Steps:**
1. Checkout code
2. Set up Python 3.9
3. Install dependencies: `pip install -r requirements.txt`
4. Run flake8 (style check — currently `continue-on-error: true`)
5. Run black (format check — currently `continue-on-error: true`)
6. Run mypy (type check — `continue-on-error: true`)
7. Run pytest with coverage:
   ```
   pytest --cov=. --cov-report=xml --cov-report=html -v
   ```
8. Upload coverage to Codecov

#### `security-scan` job

1. Checkout code
2. Install bandit
3. Run bandit security scanner (`continue-on-error: true`)

#### `deploy-notification` job

Runs after test passes on `main` branch. Currently only echoes a deployment notification (no actual deployment — Render handles that via its own GitHub integration).

### Render.com Deployment

Render monitors the `main` branch and auto-deploys on push. The `render.yaml` defines:

```yaml
services:
  - type: web
    name: analytiq-web
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn -c gunicorn.conf.py app:app
    healthCheckPath: /api/health

  - type: worker
    name: analytiq-worker
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: celery -A celery_app.celery_app worker --loglevel=info --concurrency=2
```

---

## 15. Deployment

### Render.com Configuration

**Web service:** Flask app served by Gunicorn
**Worker service:** Celery worker
**Health check endpoint:** `GET /api/health`

### Gunicorn Configuration (`gunicorn.conf.py`)

```python
workers = 4
worker_class = 'sync'
timeout = 300           # 5 minutes (for long AI calls and PDF processing)
max_requests = 1000     # Restart worker after 1000 requests (memory leak prevention)
max_requests_jitter = 100
bind = f'0.0.0.0:10000'

def post_fork(server, worker):
    """Reset DB connection pool in each worker after fork."""
    from db import init_db_pool
    init_db_pool()
```

### Startup Sequence

1. Gunicorn forks 4 worker processes
2. Each worker's `post_fork` hook calls `init_db_pool()` to create per-process connection pools
3. On first request context: `db_migrate.run_migrations()` applies any pending SQL migrations
4. Blueprints are registered, v1 aliases created
5. Application ready to serve traffic

### Database Migrations at Startup

`db_migrate.py` is called within `app.app_context()` at startup:

1. Creates `schema_migrations` table if it doesn't exist
2. Reads all `*.sql` files from `migrations/` directory, sorted by filename
3. Skips any migration already recorded in `schema_migrations`
4. Executes pending migrations in order
5. Records each migration's filename in `schema_migrations` after success
6. Idempotent — safe to run on every startup

### Environment Variables

Set in Render.com dashboard under "Environment". See Section 11 for complete list.

### Procfile

```
web: gunicorn -c gunicorn.conf.py app:app
worker: celery -A celery_app.celery_app worker --loglevel=info --concurrency=2
```

### Local Development

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with local values
python app.py
```

Local dev server runs on `http://127.0.0.1:5001`.

---

## 16. Key Architectural Decisions

### 16.1 Blueprint Extraction from Monolith

The app started as a 5,391-line monolithic `app.py`. The primary architectural goal (ongoing as of March 2026) is extracting all business logic into Flask Blueprints by domain:

| Blueprint | Domain |
|---|---|
| `auth` | Registration, authentication, password management |
| `users` | Profiles, settings, conversations, AI memory |
| `classes` | Classes, enrollment, progress, leaderboards |
| `chapters` | Chapter/PDF management, exercise generation trigger |
| `exercises` | Exercise CRUD and progress submission |
| `ai` | Gemini chat proxy |
| `health` | Health checks, utility endpoints |
| `platform` | Maintenance mode, announcements |
| `superadmin` | Platform administration |
| `tenant_admin` | Tenant-scoped administration |
| `lti` | LTI 1.3 protocol |
| `sso` | OAuth2/OIDC SSO |
| `content_import` | External content ingestion |

**Repository pattern:** SQL queries are extracted into `repositories/` modules that receive a DB connection and return plain Python data. Blueprints are responsible for connection lifecycle (commit/rollback), not repositories.

### 16.2 JWT-based Stateless Auth

No server-side sessions. Every request must include a `Bearer <token>` JWT. The token encodes `user_id`, `role`, `tenant_id`, and optional `impersonator_id`. This enables:
- Horizontal scaling (no session affinity needed)
- Impersonation without separate session storage
- Tenant scoping in the token itself

**Trade-off:** Tokens cannot be revoked before expiry. A disabled user can still use their token until expiry (mitigated by per-request `account_status` DB check in `@require_auth`).

### 16.3 Connection Pool with Per-Worker Initialization

`psycopg2.ThreadedConnectionPool` is created once per Gunicorn worker process (not shared across processes, not shared across threads). The `post_fork` hook ensures each worker gets its own pool. Each request gets a connection from the pool, stored in Flask's `g` object, and returned on `teardown_appcontext`.

**Why not SQLAlchemy?** The project uses raw psycopg2 for simplicity and full SQL control. Repository functions write explicit SQL rather than using an ORM.

### 16.4 Feature Flags for Gradual Rollout

All risky or expensive features are behind environment variable feature flags:
- `FEATURE_ASYNC_TASKS`: Celery (default off — sync processing is simpler for small scale)
- `FEATURE_CACHING`: Redis cache (default off)
- `FEATURE_CSRF`: CSRF protection (default off — currently under review to flip on)
- `FEATURE_SSO`: SSO providers (default off)
- `FEATURE_AI_EXERCISES`: AI exercise generation (default on)
- `FEATURE_EMAIL_NOTIFICATIONS`: Email sending (default off)

### 16.5 Binary PDF Storage in PostgreSQL

PDFs are stored as `BYTEA` in `class_chapters.pdf_data` and optionally also in Supabase Storage. The dual storage approach:
- DB storage: simple, no external dependency, but increases DB size
- Supabase Storage: better for large PDFs, CDN-served, presigned URLs

The health check marks Supabase Storage as non-critical (DB is critical). PDF serving in `GET /api/chapters/<id>/pdf` checks: if `pdf_url` is set, redirect to Supabase; otherwise serve from `pdf_data`.

### 16.6 Audit Logging as Same-Transaction Write

`audit()` shares the caller's DB connection and transaction. This means the audit entry is committed atomically with the business operation — there is no separate audit connection that could lag or fail independently. The design trades off the ability to audit failed operations for atomicity.

### 16.7 Circuit Breaker on Gemini API

The AI chat endpoint uses a simple in-process circuit breaker to prevent cascading failures when Gemini is down. This is a per-process state (not distributed via Redis), so circuit state is not shared across Gunicorn workers. Each worker independently tracks failures and opens/closes its own circuit.

### 16.8 Vanilla JS Frontend

The frontend uses no framework and no build step. Benefits:
- No Node.js dependency
- No build pipeline failures
- Fast iteration
- Easy to understand for new contributors

Trade-offs:
- No component reuse framework
- Manual DOM manipulation
- No TypeScript types

Each HTML page loads the modules it needs via `<script>` tags. Load order is documented (backlog item 28C).

### 16.9 ProxyFix for Cloudflare

```python
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
```

Trusts exactly one proxy hop. This ensures `request.remote_addr` reflects the real client IP (extracted from `X-Forwarded-For` with the outermost header stripped off), which is essential for rate limiting to work correctly.

### 16.10 Auto-Migration at Startup

Rather than a separate migration step in the deploy pipeline, migrations run automatically on startup via `db_migrate.run_migrations()`. The `schema_migrations` table tracks what has been applied. This keeps deployments simple (just push code) at the cost of startup latency for large migrations. The migration runner is idempotent and fails open (logs warning, continues).

---

## 17. Known Limitations and Future Work

### Active Backlog Items (from Feb 2026 Code Review)

**Priority 1 — Urgent:**

- **14A: Leaderboard endpoint exposes emails without auth.** The leaderboard endpoints (`GET /api/classes/<id>/leaderboard/*`, `GET /api/leaderboard/grand`) should require `@require_auth` and remove the `email` field from responses.

- **5A+B: `str(e)` in 500 responses exposes internal errors.** Approximately 80 instances of `return jsonify({"error": str(e)}), 500` throughout the codebase leak stack trace fragments to clients. These should use `logger.error(..., exc_info=True)` + generic client message. A global `@app.errorhandler(500)` is in place but individual route handlers still leak.

- **18B: Test auth bypass is not guarded by `FLASK_ENV`.** The bypass condition should be `TESTING=True AND ENV == 'testing'` (not `ENV != 'production'`). The current code allows bypass in `staging` or any other non-production environment.

**Priority 2 — Next Sprint:**

- **6A: User IDs use `uuid.uuid4()` (good) but some older code paths use timestamps.** Verify all user_id creation paths use UUID.

- **11A: Password reset endpoint has a 6-character minimum but signup has 8.** Inconsistent constraint — align both to 8.

- **16A: Per-user rate limit on `/api/ai/chat` is implemented** (20/min, 100/hr) but the rate key is per IP by default in Flask-Limiter. Verify it correctly identifies by `g.user_id`.

- **19A: Enable CSRF by default + audit all `@csrf_exempt` coverage.** Review agreed to flip `FEATURE_CSRF` to `True` in production.

- **12A: `.gitignore` does not cover `coverage.xml`, `.coverage`, `htmlcov/`.** These test artifacts are committed to the repo.

- **25A: flake8 and black steps in CI have `continue-on-error: true`.** This means linting failures do not block merges.

- **2A: `cache.py`, `celery_app.py`, `supabase_storage.py` re-read environment variables directly** instead of importing from `config.py`. They should import `config.REDIS_URL` etc.

**Priority 3 — With Blueprint Work:**

- **4A: ~15 per-endpoint OPTIONS handling blocks exist** in addition to the global `before_request` handler. The per-endpoint ones are redundant.

- **8A: ~45 `print()` calls** scattered in blueprint files. Should be replaced with `logger.*`.

- **15A: Supabase Storage health check is marked critical.** It should be non-critical (storage unavailable should not mark the whole app unhealthy).

- **20A: Legacy password hash function `hash_password_legacy()`** should be removed once all users have been migrated to bcrypt. A DB query to find remaining legacy-hash users should be run first.

- **23A: `exercises-database.js`** (if it still exists) appears unused.

- **3A: `@require_role` decorator is defined but not consistently used.** Some routes still do redundant DB role re-queries instead of reading `g.user_role`.

**Priority 4 — Structural:**

- **9A + 10A: Test suite has 30+ test files** but many are coverage-farming (testing mock behavior, not real logic). The agreed direction is to replace with behavioral tests per domain, plus real integration tests in `tests/integration/` using the CI postgres instance.

- **21A, 22A, 24A: Docs need cleanup.** `docs/ARCHITECTURE.md`, `docs/PROJECT_OVERVIEW.md`, `docs/SECURITY.md` may have stale information.

- **28C: JS load order comments** should be added to HTML templates to document module dependencies.

- **27A: `.env.example`** should be kept up to date with all required variables.

### Technical Debt

- The `class_resources` table uses lazy schema migration (adding columns via `ensure_resources_table()` on first access) rather than proper SQL migrations. This pattern is fragile and should be converted to a numbered migration file.

- The `exercise_repository.py` `ensure_exercises_table()` function uses the same lazy migration anti-pattern for `solution_code`, `exercise_number`, and `created_by` columns.

- OIDC discovery documents are cached in-process with no TTL or invalidation. If a provider rotates its keys, the cache must be flushed by restarting the process.

- LTI session storage uses a TTL column (`expires_at`) but there is no background job to clean up expired sessions. The `lti_sessions` table grows indefinitely.

- The circuit breaker in `blueprints/ai.py` is per-process state. With 4 Gunicorn workers, one worker's circuit may open while others are still calling Gemini. A Redis-backed circuit breaker would provide consistent behavior across all workers.

- `class_id` is user-supplied (the class code, e.g., `DATA101`) rather than a system-generated UUID. This creates a predictability/enumeration concern and makes class_id a mutable primary key if class codes need to change.

- The `practice_progress` table has a composite primary key on `(user_id, exercise_id)` but exercise_id appears to be the same field used in both standalone exercises and class exercises. The `class_exercise_id` column is a secondary reference. This dual-track tracking makes progress queries complex.

---

*End of FULL_APP_REFERENCE.md*
