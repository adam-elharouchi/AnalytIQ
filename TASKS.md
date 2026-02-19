# AnalytIQ — Master Task List

> Generated: 2026-02-17 | Last updated: 2026-02-19
> Total: 87 tasks (55 completed, 32 pending)

---

## ✅ Completed

| # | Task |
|---|------|
| CRED | Removed credentials from `docs/SECURITY_AUDIT_COMPLETE.md` git history; file gitignored and force-pushed |
| Sec-17 | Added `config.ENV != 'production'` guard in `require_auth` — `X-Test-User-ID` bypass blocked in production |
| Sec-18 | Audited CSRF coverage — all API routes use JWT Bearer (stateless), so `@csrf_exempt` on all API routes is architecturally correct; no changes needed |
| Sec-21 | Added `Content-Security-Policy-Report-Only` header on all responses; removed deprecated `X-XSS-Protection` header |
| Sec-22 | Verified: role assignment is backend-only (`detect_role_from_email()`); frontend only reads role from JWT response |
| Sec-23 | Added 12 input field limit constants to `config.py`; added `validate_fields()` helper to `auth_helpers.py` |
| 8 | Created `response_helpers.py` with `api_success()`, `api_error()`, `api_list()` — used in global error handler and new routes |
| 9 | Replaced all `str(e)` in 500 responses → `logger.error(..., exc_info=True)` + generic client message; added `@app.errorhandler(Exception)` catch-all (HTTPExceptions pass through unchanged). Remaining `str(e)` in codebase are only in `logger.extra={}` fields (logging only, never client-exposed) or health-status diagnostic dicts truncated to 200 chars |
| 10 | Replaced timestamp-based `user_id` with `uuid.uuid4()` — no more collision risk |
| 39 | Applied `validate_fields()` to 7 write endpoints: class create, profile update, password change (min 8 / max 72), chapter update, exercise create/update, contact form |
| 46 | `git rm --cached .coverage coverage.xml` — coverage artifacts removed from git tracking; both entries confirmed in `.gitignore` |
| 54 | Updated `docs/PROJECT_OVERVIEW.md` with all 15 actual HTML filenames |
| 61 | Created `.env.example` with all 40+ env vars from `config.py`, grouped and annotated |
| 62 | Added JS load order comments to all 14 HTML files |
| 63 | Created `.pre-commit-config.yaml` (black + flake8 + detect-secrets) |
| 64 | Created `render.yaml` with `healthCheckPath: /api/health` for zero-downtime deploys |
| EX-1 | Rewrote `python/exercise_generator.py` prompt — one concept per exercise, 5–10 lines max, every line commented, no chained ops, no list comprehensions, good/bad examples in prompt |
| 1 | Extracted 7 Flask Blueprints: `blueprints/{health,ai,auth,users,chapters,exercises,classes}.py` + `db.py` connection module. `app.py` reduced from 5,391 → 412 lines (3 routes remain: swagger, `/`, catch-all) |
| 2 | Added `repositories/` layer — `{auth,chapter,class,exercise,user}_repository.py`. All SQL extracted from blueprints using `cur.execute` pattern; 0 raw SQL calls remain in any blueprint. Blueprints call repo methods; routes handle only validation, auth, and response shaping |
| 3 | `cache.py`, `celery_app.py`, `supabase_storage.py` all `import config` — verified. `db.py` created as connection pool module |
| 4 | Added `@require_role("professor")` to `create_class`; replaced 8 DB role re-queries with `g.user_role` from JWT across `classes.py` and `chapters.py` |
| 5 | Per-endpoint OPTIONS handling blocks removed during Blueprint extraction (`before_request` hook covers CORS) |
| 6 | DB pool `maxconn` set to `(os.cpu_count() or 4) * 2` via `config.DB_POOL_MAX_CONNECTIONS` — overridable via `DB_POOL_MAX` env var |
| 7 | Added `on_failure` callback to Celery `DatabaseTask` base class with structured error logging |
| CDN-6 | Verified: `after_request` in `app.py` already sets `connect-src 'self'` in the CSP header. Gemini API is a server-side proxy (`/api/ai/chat`) — no browser requests ever go directly to `generativelanguage.googleapis.com`. No code change needed |
| CDN-1 | Removed `isLocal` ternary from `js/api-helper.js`; replaced with `window.API_BASE_URL = '/api'` |
| CDN-2 | Removed all 7 hardcoded URL fallbacks: `student-classes.js`, `profile.js`, `auth.js`; inline fallbacks in `reset-password.html`, `practice-playground.html` (×2), `chapter-view.html` — all replaced with `'/api'` |
| CDN-3 | Removed 15-line stale comment block in `professor-class.js` referencing `onrender.com`; replaced with one-line explanation of same-origin behaviour. Removed dead `startsWith('http')` guard in `student-class.js`. Server-relative paths pass through correctly with same-origin `API_BASE_URL` |
| CDN-4 | Added `Cache-Control: public, max-age=86400` for non-API responses in production in `after_request` |
| CDN-5 | Added `Cache-Control: no-store, no-cache, must-revalidate, max-age=0` + `Pragma: no-cache` for all `/api/*` responses in `after_request` |
| CDN-7 | Added Cloudflare Cache Rule documentation to `render.yaml` (Render web services don't support route-level headers in YAML — Flask `after_request` headers are the correct mechanism; Cloudflare edge just needs to respect `Cache-Control: public`) |
| 53 | Added 60+ CSS custom properties in `:root` (colors, spacing, radii, shadows, typography, transitions); replaced all ~65 `#2569f4` and ~21 `#222c3e` hardcoded references across `styles.css`, 8 HTML files, and 6 JS files |
| 28 | Added 50KB (`MAX_AI_MESSAGE_LENGTH`) + 100-message (`MAX_AI_CONVERSATION_MESSAGES`) payload cap in `blueprints/ai.py` — oversized requests are rejected before forwarding to Gemini (400 / 413) |
| 29 | Added `@require_auth` to both leaderboard endpoints (`/api/exercises/<id>/leaderboard`, `/api/leaderboard/grand`); removed `email` field from responses; capped `limit` at `config.MAX_PAGE_SIZE` |
| 30 | Made Supabase Storage non-critical in health check (failure logs warning, does not set `all_healthy = False`); added 30s in-process result cache on `/api/health` |
| 31 | Added per-user rate limits on `/api/ai/chat` — 20 req/min + 100 req/hr keyed by `g.user_id` via `_apply_ai_rate_limits` conditional-wrapper decorator |
| 33 | Replaced O(n²) `for ex in exercises` scan inside `get_class_progress` with an `exercise_lookup` dict built once in O(n); inner lookup is now O(1) |
| 32 | Updated `cache_response` in `cache.py` to include `g.user_id` in key (prevents cross-user leakage) and handle tuple returns. Applied to 8 endpoints: `get_class`, `get_class_chapters`, `get_chapter_exercises`, `get_exercise_details`, `get_profile`, `get_enrolled_classes`, `get_class_average_leaderboard` (classes already cached manually). Added write-side `invalidate_cache` calls on all corresponding create/update/delete routes |
| 34 | Added `GET /api/chapters/upload-url` endpoint in `blueprints/chapters.py` — returns `{upload_url, storage_path}` Supabase presigned URL via `supabase_storage.get_presigned_upload_url()`. Added `getPresignedUploadUrl(filename)` to `js/api-helper.js` for frontend use |
| 35 | Added `POST /api/users/conversations/<id>/messages` append-only endpoint in `blueprints/users.py`. Added `append_conversation_message()` to `repositories/user_repository.py` using `COALESCE(MAX(message_order), -1) + 1` INSERT. Added `conversationAPI.appendMessage()` to `js/api-helper.js` |
| 14 | Created `js/api-client.js` — unified `window.apiClient` with `get`, `post`, `put`, `del`, `upload` methods returning `{ok, data, error}` structured results; 401 interceptor clears tokens and redirects to `auth.html?reason=session_expired` |
| 15 | Created `js/constants.js` — `window.APP_CONSTANTS` centralising auth localStorage keys, pagination defaults, UI timing, difficulty colors, file upload limits |
| 24 | Created `js/ui-states.js` — `uiStates.showLoading()` (CSS skeleton shimmer cards), `showEmpty()` (empty state + CTA), `showError()` (retry button), `showContent()`; CSS injected once on first call |
| 25 | `apiClient` returns structured `{ok, data, error}` result objects — pages can now render error state with retry button |
| 27 | 401 interceptor added to `apiClient` in `js/api-client.js` → clears `authToken` + `currentUser` from localStorage, redirects to `auth.html?reason=session_expired&redirect=<current-page>` |
| 45 | Password min 8 / max 72 validation added to `POST /api/users/signup` and `POST /api/users/reset-password` using `config.MIN_PASSWORD_LENGTH` / `config.MAX_PASSWORD_LENGTH`; 4 existing tests updated from short test passwords |
| 49 | Created `tests/test_security.py` — 51 tests, one per authenticated endpoint, all asserting 401 when no Bearer token is provided. Covers users (20), classes (16), chapters (8), exercises (6), AI (1). Acts as auth-regression guard in CI. |
| 43 | Deleted 38 `test_app_*.py` coverage-farming files; replaced with 6 domain-organized behavioral test files: `test_auth.py` (18), `test_classes_routes.py` (27), `test_chapters_routes.py` (23), `test_exercises_routes.py` (18), `test_users_routes.py` (38), `test_ai_routes.py` (8). Tests verify response shape and business rules, not just status code ranges. |
| 50 | Replaced all inline `innerHTML` empty-state blobs across `professor-dashboard.js`, `professor-class.js`, `student-class.js`, `student-classes.js`, `code-assistant.js` with `uiStates.showEmpty()` / `uiStates.showError()` calls. |
| 51 | Added `uiStates.showConfirmModal()` to `js/ui-states.js` (animated backdrop, Esc/click-outside-to-cancel, danger/cancel styling). Replaced all 6 browser `confirm()` calls: `deleteClass`, `deleteResource`, `deleteExercise`, `deleteConversation`, `clearChat`. |
| 52 | Added 500ms debounced localStorage autosave in `practice-playground.html` (key: `analytiq_draft_<exercise_id>`). Draft restored on load, cleared on submit. |
| 55 | Created `docs/SECURITY.md` — covers auth, JWT, rate limits, password policy, input validation limits, security headers, CSP, file upload, CSRF, FERPA audit log, CI scan, known TODOs. |
| 57 | Created `docs/ARCHITECTURE.md` (full system reference: tech stack, repo layout, request lifecycle, DB schema, auth flow, AI pipeline, frontend patterns, Celery, deployment, CI/CD, design decisions). Prepended `AUTO-GENERATED` comment to all 21 `docs/knowledge_base/*.md` files. |

---

## Architecture

**Current state (complete):** Flask app with 7 Blueprints for routes + 5 domain repositories (`repositories/`) for SQL data access. `db.py` for pooled Postgres; `config.py` centralizes env-based settings; `cache.py`, `celery_app.py`, `supabase_storage.py` all import `config`. No remaining architecture tasks.

---

## Code Quality

**Tasks 11 and 12 complete.** `ALLOWED_EXTENSIONS` unified in `config.py` (full set: pdf, csv, xlsx, xls, json, txt, ipynb, docx); shadows removed from `app.py` and `blueprints/chapters.py`. All `print()` calls in production web-server files replaced with structured `logger.*` — messages now appear in Render's JSON log viewer with `request_id` tracing. Remaining:

| # | Task |
|---|------|
| 13 | Switch to Jinja2 server-side templates with `templates/base.html` (eliminates boilerplate across 14 HTML files) |
| 14 | Consolidate three JS fetch wrappers (`fetch`, `authFetch`, `fetchWithCache`) into single `apiClient` module |
| 15 | Extract all magic numbers/strings to `config.py` (Python) and `js/constants.js` (frontend) |
| 16 | Refactor deeply nested conditionals in app.py with guard clauses and extracted helper functions |

---

## Security

**Tasks 19, 20 complete.** `scripts/check_legacy_hashes.py` created — run against production DB. `audit.py` created with `ensure_audit_log_table()` + `audit()` helper; wired into 12 mutation endpoints across 5 blueprints (CREATE_USER, RESET_PASSWORD, UPDATE_PROFILE, UPDATE_PASSWORD, DELETE_USER, EXERCISE_SUBMISSION, CREATE_CLASS, DELETE_CLASS, ENROLL_CLASS, CREATE_CHAPTER, DELETE_CHAPTER, DELETE_EXERCISE). Table uses lazy creation with thread-safe flag; audit rows commit atomically with the business operation. **Section complete.**

---

## CDN & Same-Origin API

**Current state (complete):** All 7 CDN tasks done. `API_BASE_URL` is now `/api` everywhere — zero hardcoded hostnames in JS or HTML. `after_request` sets `Cache-Control: no-store` on all `/api/*` responses and `Cache-Control: public, max-age=86400` on static assets in production. `render.yaml` documents the Cloudflare Cache Rule setup needed to activate edge caching.

---

## Performance — Frontend

**Tasks 14, 15, 24, 25, 26, 27 complete.** `js/api-client.js`, `js/ui-states.js`, `js/constants.js` created; `ProxyFix` added to `app.py` for Cloudflare; all 17 HTML files updated with new script tags. **Section complete.**

---

## Performance — Backend

**Tasks 28–35 complete.** All backend performance tasks done.

---

## Reliability

**Tasks 36, 37, 38 complete.** `_CircuitBreaker` trips after 5 Gemini failures (auto-resets 60s); `js/offline-detector.js` shows red banner on `window.offline`; Gunicorn `post_fork`/`worker_exit`/`worker_abort` hooks reset the psycopg2 pool after fork. **Section complete.**

---

## Observability

**Tasks 40 and 42 complete.** `assign_request_id()` before_request generates `g.request_id = uuid4()` on every request; `_RequestIdFilter` injects it into all JSON log records; `X-Request-ID` response header emitted; Sentry tagged. Public `/api/health` returns `{"status":"healthy|degraded"}` only; `/api/health/detail` (`@require_auth`) returns full per-service diagnostics. Remaining:

| # | Task |
|---|------|
| 41 | Add PostHog free tier for business metrics — **deferred pending FERPA review** (student identifiers must not be sent without legal sign-off) |

---

## Testing

**Tasks 43, 44, 45 and 49 complete.** `tests/integration/` created with 31 real-DB tests across 2 files: `test_auth_integration.py` (13 tests — user insert, profile/settings/preferences rows, duplicate-email constraint, password reset token validation) and `test_classes_integration.py` (18 tests — class CRUD, cascade deletes, enrollment uniqueness, chapter/exercise ops, audit_log writes). Tests use savepoint-per-test isolation, skip gracefully when DATABASE_URL is absent, and run automatically in CI alongside unit tests. Remaining:

| # | Task |
|---|------|
| 47 | Add Playwright E2E tests for 4 core flows: signup, upload chapter, generate exercises, AI chat |
| 48 | Add k6 load tests for 3 scenarios: login burst, exercise list, AI chat concurrent users |

---

## UI / UX

**Tasks 50, 51, 52 complete.** `uiStates.showConfirmModal()` added to `js/ui-states.js`; replaces all 6 browser `confirm()` calls. `showEmpty()` / `showError()` wired into 5 JS files. 500ms debounced autosave + restore added to exercise playground. **Section complete.**

---

## Design System

**Current state (complete):** Task 53 done. Comprehensive `:root` design token system added to `css/styles.css` with 60+ CSS custom properties covering colors (`--color-primary`, `--color-dark`, semantic error/success/warning/info colors, badge colors), spacing (`--spacing-xs` through `--spacing-2xl`), border radii (`--radius-xs` through `--radius-pill`), shadows, typography (font families, sizes, line heights), layout, and transitions. All ~65 hardcoded `#2569f4` and ~21 `#222c3e` references replaced across `styles.css`, 8 HTML files, and 6 JS files. Legacy aliases (`--primary-color`, `--primary-dark`, `--secondary-color`) preserved for backward compatibility.

---

## Documentation

**Task 56 complete.** `js/exercises-database.js` deleted; `practice-playground.html` updated to remove script tag and replace `ALL_EXERCISES` reference with `[]` (exercises now served from API). Remaining:

**Tasks 55, 57 complete.** `docs/SECURITY.md` and `docs/ARCHITECTURE.md` created. All 21 `knowledge_base/*.md` files labeled AUTO-GENERATED. Remaining:

| # | Task |
|---|------|
| 58 | Auto-generate OpenAPI 3.0 docs via Flask-Smorest; expose Swagger UI at `/api/docs` |

---

## Developer Experience

**Tasks 59, 60 complete.** `continue-on-error` removed from flake8 + black CI steps. `validate_email()` added to `auth_helpers.py` (RFC 5321 regex + max-length check); wired into `signup`, `forgot_password` (auth.py) and `update_profile` (users.py). 400 response shape was already consistent `{"error": "..."}` across all 41 endpoints. **Section complete.**

---

## Accessibility

| # | Task |
|---|------|
| 65 | Run axe-core audit on all 14 pages; fix ARIA labels, focus rings, keyboard-navigable modals, alt text, color contrast; produce `ACCESSIBILITY.md` |

---

## LMS Integration

> Target LMS platforms: Canvas, Blackboard, Moodle, Google Classroom, D2L Brightspace
> Standard: LTI 1.3 + LTI Advantage (Names and Roles Provisioning Service)

| # | Task |
|---|------|
| LMS-1 | Add `lti_config` table — store `client_id`, JWKS URL, token URL, auth URL per LMS platform per institution |
| LMS-2 | Implement OIDC login initiation + callback: `/lti/login`, `/lti/launch` using `pylti1.3` library |
| LMS-3 | Implement NRPS roster sync — "Sync Students" button pulls enrolled list from Canvas/Blackboard into AnalytIQ class |
| LMS-4 | Add LTI deep linking — professors link specific AnalytIQ classes/chapters from inside their LMS |
| LMS-5 | Build professor LTI setup UI — generate tool XML/JSON config file to paste into Canvas/Blackboard admin |
| LMS-6 | Add `lti_sessions` table — map LMS user identities to AnalytIQ `user_id`; handle first-time vs returning LTI users |

---

## External Content Import

> Sources: file uploads, package docs, arbitrary URLs, OpenStax, LibreTexts, OER Commons

| # | Task |
|---|------|
| LIB-1 | Extend upload support to `.ipynb`, `.docx`, `.csv`, `.txt` with format-specific text extractors |
| LIB-2 | PyPI package doc importer — professor enters package name, system fetches official docs, converts to chapter |
| LIB-3 | URL content importer — paste any URL (GitHub README, article, blog post), system scrapes + converts to chapter |
| LIB-4 | OpenStax importer — browse OpenStax catalog via API, pick book + chapter, import directly |
| LIB-5 | LibreTexts importer — browse by subject/book via API, import chapter content |
| LIB-6 | OER Commons importer — search by keyword/subject, preview, import |
| LIB-7 | Unified Import UI — single modal with tabs: Upload File / Paste URL / Package Docs / Browse OER / OpenStax & LibreTexts |

---

## Recommended Implementation Order

1. ~~**Architecture** — Blueprint + repository extraction~~ **DONE** (tasks 1–7)

2. ~~**CDN & same-origin API**~~ **DONE** (tasks CDN-1 through CDN-7)

3. ~~**Backend performance** — caching, rate limiting, leaderboard fixes, presigned URLs, append-only messages (28–35 done)~~

4. ~~**Frontend** — apiClient, ui-states, design tokens (14, 15, 24, 25, 27, 53 done)~~:
   Remaining: Task 13 (Jinja2 templates), Task 26 (Cloudflare CDN — infrastructure)

5. **Testing** — consolidate + add integration + security tests:
   ~~Tasks 43, 45, 49 done~~ — Remaining: Tasks 44, 47, 48

6. **Security (remaining)** — legacy hashes, audit log:
   Tasks 19, 20

7. **LMS Integration** — LTI 1.3 + roster sync:
   Tasks LMS-1 through LMS-6

8. **External Content Import** — multi-format + OER platforms:
   Tasks LIB-1 through LIB-7

9. **Long-term** — accessibility audit, Flask-Smorest migration:
   Tasks 58, 65
