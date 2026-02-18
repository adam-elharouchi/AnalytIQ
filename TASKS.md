# AnalytIQ — Master Task List

> Generated: 2026-02-17 | Last updated: 2026-02-17
> Total: 87 tasks (25 completed, 62 pending)

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

---

## Architecture

**Current state (complete):** Flask app with 7 Blueprints for routes + 5 domain repositories (`repositories/`) for SQL data access. `db.py` for pooled Postgres; `config.py` centralizes env-based settings; `cache.py`, `celery_app.py`, `supabase_storage.py` all import `config`. No remaining architecture tasks.

---

## Code Quality

| # | Task |
|---|------|
| 11 | Unify `ALLOWED_EXTENSIONS` in `config.py` with full set: pdf, csv, xlsx, xls, json, txt, ipynb, docx; remove app.py shadow |
| 12 | Replace all `print()` calls throughout codebase with `logger.*` |
| 13 | Switch to Jinja2 server-side templates with `templates/base.html` (eliminates boilerplate across 14 HTML files) |
| 14 | Consolidate three JS fetch wrappers (`fetch`, `authFetch`, `fetchWithCache`) into single `apiClient` module |
| 15 | Extract all magic numbers/strings to `config.py` (Python) and `js/constants.js` (frontend) |
| 16 | Refactor deeply nested conditionals in app.py with guard clauses and extracted helper functions |

---

## Security

| # | Task |
|---|------|
| 19 | Query DB for users with legacy password hashes; delete `hash_password_legacy()` and fallback if none exist |
| 20 | Add `audit_log` table + `audit()` helper called on all data mutations (FERPA compliance) |

---

## CDN & Same-Origin API

> **Goal:** Make all frontend API calls use a same-origin relative path (`/api`) with zero deployment-specific domain logic anywhere in the frontend. Prepare the app for Cloudflare CDN by making static assets safely cacheable while ensuring all API responses are explicitly prevented from being cached by any intermediary.
>
> **Dependency order:** CDN-1 → CDN-2 → CDN-3 (verify). CDN-4 and CDN-5 are independent backend changes and can run in parallel with the JS changes. CDN-7 follows CDN-4/5. CDN-6 is already complete.

| # | Task |
|---|------|
| CDN-1 | **Remove hardcoded URL from `js/api-helper.js`.** Lines 4–12 have an `isLocal` ternary that sets `API_BASE_URL` to `http://localhost:5001/api` or `https://analytiq-qbfr.onrender.com/api`. Replace the entire block with: `window.API_BASE_URL = '/api';`. This single relative path works in both local dev (Flask serves frontend and API on the same origin) and production (same-origin on Render). No environment detection needed. |
| CDN-2 | **Remove all remaining hardcoded URL fallbacks — 7 locations across JS and HTML files.** (a) `js/student-classes.js` lines 4–12: same isLocal ternary as CDN-1, replace with `window.API_BASE_URL = '/api'`. (b) `js/profile.js` line 4: directly hardcodes Render URL, replace with `window.API_BASE_URL = '/api'`. (c) `js/auth.js` lines 4–7: uses `window.location.origin + '/api'`, simplify to `window.API_BASE_URL = '/api'` for consistency. (d) `reset-password.html` line 93: inline fallback `window.API_BASE_URL \|\| 'https://analytiq-qbfr.onrender.com/api'` — replace fallback value with `'/api'`. (e) `practice-playground.html` line 898: isLocal ternary — replace with `'/api'`. (f) `practice-playground.html` line 1191: inline fallback — replace with `'/api'`. (g) `chapter-view.html` line 1588: isLocal ternary — replace with `'/api'`. |
| CDN-3 | **Verify resource URL construction after CDN-1/2.** `js/professor-class.js` (~line 1080) and `js/student-class.js` (line 587) both build absolute resource URLs by extracting `new URL(API_BASE_URL).origin`. Both are guarded by `if (window.API_BASE_URL && window.API_BASE_URL.startsWith('http'))` — so with `API_BASE_URL = '/api'` the guard evaluates false and server-relative URLs (e.g. `/api/resources/files/...`) pass through unchanged, which is correct for same-origin. Action: after CDN-1/2, confirm resource download links still work; remove the stale comment in `professor-class.js` (~line 1070) that references `analytiq-qbfr.onrender.com`. No functional code change expected. |
| CDN-4 | **Add `Cache-Control` headers for static assets in `after_request`.** Currently `after_request` in `app.py` only sets security and CORS headers for paths starting with `/api`. For non-API responses (HTML, JS, CSS, images), add `Cache-Control: public, max-age=86400` in production (`config.ENV == 'production'`) only — keep `no-cache` behaviour in development so local changes are always fresh. This enables Cloudflare to cache static assets at the edge. |
| CDN-5 | **Add explicit no-cache headers on all API responses.** In `after_request`, inside the existing `if request.path.startswith("/api"):` block, add: `Cache-Control: no-store, no-cache, must-revalidate, max-age=0` and `Pragma: no-cache`. This prevents Cloudflare (or any proxy/browser cache) from ever storing API responses, which would break auth-gated data and produce stale reads. |
| CDN-7 | **Update `render.yaml` with a `headers` section** to set long-lived `Cache-Control` on static asset paths (`/js/*`, `/css/*`, image paths). Complements CDN-4 so Cloudflare edge nodes respect caching intent at the infrastructure level. If Render's `headers` support in `render.yaml` is insufficient, document the equivalent Cloudflare Page Rules / Transform Rules as an alternative. |

---

## Performance — Frontend

| # | Task |
|---|------|
| 24 | Create `ui-states.js` with `showLoading()`, `showEmpty()`, `showContent()` + CSS skeleton loaders |
| 25 | `apiClient` returns structured result objects (`{ok, data, error}`); pages render error state with retry button |
| 26 | Add Cloudflare CDN in front of Render for static asset caching (depends on CDN-1 through CDN-5, CDN-7) |
| 27 | Add global 401 interceptor in `apiClient` → redirect to login with session-expired message |

---

## Performance — Backend

| # | Task |
|---|------|
| 28 | Add payload size cap (50KB, 100 messages) on AI chat endpoint before forwarding to Gemini |
| 29 | Add `@require_auth` to both leaderboard endpoints; remove `email` from response; cap `limit` at `MAX_PAGE_SIZE` |
| 30 | Make storage non-critical in health check; add 30s cache on health check results |
| 31 | Add per-user rate limit on AI chat: 20/min, 100/hr, keyed by `user_id` |
| 32 | Apply `@cache_response` to the 8 most-read endpoints + add cache invalidation on writes |
| 33 | Replace N+1 loop in professor analytics with a single aggregated JOIN query + 60s cache |
| 34 | Supabase presigned upload URLs — frontend uploads PDFs directly to Supabase, bypassing the Flask server |
| 35 | Append-only conversation messages — frontend sends delta only, backend inserts single row (no full-replace) |

---

## Reliability

| # | Task |
|---|------|
| 36 | Add structured `AI_UNAVAILABLE` error response + circuit breaker for Gemini API failures |
| 37 | Create `offline-detector.js` with connection banner + write queue for critical operations |
| 38 | Add Gunicorn `post_fork` + `worker_exit` hooks in `gunicorn.conf.py` for DB pool lifecycle management |

---

## Observability

| # | Task |
|---|------|
| 40 | Generate UUID `request_id` in `before_request`; add to all logger calls, Sentry scope, and `X-Request-ID` response header |
| 41 | Add PostHog free tier for business metrics (review FERPA before including student identifiers) |
| 42 | Split health check: public `/api/health` returns status only; `/api/health/detail` requires `@require_auth` |

---

## Testing

| # | Task |
|---|------|
| 43 | Consolidate 56 coverage-farming test files into feature-organized behavioral tests |
| 44 | Add `tests/integration/` with real DB integration tests for core flows (CI already spins up Postgres + Redis) |
| 45 | Add password validation to signup (min 8, max 72 chars), align reset-password endpoint, add tests |
| 47 | Add Playwright E2E tests for 4 core flows: signup, upload chapter, generate exercises, AI chat |
| 48 | Add k6 load tests for 3 scenarios: login burst, exercise list, AI chat concurrent users |
| 49 | Add `tests/test_security.py` with 401/403 assertions for all authenticated endpoints |

---

## UI / UX

| # | Task |
|---|------|
| 50 | Add empty state per page: illustration + CTA (e.g. "No chapters yet — upload your first PDF") |
| 51 | Add `ConfirmModal` component in `ui-states.js` for all destructive actions (delete class, delete chapter) |
| 52 | Add debounced localStorage autosave (500ms) for exercise playground with restore-on-load |

---

## Design System

| # | Task |
|---|------|
| 53 | Add CSS custom properties (`--color-primary`, `--spacing-md`, `--radius-sm`, etc.) in `:root` block; update all ~30 hardcoded `#2569f4` references |

---

## Documentation

| # | Task |
|---|------|
| 55 | Replace `SECURITY_AUDIT_COMPLETE.md` with accurate `SECURITY.md` |
| 56 | Verify `exercises-database.js` is unreferenced anywhere, then delete it |
| 57 | Add AUTO-GENERATED label to `knowledge_base/` files; write human-maintained `ARCHITECTURE.md` |
| 58 | Auto-generate OpenAPI 3.0 docs via Flask-Smorest; expose Swagger UI at `/api/docs` |

---

## Developer Experience

| # | Task |
|---|------|
| 59 | Remove `continue-on-error` from flake8 + black CI steps (keep it for mypy and bandit) |
| 60 | Add email validation helper + standardize 400 error response shape across all endpoints |

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

2. **CDN & same-origin API** — remove hardcoded URLs, add cache headers, prepare for Cloudflare:
   Tasks CDN-1, CDN-2, CDN-3, CDN-4, CDN-5, CDN-7
   > Start with CDN-1 then CDN-2 (JS/HTML URL cleanup), then CDN-3 (verify resource links). CDN-4/5 (backend cache headers) can be done in parallel. CDN-7 last. CDN-6 is already done.

3. **Backend performance** — caching, rate limiting, leaderboard fixes:
   Tasks 28, 29, 30, 31, 32, 33, 34, 35

4. **Frontend** — apiClient, ui-states, design tokens:
   Tasks 13, 14, 15, 24, 25, 26, 27, 53

5. **Testing** — consolidate + add integration + security tests:
   Tasks 43, 44, 45, 47, 48, 49

6. **Security (remaining)** — legacy hashes, audit log:
   Tasks 19, 20

7. **LMS Integration** — LTI 1.3 + roster sync:
   Tasks LMS-1 through LMS-6

8. **External Content Import** — multi-format + OER platforms:
   Tasks LIB-1 through LIB-7

9. **Long-term** — accessibility audit, Flask-Smorest migration:
   Tasks 58, 65
