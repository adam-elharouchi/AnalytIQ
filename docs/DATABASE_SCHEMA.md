# AnalytIQ Database Schema Reference

Last updated: 2026-03-22

All tables are PostgreSQL. Migrations live in `migrations/` and are applied
automatically at startup via `db_migrate.py`. Every migration file is
idempotent (`IF NOT EXISTS`, `ON CONFLICT DO NOTHING`, `DO $$ ... $$` guards).

---

## Table Index

| Table | Purpose |
|---|---|
| [`users`](#users) | Accounts — email/password, LTI identity, SSO identity |
| [`user_profiles`](#user_profiles) | Display name, bio, avatar |
| [`user_settings`](#user_settings) | Notification preferences |
| [`user_preferences`](#user_preferences) | UI preferences (theme, language) |
| [`tenants`](#tenants) | Multi-tenant organizations |
| [`classes`](#classes) | Professor-created classes |
| [`class_enrollments`](#class_enrollments) | Student ↔ class membership |
| [`class_chapters`](#class_chapters) | PDF chapters within a class |
| [`class_exercises`](#class_exercises) | Coding exercises within a chapter |
| [`class_resources`](#class_resources) | Supplementary files attached to a class |
| [`exercise_progress`](#exercise_progress) | Per-student submission scores |
| [`conversations`](#conversations) | AI chat history |
| [`ai_agent_digest`](#ai_agent_digest) | Per-user AI context summary |
| [`password_resets`](#password_resets) | Short-lived email reset tokens |
| [`audit_log`](#audit_log) | FERPA-compliant mutation log |
| [`lti_configurations`](#lti_configurations) | LMS platform registrations (LTI 1.3) |
| [`lti_sessions`](#lti_sessions) | Active LTI launch sessions |
| [`tenant_sso_providers`](#tenant_sso_providers) | Per-tenant OIDC/SSO provider config |
| [`platform_config`](#platform_config) | Key-value platform settings |
| [`announcements`](#announcements) | Platform-wide banners |
| [`ip_blocklist`](#ip_blocklist) | Blocked IP addresses |
| [`exercise_generation_events`](#exercise_generation_events) | AI flywheel — generation metadata |
| [`exercise_outcome_events`](#exercise_outcome_events) | AI flywheel — student attempt outcomes |
| [`schema_migrations`](#schema_migrations) | Applied migration tracking |

---

## Core User Tables

### `users`

Central identity table. A user may authenticate via password, LTI SSO, or
OIDC SSO — the columns reflect all three methods.

| Column | Type | Notes |
|---|---|---|
| `user_id` | `VARCHAR(255) PK` | UUID string |
| `email` | `VARCHAR(255) UNIQUE NOT NULL` | |
| `password_hash` | `VARCHAR(255)` | NULL for SSO-only accounts |
| `role` | `VARCHAR(50)` | `student`, `professor`, `tenant_admin`, `superadmin` |
| `tenant_id` | `VARCHAR(255) FK→tenants` | NULL = platform user |
| `is_super_admin` | `BOOLEAN` | Redundant with `role='superadmin'`; legacy column |
| `account_status` | `VARCHAR(50)` | `active`, `suspended` |
| `requires_password_reset` | `BOOLEAN` | Forces reset on next signin |
| `last_login` | `TIMESTAMP` | Updated on each successful signin |
| `lti_sub` | `VARCHAR(255)` | LTI 1.3 subject claim |
| `lti_issuer` | `VARCHAR(500)` | LTI platform issuer URL |
| `sso_provider_id` | `VARCHAR(255) FK→tenant_sso_providers` | OIDC provider |
| `sso_subject` | `TEXT` | OIDC `sub` claim |
| `created_at` | `TIMESTAMP` | |

**Indexes:** `(lti_sub, lti_issuer)` UNIQUE; `(sso_provider_id, sso_subject)`
UNIQUE partial (WHERE `sso_provider_id IS NOT NULL`).

---

### `user_profiles`

| Column | Type | Notes |
|---|---|---|
| `user_id` | `VARCHAR(255) PK FK→users` | |
| `display_name` | `VARCHAR(255)` | |
| `bio` | `TEXT` | |
| `avatar_url` | `TEXT` | |
| `updated_at` | `TIMESTAMP` | |

---

### `user_settings`

| Column | Type | Notes |
|---|---|---|
| `user_id` | `VARCHAR(255) PK FK→users` | |
| `email_notifications` | `BOOLEAN` | |
| `exercise_reminders` | `BOOLEAN` | |
| `weekly_digest` | `BOOLEAN` | |
| `updated_at` | `TIMESTAMP` | |

---

### `user_preferences`

| Column | Type | Notes |
|---|---|---|
| `user_id` | `VARCHAR(255) PK FK→users` | |
| `theme` | `VARCHAR(50)` | `light`, `dark` |
| `language` | `VARCHAR(10)` | `en`, etc. |
| `updated_at` | `TIMESTAMP` | |

---

## Multi-Tenancy

### `tenants`

| Column | Type | Notes |
|---|---|---|
| `tenant_id` | `VARCHAR(255) PK` | UUID string |
| `name` | `VARCHAR(255) NOT NULL` | |
| `lti_issuer` | `VARCHAR(500) UNIQUE` | Maps 1:1 with `lti_configurations.issuer` |
| `is_active` | `BOOLEAN` | |
| `created_at` | `TIMESTAMP` | |
| `updated_at` | `TIMESTAMP` | |

---

## Course Content

### `classes`

| Column | Type | Notes |
|---|---|---|
| `class_id` | `VARCHAR(255) PK` | Also serves as the student join code |
| `class_name` | `VARCHAR(255) NOT NULL` | |
| `professor_id` | `VARCHAR(255) FK→users` | |
| `tenant_id` | `VARCHAR(255) FK→tenants` | |
| `lti_context_id` | `VARCHAR(500)` | LTI context identifier |
| `lti_issuer` | `VARCHAR(500)` | LTI platform URL |
| `nrps_context_url` | `TEXT` | Names and Roles Provisioning URL |
| `ags_enabled` | `BOOLEAN` | Assignment and Grade Services enabled |
| `ags_lineitems_url` | `TEXT` | AGS lineitems endpoint |
| `created_at` | `TIMESTAMP` | |

---

### `class_enrollments`

| Column | Type | Notes |
|---|---|---|
| `enrollment_id` | `VARCHAR(255) PK` | |
| `class_id` | `VARCHAR(255) FK→classes` | |
| `student_id` | `VARCHAR(255) FK→users` | |
| `enrolled_at` | `TIMESTAMP` | |

---

### `class_chapters`

| Column | Type | Notes |
|---|---|---|
| `chapter_id` | `VARCHAR(255) PK` | |
| `class_id` | `VARCHAR(255) FK→classes` | |
| `title` | `VARCHAR(255) NOT NULL` | |
| `pdf_filename` | `VARCHAR(255)` | Original upload filename |
| `pdf_url` | `TEXT` | Supabase Storage URL |
| `pdf_data` | `BYTEA` | Raw PDF bytes (for Supabase-less fallback) |
| `pdf_text` | `TEXT` | Extracted plain text (written by Celery task) |
| `chapter_order` | `INTEGER` | Display ordering within class |
| `created_at` | `TIMESTAMP` | |

---

### `class_exercises`

Full schema after all migrations (001, 005, 007):

| Column | Type | Notes |
|---|---|---|
| `exercise_id` | `VARCHAR(255) PK` | UUID string (generated by `uuid.uuid4()`) |
| `chapter_id` | `VARCHAR(255) FK→class_chapters` | |
| `class_id` | `VARCHAR(255) FK→classes` | |
| `title` | `VARCHAR(255) NOT NULL` | |
| `description` | `TEXT` | Problem statement shown to students |
| `difficulty` | `VARCHAR(50)` | `easy`, `medium`, `hard` |
| `solution_code` | `TEXT` | Reference solution (professor-visible only) |
| `exercise_number` | `INTEGER` | Ordering within chapter (default 1) |
| `function_name` | `VARCHAR(255)` | Name of function students must define (default `solution`) |
| `test_cases` | `JSONB` | Array of `{description, input, expected_output, weight}` |
| `language` | `VARCHAR(50)` | `Python`, `R`, `JavaScript`, `SQL` (default `Python`) |
| `created_by` | `VARCHAR(255)` | `user_id` of creator |
| `created_at` | `TIMESTAMP` | |

**Index:** Partial index on `(test_cases IS NOT NULL)` for grading dispatch.

---

### `class_resources`

| Column | Type | Notes |
|---|---|---|
| `resource_id` | `VARCHAR(255) PK` | |
| `class_id` | `VARCHAR(255)` | |
| `user_id` | `VARCHAR(255)` | Uploader |
| `title` | `VARCHAR(255) NOT NULL` | |
| `description` | `TEXT` | |
| `resource_type` | `VARCHAR(50)` | `pdf`, `link`, `dataset`, etc. |
| `resource_url` | `TEXT` | External link or Supabase URL |
| `file_data` | `BYTEA` | Inline binary (small files) |
| `filename` | `VARCHAR(255)` | |
| `created_at` | `TIMESTAMP` | |
| `updated_at` | `TIMESTAMP` | |

---

## Progress & AI

### `exercise_progress`

| Column | Type | Notes |
|---|---|---|
| `progress_id` | `VARCHAR(255) PK` | |
| `exercise_id` | `VARCHAR(255) FK→class_exercises` | |
| `student_id` | `VARCHAR(255) FK→users` | |
| `class_id` | `VARCHAR(255) FK→classes` | Denormalized for fast leaderboard queries |
| `code` | `TEXT` | Last submitted code |
| `score` | `DECIMAL` | 0–100 |
| `status` | `VARCHAR(50)` | `not_started`, `in_progress`, `completed` |
| `attempts` | `INTEGER` | |
| `submitted_at` | `TIMESTAMP` | |
| `completed_at` | `TIMESTAMP` | |

---

### `conversations`

| Column | Type | Notes |
|---|---|---|
| `conversation_id` | `VARCHAR(255) PK` | |
| `user_id` | `VARCHAR(255) FK→users` | |
| `messages` | `JSONB` | Array of `{role, content}` |
| `created_at` | `TIMESTAMP` | |
| `updated_at` | `TIMESTAMP` | |

---

### `ai_agent_digest`

| Column | Type | Notes |
|---|---|---|
| `user_id` | `VARCHAR(255) PK FK→users` | |
| `digest` | `TEXT` | Rolling summary injected into Gemini system prompt |
| `updated_at` | `TIMESTAMP` | |

---

## Security & Auth

### `password_resets`

| Column | Type | Notes |
|---|---|---|
| `id` | `SERIAL PK` | |
| `email` | `VARCHAR(255) NOT NULL` | |
| `token` | `VARCHAR(255) NOT NULL` | Random URL-safe token |
| `expires_at` | `TIMESTAMP NOT NULL` | Default TTL: 24h (`PW_RESET_EXPIRY_HOURS`) |
| `created_at` | `TIMESTAMP` | |

**Indexes:** `(token)`, `(email)`.

---

### `audit_log`

FERPA-compliant log of all data mutations. Written by `core/audit.py` within
the same transaction as the mutating query.

| Column | Type | Notes |
|---|---|---|
| `id` | `BIGSERIAL PK` | |
| `user_id` | `TEXT` | Actor |
| `action` | `TEXT NOT NULL` | e.g. `exercise.submit`, `user.delete` |
| `resource_type` | `TEXT` | e.g. `exercise`, `class` |
| `resource_id` | `TEXT` | |
| `ip_address` | `TEXT` | |
| `details` | `JSONB` | Action-specific metadata |
| `created_at` | `TIMESTAMPTZ` | |

**Indexes:** `(user_id)`, `(created_at DESC)`.

---

## LTI 1.3

### `lti_configurations`

Registered LMS platforms.

| Column | Type | Notes |
|---|---|---|
| `config_id` | `VARCHAR(255) PK` | UUID |
| `platform_name` | `VARCHAR(255) NOT NULL` | Display name (e.g. "Canvas") |
| `issuer` | `VARCHAR(500) NOT NULL` | |
| `client_id` | `VARCHAR(255) NOT NULL` | |
| `auth_login_url` | `TEXT NOT NULL` | OIDC initiation URL |
| `auth_token_url` | `TEXT NOT NULL` | Token exchange URL |
| `key_set_url` | `TEXT NOT NULL` | JWKS endpoint |
| `deployment_ids` | `TEXT[]` | |
| `tenant_id` | `VARCHAR(255) FK→tenants` | |
| `created_by` | `VARCHAR(255) FK→users` | |
| `created_at` | `TIMESTAMP` | |
| `updated_at` | `TIMESTAMP` | |

**Unique:** `(issuer, client_id)`.

---

### `lti_sessions`

Short-lived sessions created at LTI launch.

| Column | Type | Notes |
|---|---|---|
| `session_id` | `VARCHAR(255) PK` | OIDC `state` parameter |
| `user_id` | `VARCHAR(255) FK→users CASCADE` | |
| `class_id` | `VARCHAR(255) FK→classes SET NULL` | |
| `nrps_context_url` | `TEXT` | |
| `lti_context_id` | `TEXT` | |
| `issuer` | `VARCHAR(500)` | |
| `client_id` | `VARCHAR(255)` | |
| `launch_data` | `JSONB` | Full decoded JWT claims |
| `expires_at` | `TIMESTAMP NOT NULL` | TTL set by `LTI_SESSION_TTL` |
| `created_at` | `TIMESTAMP` | |

**Indexes:** `(user_id)`, `(class_id)`, `(expires_at)`.

---

## SSO

### `tenant_sso_providers`

Per-tenant OIDC provider configuration.

| Column | Type | Notes |
|---|---|---|
| `provider_id` | `VARCHAR(255) PK` | UUID |
| `tenant_id` | `VARCHAR(255) NOT NULL FK→tenants CASCADE` | |
| `provider_name` | `VARCHAR(100) NOT NULL` | Display name |
| `provider_type` | `VARCHAR(20) NOT NULL` | `google`, `microsoft`, `oidc` |
| `client_id` | `TEXT NOT NULL` | |
| `client_secret` | `TEXT NOT NULL` | Fernet-encrypted with `SECRET_KEY` |
| `discovery_url` | `TEXT NOT NULL` | OIDC `/.well-known/openid-configuration` |
| `allowed_domains` | `TEXT[]` | Restrict sign-in to these email domains |
| `role_mapping_attribute` | `VARCHAR(100)` | OIDC claim carrying role info |
| `role_mapping` | `JSONB` | `{"Staff":"professor","Students":"student"}` |
| `default_role` | `VARCHAR(50)` | Role for unmapped claims (default `student`) |
| `is_enabled` | `BOOLEAN` | |
| `created_by` | `VARCHAR(255) FK→users` | |
| `created_at` | `TIMESTAMP` | |
| `updated_at` | `TIMESTAMP` | |

---

## Platform Administration

### `platform_config`

Key-value store for runtime-configurable platform settings.

| Column | Type | Notes |
|---|---|---|
| `key` | `VARCHAR(100) PK` | |
| `value` | `TEXT NOT NULL` | String-encoded; callers cast as needed |
| `updated_by` | `VARCHAR(255) FK→users` | |
| `updated_at` | `TIMESTAMP` | |

**Default rows:** `maintenance_mode=false`, `maintenance_message=...`,
`registration_open=true`.

---

### `announcements`

| Column | Type | Notes |
|---|---|---|
| `announcement_id` | `VARCHAR(255) PK` | UUID |
| `title` | `VARCHAR(255) NOT NULL` | |
| `message` | `TEXT NOT NULL` | |
| `type` | `VARCHAR(20)` | `info`, `warning`, `danger`, `success` |
| `target_roles` | `TEXT[]` | Empty = show to all roles |
| `is_active` | `BOOLEAN` | |
| `expires_at` | `TIMESTAMP` | NULL = no expiry |
| `created_by` | `VARCHAR(255) FK→users` | |
| `created_at` | `TIMESTAMP` | |
| `updated_at` | `TIMESTAMP` | |

---

### `ip_blocklist`

| Column | Type | Notes |
|---|---|---|
| `id` | `SERIAL PK` | |
| `ip_address` | `VARCHAR(100) UNIQUE NOT NULL` | |
| `reason` | `TEXT` | |
| `blocked_by` | `VARCHAR(255) FK→users` | |
| `created_at` | `TIMESTAMP` | |

---

## Data Flywheel (AI Quality Improvement)

### `exercise_generation_events`

Records metadata about every Gemini exercise generation call. Used to correlate
model inputs with downstream student outcomes for quality analysis.

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID PK` | |
| `exercise_id` | `VARCHAR(255)` | Soft FK to `class_exercises` |
| `class_id` | `VARCHAR(255) FK→classes` | |
| `chapter_id` | `VARCHAR(255) FK→class_chapters` | |
| `tenant_id` | `TEXT` | |
| `source_content_hash` | `VARCHAR(64)` | SHA-256 of input text |
| `source_content_type` | `VARCHAR(50)` | `pdf`, `docx`, etc. |
| `source_char_count` | `INTEGER` | |
| `was_truncated` | `BOOLEAN` | |
| `detected_language` | `VARCHAR(20)` | |
| `detected_topics` | `JSONB` | `["arrays","sorting",...]` |
| `gemini_model` | `VARCHAR(100)` | e.g. `gemini-2.5-flash` |
| `prompt_template_version` | `VARCHAR(50)` | |
| `prompt_tokens` | `INTEGER` | |
| `completion_tokens` | `INTEGER` | |
| `generation_params` | `JSONB` | Temperature, top-p, etc. |
| `difficulty_requested` | `VARCHAR(20)` | |
| `difficulty_generated` | `VARCHAR(20)` | |
| `exercise_type` | `VARCHAR(50)` | |
| `exercise_structure` | `JSONB` | |
| `num_test_cases` | `INTEGER` | |
| `generation_time_ms` | `INTEGER` | |
| `created_at` | `TIMESTAMPTZ` | |

---

### `exercise_outcome_events`

Records student attempt outcomes to close the flywheel loop.

*(Added by migration 010 — see `migrations/010_flywheel_outcome_events.sql`
for full column list.)*

---

## Infrastructure

### `schema_migrations`

Tracks which migration files have been applied. Managed exclusively by
`db_migrate.py`.

| Column | Type | Notes |
|---|---|---|
| `filename` | `VARCHAR(255) PK` | e.g. `001_lti_tables.sql` |
| `applied_at` | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` |
