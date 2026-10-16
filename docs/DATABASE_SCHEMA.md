# AnalytIQ Database Schema Reference

33 tables in PostgreSQL (>= 13 -- `gen_random_uuid()` is used as a column default).

The schema has a single home: the numbered SQL files in `migrations/`.
`migrations/000_initial_schema.sql` creates all of it from nothing and each later
migration changes it once, so

```bash
createdb analytiq && python db_migrate.py
```

is the whole setup. Nothing else in the repository creates tables -- the
integration test suite builds its schema by running these same migrations.

The table listings below are generated from a database built exactly that way,
by `scripts/dump_schema_doc.py`; see the end of this file.

## Conventions

- `user_id`, `tenant_id`, `class_id`, `chapter_id` and `exercise_id` are VARCHAR
  **strings** -- UUID text, or a human-readable join code for `class_id` -- never
  integers.
- Tables with an `id SERIAL` primary key also carry a UNIQUE business key, and
  the application joins on the business key. `users.user_id` is the identifier
  that matters; `users.id` is an implementation detail.
- `tenant_id IS NULL` means a platform-level row rather than one belonging to a
  tenant.
- `password_hash IS NULL` means an SSO-only or LTI-only account.
- Timestamps are `TIMESTAMP` (no zone) on the older tables and `TIMESTAMPTZ` on
  everything added from migration 009 onwards. New tables should use TIMESTAMPTZ.
- `exercise_id` columns outside `class_exercises` are deliberately unconstrained:
  they also hold ids of built-in practice exercises, and recorded events outlive
  the exercises they describe.

## Table index

**Identity and accounts** -- [`users`](#users) · [`user_profiles`](#user_profiles) · [`user_settings`](#user_settings) · [`user_preferences`](#user_preferences) · [`password_resets`](#password_resets)

**Multi-tenancy and SSO** -- [`tenants`](#tenants) · [`tenant_sso_providers`](#tenant_sso_providers)

**LTI 1.3** -- [`lti_configurations`](#lti_configurations) · [`lti_sessions`](#lti_sessions)

**Course content** -- [`classes`](#classes) · [`class_enrollments`](#class_enrollments) · [`class_chapters`](#class_chapters) · [`class_exercises`](#class_exercises) · [`class_resources`](#class_resources)

**Progress and grading** -- [`practice_progress`](#practice_progress) · [`exercise_attempts`](#exercise_attempts) · [`exercise_ratings`](#exercise_ratings)

**AI assistant** -- [`conversations`](#conversations) · [`conversation_messages`](#conversation_messages) · [`ai_agent_digest`](#ai_agent_digest) · [`ai_agent_memory`](#ai_agent_memory)

**Data flywheel** -- [`exercise_generation_events`](#exercise_generation_events) · [`exercise_outcome_events`](#exercise_outcome_events) · [`exercise_quality_scores`](#exercise_quality_scores)

**Student portfolios** -- [`portfolio_profiles`](#portfolio_profiles) · [`portfolio_items`](#portfolio_items) · [`portfolio_views`](#portfolio_views)

**Platform administration** -- [`platform_config`](#platform_config) · [`announcements`](#announcements) · [`ip_blocklist`](#ip_blocklist) · [`contact_submissions`](#contact_submissions) · [`audit_log`](#audit_log)

**Infrastructure** -- [`schema_migrations`](#schema_migrations)

---

## Identity and accounts

### `users`

One row per account, however it authenticates. `user_id` is the application's identifier -- a UUID string -- and every other table references it rather than the `id` surrogate key. `password_hash` is NULL for LTI-only and SSO-only accounts. `role` is one of `student`, `professor`, `tenant_admin`, `superadmin`; `is_super_admin` is a legacy duplicate of `role = 'superadmin'`. `token_version` is the JWT revocation counter: every issued token carries it as a `tv` claim and `require_auth` rejects a token whose claim no longer matches, so bumping it signs that user out everywhere. `archived_at` soft-deletes users whose tenant was removed.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | `INTEGER` | no | auto | **PK** |
| `user_id` | `VARCHAR(255)` | no |  |  |
| `name` | `VARCHAR(255)` | no |  |  |
| `email` | `VARCHAR(255)` | no |  |  |
| `password_hash` | `VARCHAR(255)` | yes |  |  |
| `role` | `VARCHAR(50)` | yes |  |  |
| `lti_sub` | `VARCHAR(255)` | yes |  |  |
| `lti_issuer` | `VARCHAR(500)` | yes |  |  |
| `created_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |
| `updated_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |
| `tenant_id` | `VARCHAR(255)` | yes |  | FK&rarr;`tenants.tenant_id` SET NULL |
| `is_super_admin` | `BOOLEAN` | yes | `false` |  |
| `account_status` | `VARCHAR(50)` | yes | `'active'` |  |
| `requires_password_reset` | `BOOLEAN` | yes | `false` |  |
| `last_login` | `TIMESTAMP` | yes |  |  |
| `sso_provider_id` | `VARCHAR(255)` | yes |  | FK&rarr;`tenant_sso_providers.provider_id` SET NULL |
| `sso_subject` | `TEXT` | yes |  |  |
| `archived_at` | `TIMESTAMP` | yes |  |  |
| `token_version` | `INTEGER` | no | `0` |  |

- Unique: `UNIQUE (email)`
- Unique: `UNIQUE (lti_sub, lti_issuer)`
- Unique: `UNIQUE (user_id)`
- Index `idx_users_archived_at`: `users (archived_at) WHERE (archived_at IS NOT NULL)`
- Index `idx_users_email`: `users (email)`
- Index `idx_users_user_id`: `users (user_id)`
- Index `uq_sso_user_identity`: `users (sso_provider_id, sso_subject) WHERE (sso_provider_id IS NOT NULL)`

### `user_profiles`

Display fields shown on the profile page. Created empty at signup (`INSERT ... ON CONFLICT DO NOTHING`), so a row exists for every user.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | `INTEGER` | no | auto | **PK** |
| `user_id` | `VARCHAR(255)` | no |  | FK&rarr;`users.user_id` CASCADE |
| `full_name` | `VARCHAR(255)` | yes |  |  |
| `bio` | `TEXT` | yes |  |  |
| `profile_picture` | `TEXT` | yes |  |  |
| `created_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |
| `updated_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |

- Unique: `UNIQUE (user_id)`

### `user_settings`

Notification and display toggles. Also created empty at signup.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | `INTEGER` | no | auto | **PK** |
| `user_id` | `VARCHAR(255)` | no |  | FK&rarr;`users.user_id` CASCADE |
| `email_notifications` | `BOOLEAN` | yes | `false` |  |
| `dark_mode` | `BOOLEAN` | yes | `false` |  |
| `created_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |
| `updated_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |

- Unique: `UNIQUE (user_id)`

### `user_preferences`

Editor language and AI-provider preferences. Also created empty at signup.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | `INTEGER` | no | auto | **PK** |
| `user_id` | `VARCHAR(255)` | no |  | FK&rarr;`users.user_id` CASCADE |
| `current_language` | `VARCHAR(50)` | yes | `'python'` |  |
| `gemini_model` | `VARCHAR(100)` | yes | `'gemini-3.5-flash'` |  |
| `ai_provider` | `VARCHAR(50)` | yes | `'gemini'` |  |
| `created_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |
| `updated_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |

- Unique: `UNIQUE (user_id)`

### `password_resets`

Short-lived reset tokens, keyed by email rather than user_id. Rows are deleted once used; the TTL is `PW_RESET_EXPIRY_HOURS`.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | `INTEGER` | no | auto | **PK** |
| `email` | `VARCHAR(255)` | no |  |  |
| `token` | `VARCHAR(255)` | no |  |  |
| `expires_at` | `TIMESTAMP` | no |  |  |
| `created_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |

- Index `idx_password_resets_email`: `password_resets (email)`
- Index `idx_password_resets_token`: `password_resets (token)`

## Multi-tenancy and SSO

### `tenants`

An institution. `email_domain` drives automatic tenant assignment at signup, and `lti_issuer` maps 1:1 with `lti_configurations.issuer`.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `tenant_id` | `VARCHAR(255)` | no | `(gen_random_uuid())` | **PK** |
| `name` | `VARCHAR(255)` | no |  |  |
| `lti_issuer` | `VARCHAR(500)` | yes |  |  |
| `is_active` | `BOOLEAN` | yes | `true` |  |
| `created_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |
| `updated_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |
| `email_domain` | `VARCHAR(255)` | yes |  |  |

- Unique: `UNIQUE (lti_issuer)`
- Index `idx_tenants_email_domain`: `tenants (email_domain) WHERE (email_domain IS NOT NULL)`

### `tenant_sso_providers`

Per-tenant OIDC configuration. `client_secret` is Fernet-encrypted with the app `SECRET_KEY`, and the repository layer only ever handles the encrypted value. `role_mapping` maps a claim value to an AnalytIQ role; `default_role` applies when nothing matches. SAML is not supported.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `provider_id` | `VARCHAR(255)` | no | `(gen_random_uuid())` | **PK** |
| `tenant_id` | `VARCHAR(255)` | no |  | FK&rarr;`tenants.tenant_id` CASCADE |
| `provider_name` | `VARCHAR(100)` | no |  |  |
| `provider_type` | `VARCHAR(20)` | no |  |  |
| `client_id` | `TEXT` | no |  |  |
| `client_secret` | `TEXT` | no |  |  |
| `discovery_url` | `TEXT` | no |  |  |
| `allowed_domains` | `TEXT[]` | yes |  |  |
| `role_mapping_attribute` | `VARCHAR(100)` | yes |  |  |
| `role_mapping` | `JSONB` | yes | `'{}'` |  |
| `default_role` | `VARCHAR(50)` | yes | `'student'` |  |
| `is_enabled` | `BOOLEAN` | yes | `true` |  |
| `created_by` | `VARCHAR(255)` | yes |  | FK&rarr;`users.user_id` SET NULL |
| `created_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |
| `updated_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |

- Index `idx_sso_providers_enabled`: `tenant_sso_providers (is_enabled) WHERE (is_enabled = true)`
- Index `idx_sso_providers_tenant`: `tenant_sso_providers (tenant_id)`

## LTI 1.3

### `lti_configurations`

A registered LMS platform (Canvas, Moodle, ...), one row per issuer/client_id pair.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `config_id` | `VARCHAR(255)` | no | `(gen_random_uuid())` | **PK** |
| `platform_name` | `VARCHAR(255)` | no |  |  |
| `issuer` | `VARCHAR(500)` | no |  |  |
| `client_id` | `VARCHAR(255)` | no |  |  |
| `auth_login_url` | `TEXT` | no |  |  |
| `auth_token_url` | `TEXT` | no |  |  |
| `key_set_url` | `TEXT` | no |  |  |
| `deployment_ids` | `TEXT[]` | yes | `'{}'` |  |
| `created_by` | `VARCHAR(255)` | yes |  | FK&rarr;`users.user_id` SET NULL |
| `created_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |
| `updated_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |
| `tenant_id` | `VARCHAR(255)` | yes |  | FK&rarr;`tenants.tenant_id` CASCADE |

- Unique: `UNIQUE (issuer, client_id)`

### `lti_sessions`

One row per LTI launch; `session_id` is the OIDC `state` parameter. Expired rows are swept by `expires_at`.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `session_id` | `VARCHAR(255)` | no |  | **PK** |
| `user_id` | `VARCHAR(255)` | yes |  | FK&rarr;`users.user_id` CASCADE |
| `class_id` | `VARCHAR(255)` | yes |  | FK&rarr;`classes.class_id` SET NULL |
| `nrps_context_url` | `TEXT` | yes |  |  |
| `lti_context_id` | `TEXT` | yes |  |  |
| `issuer` | `VARCHAR(500)` | yes |  |  |
| `client_id` | `VARCHAR(255)` | yes |  |  |
| `launch_data` | `JSONB` | yes |  |  |
| `expires_at` | `TIMESTAMP` | no |  |  |
| `created_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |

- Index `idx_lti_sessions_class_id`: `lti_sessions (class_id)`
- Index `idx_lti_sessions_expires`: `lti_sessions (expires_at)`
- Index `idx_lti_sessions_user_id`: `lti_sessions (user_id)`

## Course content

### `classes`

A professor's class. `class_id` is both the primary key and the join code students type in. The `lti_*`, `nrps_*` and `ags_*` columns are populated only for classes created through an LMS launch.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `class_id` | `VARCHAR(255)` | no |  | **PK** |
| `professor_id` | `VARCHAR(255)` | no |  | FK&rarr;`users.user_id` CASCADE |
| `name` | `VARCHAR(255)` | no |  |  |
| `description` | `TEXT` | yes |  |  |
| `lti_context_id` | `VARCHAR(500)` | yes |  |  |
| `lti_issuer` | `VARCHAR(500)` | yes |  |  |
| `nrps_context_url` | `TEXT` | yes |  |  |
| `ags_enabled` | `BOOLEAN` | yes | `false` |  |
| `ags_lineitems_url` | `TEXT` | yes |  |  |
| `created_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |
| `updated_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |
| `tenant_id` | `VARCHAR(255)` | yes |  | FK&rarr;`tenants.tenant_id` SET NULL |

### `class_enrollments`

Student-to-class membership. The UNIQUE on `(class_id, student_id)` is what makes enrolling twice a no-op.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | `INTEGER` | no | auto | **PK** |
| `class_id` | `VARCHAR(255)` | no |  | FK&rarr;`classes.class_id` CASCADE |
| `student_id` | `VARCHAR(255)` | no |  | FK&rarr;`users.user_id` CASCADE |
| `enrolled_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |

- Unique: `UNIQUE (class_id, student_id)`

### `class_chapters`

A PDF chapter within a class. The file lives in Supabase Storage (`pdf_url`), with the raw bytes kept in `pdf_data` as a fallback for deployments that have no storage configured.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `chapter_id` | `VARCHAR(255)` | no |  | **PK** |
| `class_id` | `VARCHAR(255)` | no |  | FK&rarr;`classes.class_id` CASCADE |
| `title` | `VARCHAR(255)` | no |  |  |
| `description` | `TEXT` | yes |  |  |
| `chapter_number` | `INTEGER` | yes |  |  |
| `pdf_url` | `TEXT` | yes |  |  |
| `pdf_filename` | `VARCHAR(255)` | yes |  |  |
| `pdf_data` | `BYTEA` | yes |  |  |
| `created_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |
| `updated_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |

### `class_exercises`

A coding exercise, usually generated from a chapter PDF. `test_cases` holds `[{description, input, expected_output, weight}]` and drives output-based grading; `function_name` is the function students must define. `generation_event_id` links back to the AI run that produced the exercise.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `exercise_id` | `VARCHAR(255)` | no |  | **PK** |
| `chapter_id` | `VARCHAR(255)` | no |  | FK&rarr;`class_chapters.chapter_id` CASCADE |
| `class_id` | `VARCHAR(255)` | no |  | FK&rarr;`classes.class_id` CASCADE |
| `title` | `VARCHAR(500)` | no |  |  |
| `description` | `TEXT` | yes |  |  |
| `difficulty` | `VARCHAR(50)` | yes |  |  |
| `solution_code` | `TEXT` | yes |  |  |
| `exercise_number` | `INTEGER` | yes |  |  |
| `created_by` | `VARCHAR(255)` | yes |  |  |
| `function_name` | `VARCHAR(255)` | yes | `'solution'` |  |
| `language` | `VARCHAR(50)` | yes | `'Python'` |  |
| `test_cases` | `JSONB` | yes |  |  |
| `created_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |
| `updated_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |
| `generation_event_id` | `UUID` | yes |  | FK&rarr;`exercise_generation_events.id` SET NULL |

- Index `idx_class_exercises_has_test_cases`: `class_exercises (((test_cases IS NOT NULL)))`

### `class_resources`

Supplementary files and links attached to a class. Deliberately carries no foreign keys -- it predates the conventions used elsewhere.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `resource_id` | `VARCHAR(255)` | no |  | **PK** |
| `class_id` | `VARCHAR(255)` | no |  |  |
| `user_id` | `VARCHAR(255)` | no |  |  |
| `title` | `VARCHAR(255)` | no |  |  |
| `description` | `TEXT` | yes |  |  |
| `resource_type` | `VARCHAR(50)` | no |  |  |
| `resource_url` | `TEXT` | yes |  |  |
| `file_data` | `BYTEA` | yes |  |  |
| `filename` | `VARCHAR(255)` | yes |  |  |
| `created_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |
| `updated_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |

## Progress and grading

### `practice_progress`

Current best result per (user, exercise); the UNIQUE on `(user_id, exercise_id)` is the upsert's `ON CONFLICT` target. `class_exercise_id` is the link used by the class progress and leaderboard queries, and is NULL for built-in practice exercises.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | `INTEGER` | no | auto | **PK** |
| `user_id` | `VARCHAR(255)` | no |  | FK&rarr;`users.user_id` CASCADE |
| `exercise_id` | `VARCHAR(255)` | no |  |  |
| `exercise_title` | `VARCHAR(500)` | yes |  |  |
| `class_id` | `VARCHAR(255)` | yes |  |  |
| `class_exercise_id` | `VARCHAR(255)` | yes |  |  |
| `best_score` | `INTEGER` | yes | `0` |  |
| `best_accuracy` | `NUMERIC(5,2)` | yes | `0` |  |
| `best_time` | `INTEGER` | yes |  |  |
| `total_attempts` | `INTEGER` | yes | `0` |  |
| `last_attempt_score` | `INTEGER` | yes |  |  |
| `last_attempt_accuracy` | `NUMERIC(5,2)` | yes |  |  |
| `last_attempt_time` | `INTEGER` | yes |  |  |
| `completed` | `BOOLEAN` | yes | `false` |  |
| `last_completed_at` | `TIMESTAMP` | yes |  |  |
| `created_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |
| `updated_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |

- Unique: `UNIQUE (user_id, exercise_id)`
- Index `idx_practice_user_id`: `practice_progress (user_id)`

### `exercise_attempts`

Append-only log of every graded submission. `MAX(score)` here is the trusted ceiling for a client-submitted score.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | `INTEGER` | no | auto | **PK** |
| `user_id` | `VARCHAR(255)` | no |  | FK&rarr;`users.user_id` CASCADE |
| `exercise_id` | `VARCHAR(255)` | no |  |  |
| `score` | `INTEGER` | no |  |  |
| `accuracy` | `NUMERIC(5,2)` | no |  |  |
| `time_spent` | `INTEGER` | no |  |  |
| `attempt_number` | `INTEGER` | no |  |  |
| `created_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |

### `exercise_ratings`

A student's thumbs-up/down on an exercise, upserted on `(exercise_id, user_id)`. Feeds exercise-quality analysis.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `exercise_id` | `VARCHAR(255)` | no |  | **PK** |
| `user_id` | `VARCHAR(255)` | no |  | **PK** · FK&rarr;`users.user_id` CASCADE |
| `rating` | `VARCHAR(10)` | no |  |  |
| `created_at` | `TIMESTAMPTZ` | yes | `now()` |  |

- Check: `CHECK (((rating)::text = ANY ((ARRAY['up'::character varying, 'down'::character varying])::text[])))`
- Index `idx_exercise_ratings_exercise`: `exercise_ratings (exercise_id)`

## AI assistant

### `conversations`

An AI chat thread. Deletes are soft (`deleted = true`), and `conversation_id` rather than `id` is the key the API and child rows use.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | `INTEGER` | no | auto | **PK** |
| `conversation_id` | `VARCHAR(255)` | no |  |  |
| `user_id` | `VARCHAR(255)` | no |  | FK&rarr;`users.user_id` CASCADE |
| `title` | `VARCHAR(500)` | yes |  |  |
| `archived` | `BOOLEAN` | yes | `false` |  |
| `deleted` | `BOOLEAN` | yes | `false` |  |
| `created_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |
| `updated_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |

- Unique: `UNIQUE (conversation_id)`
- Index `idx_conversations_conversation_id`: `conversations (conversation_id)`
- Index `idx_conversations_user_id`: `conversations (user_id)`

### `conversation_messages`

Messages within a thread, ordered by `message_order` rather than by timestamp.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | `INTEGER` | no | auto | **PK** |
| `conversation_id` | `VARCHAR(255)` | no |  | FK&rarr;`conversations.conversation_id` CASCADE |
| `role` | `VARCHAR(50)` | no |  |  |
| `content` | `TEXT` | no |  |  |
| `message_order` | `INTEGER` | no |  |  |
| `created_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |

- Index `idx_messages_conversation_id`: `conversation_messages (conversation_id)`

### `ai_agent_digest`

Rolling per-user context injected into the AI system prompt. One row per user, created at signup.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | `INTEGER` | no | auto | **PK** |
| `user_id` | `VARCHAR(255)` | no |  | FK&rarr;`users.user_id` CASCADE |
| `goal` | `TEXT` | yes |  |  |
| `constraints` | `TEXT` | yes |  |  |
| `decisions` | `TEXT` | yes |  |  |
| `current_state` | `TEXT` | yes |  |  |
| `open_questions` | `TEXT` | yes |  |  |
| `created_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |
| `updated_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |

- Unique: `UNIQUE (user_id)`

### `ai_agent_memory`

Individual long-lived facts the assistant remembers for a user. Replaced wholesale on update.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | `INTEGER` | no | auto | **PK** |
| `user_id` | `VARCHAR(255)` | no |  | FK&rarr;`users.user_id` CASCADE |
| `memory_item` | `TEXT` | no |  |  |
| `created_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |

- Index `idx_ai_memory_user_id`: `ai_agent_memory (user_id)`

## Data flywheel

### `exercise_generation_events`

One row per Gemini generation call: what went in, what we asked for, and what came out. `exercise_id` and `tenant_id` are unconstrained so an event survives deletion of what it refers to.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | `UUID` | no | `gen_random_uuid()` | **PK** |
| `exercise_id` | `VARCHAR(255)` | yes |  |  |
| `class_id` | `VARCHAR(255)` | yes |  | FK&rarr;`classes.class_id` SET NULL |
| `chapter_id` | `VARCHAR(255)` | yes |  | FK&rarr;`class_chapters.chapter_id` SET NULL |
| `tenant_id` | `TEXT` | yes |  |  |
| `source_content_hash` | `VARCHAR(64)` | yes |  |  |
| `source_content_type` | `VARCHAR(50)` | yes |  |  |
| `source_char_count` | `INTEGER` | yes |  |  |
| `was_truncated` | `BOOLEAN` | yes | `false` |  |
| `detected_language` | `VARCHAR(20)` | yes |  |  |
| `detected_topics` | `JSONB` | yes | `'[]'` |  |
| `gemini_model` | `VARCHAR(100)` | yes |  |  |
| `prompt_template_version` | `VARCHAR(50)` | yes |  |  |
| `prompt_tokens` | `INTEGER` | yes |  |  |
| `completion_tokens` | `INTEGER` | yes |  |  |
| `generation_params` | `JSONB` | yes | `'{}'` |  |
| `difficulty_requested` | `VARCHAR(20)` | yes |  |  |
| `difficulty_generated` | `VARCHAR(20)` | yes |  |  |
| `exercise_type` | `VARCHAR(50)` | yes |  |  |
| `exercise_structure` | `JSONB` | yes | `'{}'` |  |
| `num_test_cases` | `INTEGER` | yes |  |  |
| `generation_time_ms` | `INTEGER` | yes |  |  |
| `created_at` | `TIMESTAMPTZ` | yes | `now()` |  |

- Index `idx_gen_events_chapter`: `exercise_generation_events (chapter_id)`
- Index `idx_gen_events_class`: `exercise_generation_events (class_id)`
- Index `idx_gen_events_created`: `exercise_generation_events (created_at)`
- Index `idx_gen_events_exercise`: `exercise_generation_events (exercise_id)`

### `exercise_outcome_events`

One row per graded submission, linked back to the generation event, so model inputs can be correlated with student outcomes.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | `UUID` | no | `gen_random_uuid()` | **PK** |
| `exercise_id` | `VARCHAR(255)` | yes |  |  |
| `generation_event_id` | `UUID` | yes |  | FK&rarr;`exercise_generation_events.id` SET NULL |
| `user_id` | `TEXT` | yes |  |  |
| `class_id` | `VARCHAR(255)` | yes |  |  |
| `tenant_id` | `TEXT` | yes |  |  |
| `attempt_number` | `INTEGER` | yes |  |  |
| `time_spent_seconds` | `INTEGER` | yes |  |  |
| `hints_requested` | `INTEGER` | yes | `0` |  |
| `ai_chat_messages` | `INTEGER` | yes | `0` |  |
| `code_char_count` | `INTEGER` | yes |  |  |
| `passed` | `BOOLEAN` | yes |  |  |
| `total_score` | `NUMERIC(5,2)` | yes |  |  |
| `correctness_score` | `NUMERIC(5,2)` | yes |  |  |
| `quality_score` | `NUMERIC(5,2)` | yes |  |  |
| `tests_total` | `INTEGER` | yes |  |  |
| `tests_passed` | `INTEGER` | yes |  |  |
| `test_results` | `JSONB` | yes | `'[]'` |  |
| `error_category` | `VARCHAR(50)` | yes |  |  |
| `execution_time_ms` | `INTEGER` | yes |  |  |
| `created_at` | `TIMESTAMPTZ` | yes | `now()` |  |

- Index `idx_outcome_created`: `exercise_outcome_events (created_at)`
- Index `idx_outcome_exercise`: `exercise_outcome_events (exercise_id)`
- Index `idx_outcome_gen_event`: `exercise_outcome_events (generation_event_id)`
- Index `idx_outcome_user`: `exercise_outcome_events (user_id)`

### `exercise_quality_scores`

Per-exercise rollup of the two event tables, recomputed by a Celery task. One row per exercise.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | `UUID` | no | `gen_random_uuid()` | **PK** |
| `exercise_id` | `VARCHAR(255)` | no |  |  |
| `generation_event_id` | `UUID` | yes |  | FK&rarr;`exercise_generation_events.id` SET NULL |
| `total_attempts` | `INTEGER` | yes | `0` |  |
| `unique_students` | `INTEGER` | yes | `0` |  |
| `first_attempt_pass_rate` | `FLOAT` | yes |  |  |
| `overall_pass_rate` | `FLOAT` | yes |  |  |
| `avg_attempts_to_pass` | `FLOAT` | yes |  |  |
| `median_time_to_pass_seconds` | `INTEGER` | yes |  |  |
| `avg_hints_before_pass` | `FLOAT` | yes |  |  |
| `dropout_rate` | `FLOAT` | yes |  |  |
| `quality_score` | `FLOAT` | yes |  |  |
| `quality_label` | `VARCHAR(20)` | yes |  |  |
| `dominant_error_category` | `VARCHAR(50)` | yes |  |  |
| `common_failure_pattern` | `JSONB` | yes | `'{}'` |  |
| `last_computed_at` | `TIMESTAMPTZ` | yes | `now()` |  |
| `sample_size` | `INTEGER` | yes |  |  |

- Unique: `UNIQUE (exercise_id)`

## Student portfolios

### `portfolio_profiles`

A student's public portfolio, served at `/portfolio/{slug}`. `is_public` gates visibility; the `github_*` columns drive optional sync to a repository.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | `VARCHAR(255)` | no | `(gen_random_uuid())` | **PK** |
| `user_id` | `VARCHAR(255)` | no |  | FK&rarr;`users.user_id` CASCADE |
| `slug` | `VARCHAR(60)` | no |  |  |
| `portfolio_title` | `VARCHAR(100)` | yes |  |  |
| `display_name` | `VARCHAR(100)` | yes |  |  |
| `headline` | `VARCHAR(200)` | yes |  |  |
| `bio` | `TEXT` | yes |  |  |
| `avatar_url` | `VARCHAR(500)` | yes |  |  |
| `accent_color` | `VARCHAR(7)` | yes | `'#2569f4'` |  |
| `layout_style` | `VARCHAR(20)` | yes | `'grid'` |  |
| `linkedin_url` | `VARCHAR(300)` | yes |  |  |
| `github_username` | `VARCHAR(80)` | yes |  |  |
| `personal_website` | `VARCHAR(300)` | yes |  |  |
| `is_public` | `BOOLEAN` | yes | `false` |  |
| `github_access_token` | `TEXT` | yes |  |  |
| `github_repo_name` | `VARCHAR(200)` | yes | `'analytiq-portfolio'` |  |
| `github_sync_enabled` | `BOOLEAN` | yes | `false` |  |
| `github_last_synced_at` | `TIMESTAMPTZ` | yes |  |  |
| `created_at` | `TIMESTAMPTZ` | yes | `now()` |  |
| `updated_at` | `TIMESTAMPTZ` | yes | `now()` |  |

- Unique: `UNIQUE (slug)`
- Unique: `UNIQUE (user_id)`
- Index `idx_portfolio_slug`: `portfolio_profiles (slug)`
- Index `idx_portfolio_user`: `portfolio_profiles (user_id)`

### `portfolio_items`

An entry in a portfolio: a class exercise, a personal project, or an external link. The `source_*` columns are denormalised provenance shown on the public page.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | `VARCHAR(255)` | no | `(gen_random_uuid())` | **PK** |
| `portfolio_id` | `VARCHAR(255)` | no |  | FK&rarr;`portfolio_profiles.id` CASCADE |
| `item_type` | `VARCHAR(20)` | no |  |  |
| `exercise_id` | `VARCHAR(255)` | yes |  | FK&rarr;`class_exercises.exercise_id` SET NULL |
| `class_id` | `VARCHAR(255)` | yes |  | FK&rarr;`classes.class_id` SET NULL |
| `title` | `VARCHAR(200)` | no |  |  |
| `description` | `TEXT` | yes |  |  |
| `language` | `VARCHAR(30)` | yes |  |  |
| `code_content` | `TEXT` | yes |  |  |
| `last_output` | `TEXT` | yes |  |  |
| `last_error` | `TEXT` | yes |  |  |
| `last_run_at` | `TIMESTAMPTZ` | yes |  |  |
| `project_status` | `VARCHAR(20)` | yes | `'draft'` |  |
| `external_url` | `VARCHAR(500)` | yes |  |  |
| `tags` | `JSONB` | yes | `'[]'` |  |
| `source_class_name` | `VARCHAR(200)` | yes |  |  |
| `source_chapter_name` | `VARCHAR(200)` | yes |  |  |
| `source_institution` | `VARCHAR(200)` | yes |  |  |
| `score` | `NUMERIC(5,2)` | yes |  |  |
| `show_score` | `BOOLEAN` | yes | `false` |  |
| `display_order` | `INTEGER` | yes | `0` |  |
| `is_visible` | `BOOLEAN` | yes | `true` |  |
| `is_pinned` | `BOOLEAN` | yes | `false` |  |
| `github_synced` | `BOOLEAN` | yes | `false` |  |
| `github_file_path` | `VARCHAR(300)` | yes |  |  |
| `github_commit_sha` | `VARCHAR(40)` | yes |  |  |
| `last_saved_at` | `TIMESTAMPTZ` | yes |  |  |
| `completed_at` | `TIMESTAMPTZ` | yes |  |  |
| `created_at` | `TIMESTAMPTZ` | yes | `now()` |  |
| `updated_at` | `TIMESTAMPTZ` | yes | `now()` |  |

- Check: `CHECK (((item_type)::text = ANY ((ARRAY['class_exercise'::character varying, 'personal_project'::character varying, 'external_link'::character varying])::text[])))`
- Check: `CHECK (((project_status)::text = ANY ((ARRAY['draft'::character varying, 'published'::character varying])::text[])))`
- Index `idx_pitems_order`: `portfolio_items (portfolio_id, display_order)`
- Index `idx_pitems_portfolio`: `portfolio_items (portfolio_id)`
- Index `idx_pitems_status`: `portfolio_items (project_status)`
- Index `idx_pitems_type`: `portfolio_items (item_type)`

### `portfolio_views`

Anonymous view counter for public portfolios.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | `VARCHAR(255)` | no | `(gen_random_uuid())` | **PK** |
| `portfolio_id` | `VARCHAR(255)` | no |  | FK&rarr;`portfolio_profiles.id` CASCADE |
| `viewed_at` | `TIMESTAMPTZ` | yes | `now()` |  |
| `referrer` | `VARCHAR(500)` | yes |  |  |

- Index `idx_pviews_date`: `portfolio_views (viewed_at)`
- Index `idx_pviews_portfolio`: `portfolio_views (portfolio_id)`

## Platform administration

### `platform_config`

Key-value runtime settings, read and written by the superadmin dashboard. Migration 003 defines a wider table (with `updated_by` and `updated_at`), but every database already had the key/value table by the time 003 ran, so this two-column shape is what exists -- and only `key` and `value` are ever read.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `key` | `VARCHAR(255)` | no |  | **PK** |
| `value` | `TEXT` | no | `''` |  |

### `announcements`

Banner messages. `tenant_id IS NULL` means platform-wide, and an empty `target_roles` means all roles.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `announcement_id` | `VARCHAR(255)` | no | `(gen_random_uuid())` | **PK** |
| `title` | `VARCHAR(255)` | no |  |  |
| `message` | `TEXT` | no |  |  |
| `type` | `VARCHAR(20)` | no | `'info'` |  |
| `target_roles` | `TEXT[]` | yes | `'{}'` |  |
| `is_active` | `BOOLEAN` | yes | `true` |  |
| `expires_at` | `TIMESTAMP` | yes |  |  |
| `created_by` | `VARCHAR(255)` | yes |  | FK&rarr;`users.user_id` SET NULL |
| `created_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |
| `updated_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |
| `tenant_id` | `VARCHAR(255)` | yes |  | FK&rarr;`tenants.tenant_id` SET NULL |

- Index `idx_announcements_tenant_id`: `announcements (tenant_id)`

### `ip_blocklist`

Addresses refused by the request middleware.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | `INTEGER` | no | auto | **PK** |
| `ip_address` | `VARCHAR(100)` | no |  |  |
| `reason` | `TEXT` | yes |  |  |
| `blocked_by` | `VARCHAR(255)` | yes |  | FK&rarr;`users.user_id` SET NULL |
| `created_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |

- Unique: `UNIQUE (ip_address)`

### `contact_submissions`

Public contact-form submissions, read by the superadmin dashboard. `user_id` is NULL for signed-out visitors.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `submission_id` | `INTEGER` | no | auto | **PK** |
| `user_id` | `VARCHAR(255)` | yes |  |  |
| `name` | `VARCHAR(255)` | no |  |  |
| `email` | `VARCHAR(255)` | no |  |  |
| `subject` | `VARCHAR(255)` | no |  |  |
| `message` | `TEXT` | no |  |  |
| `status` | `VARCHAR(50)` | yes | `'submitted'` |  |
| `created_at` | `TIMESTAMP` | yes | `CURRENT_TIMESTAMP` |  |

### `audit_log`

FERPA mutation log, written by `core/audit.py` inside the same transaction as the mutation it describes, so a rolled-back operation leaves no audit row. `user_id` is unconstrained TEXT so a record outlives the actor it names.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `id` | `BIGINT` | no | auto | **PK** |
| `user_id` | `TEXT` | yes |  |  |
| `action` | `TEXT` | no |  |  |
| `resource_type` | `TEXT` | yes |  |  |
| `resource_id` | `TEXT` | yes |  |  |
| `ip_address` | `TEXT` | yes |  |  |
| `details` | `JSONB` | yes |  |  |
| `created_at` | `TIMESTAMPTZ` | yes | `now()` |  |

- Index `idx_audit_log_created_at`: `audit_log (created_at DESC)`
- Index `idx_audit_log_user_id`: `audit_log (user_id)`

## Infrastructure

### `schema_migrations`

Which migration files have been applied, one row per filename. Created and managed exclusively by `db_migrate.py`.

| Column | Type | Null | Default | Notes |
|---|---|---|---|---|
| `filename` | `VARCHAR(255)` | no |  | **PK** |
| `applied_at` | `TIMESTAMPTZ` | yes | `now()` |  |

---

## Regenerating this document

```bash
createdb analytiq_doc
DATABASE_URL=postgresql://localhost/analytiq_doc python db_migrate.py
DATABASE_URL=postgresql://localhost/analytiq_doc \
    python scripts/dump_schema_doc.py > docs/DATABASE_SCHEMA.md
```

The prose -- the conventions above and the paragraph under each table -- lives in
`scripts/dump_schema_doc.py` next to the catalogue queries. The script fails if
the database contains a table it has no note for, so a new table cannot be added
without describing it.
