# AnalytIQ — Master Task List

> Generated: 2026-02-17 | Last updated: 2026-02-17
> Total: 73 tasks (17 completed, 56 pending)

---

## ✅ Completed

| # | Task |
|---|------|
| 17 | Remove `SECURITY_AUDIT_COMPLETE.md` credentials from git history, gitignore it, force-push |
| 18 | Add `FLASK_ENV` check guard in `require_auth` — `X-Test-User-ID` bypass now blocked when `config.ENV == 'production'` |
| 21 | Added `Content-Security-Policy-Report-Only` header on all responses; removed deprecated `X-XSS-Protection` header |
| 22 | Verified: role assignment is backend-only (`detect_role_from_email()`); frontend only reads role from JWT response |
| 23 | Added 12 input field limit constants to `config.py`; added `validate_fields()` helper to `app.py` |
| 46 | `git rm --cached .coverage coverage.xml` — coverage artifacts removed from git tracking |
| 54 | Updated `docs/PROJECT_OVERVIEW.md` with all 15 actual HTML filenames |
| 61 | Created `.env.example` with all 40+ env vars from `config.py`, grouped and annotated |
| 62 | Added JS load order comments to all 14 HTML files |
| 63 | Created `.pre-commit-config.yaml` (black + flake8 + detect-secrets) |
| 64 | Created `render.yaml` with `healthCheckPath: /api/health` for zero-downtime deploys |
| EX-1 | Rewrote `python/exercise_generator.py` prompt — one concept per exercise, 5–10 lines max, every line commented, no chained ops, no list comprehensions, good/bad examples in prompt |

---

## Architecture

| # | Task |
|---|------|
| 1 | Extract Flask Blueprints per domain: auth, classes, chapters, exercises, users, ai, health |
| 2 | Add `repositories/` layer (SQL separated from route handlers) alongside Blueprints |
| 3 | Create `db.py` connection module; import `config.py` in `cache.py`, `celery_app.py`, `supabase_storage.py` |
| 4 | Add `@require_role` decorator reading `g.user_role`; remove redundant DB role re-queries per endpoint |
| 5 | Delete per-endpoint OPTIONS handling blocks (the `before_request` hook already covers CORS) |
| 6 | Set DB pool `maxconn = CPU_COUNT * 2` (8); rely on Supabase Pooler for overflow |
| 7 | Celery `on_failure` callback → log to Sentry + update DB task status + surface user-facing error state |
| 8 | Create `response_helpers.py` with `api_success()`, `api_error()`, `api_list()` — use everywhere |

---

## Code Quality

| # | Task |
|---|------|
| 9 | Replace all `str(e)` (80 instances) with `logger.error()` + generic client message; add `@app.errorhandler(500)` |
| 10 | Replace timestamp-based `user_id` generation with `uuid.uuid4()` |
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
| 17 | Add `FLASK_ENV` check guard in `require_auth` to block `X-Test-User-ID` bypass in production |
| 18 | Enable CSRF protection by default; audit all API endpoints for `@csrf_exempt` coverage; add where missing |
| 19 | Query DB for users with legacy password hashes; delete `hash_password_legacy()` and fallback if none exist |
| 20 | Add `audit_log` table + `audit()` helper called on all data mutations (FERPA compliance) |
| 21 | Add CSP header in `report-only` mode first, then switch to enforcement; remove deprecated `X-XSS-Protection` |
| 22 | Confirm email domain mapping in backend only: `student.hult.edu` → student, `hult.edu` / `faculty.hult.edu` → professor; remove role logic from frontend |
| 23 | Add input length limits as config constants + `validate_fields()` helper applied at all write endpoints |

---

## Performance — Frontend

| # | Task |
|---|------|
| 24 | Create `ui-states.js` with `showLoading()`, `showEmpty()`, `showContent()` + CSS skeleton loaders |
| 25 | `apiClient` returns structured result objects (`{ok, data, error}`); pages render error state with retry button |
| 26 | Add Cloudflare CDN in front of Render for static asset caching |
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
| 39 | Create `validate_schema()` helper and apply it to all write endpoints |

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
| 46 | `git rm --cached` for `.coverage`, `coverage.xml`, `htmlcov/` (already in `.gitignore`) |
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
| 54 | Update `PROJECT_OVERVIEW.md` to reference actual HTML file names |
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
| 61 | Create `.env.example` with all required env vars and placeholder values + setup guide |
| 62 | Add load order comments to HTML files for JS script tags |
| 63 | Add `.pre-commit-config.yaml` with black (format), flake8 (lint), detect-secrets (block credential commits) |
| 64 | Configure `render.yaml` with `healthCheckPath: /api/health` for zero-downtime deploys |

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

## Exercise Generator — Prompt Quality

| # | Task |
|---|------|
| EX-1 | Refine `exercise_generator.py` prompt to produce beginner-friendly, digestible solution code — one concept per exercise, 5–10 lines max per solution, no chained operations, every line commented, mirrors the simplicity of the coding assistant's output. Exercises that are currently too dense (e.g. computing mean + std + above/below average + proportions in one block) must be broken into separate focused exercises, each doing exactly one thing. Add explicit prompt constraints: no nested logic, no list comprehensions, no method chaining, prefer named intermediate variables, use `print()` to show results clearly. |

---

## Recommended Implementation Order

1. **Quick wins** — no behaviour change, low risk:
   Tasks 46, 54, 56, 57, 61, 62, 63, 64,

2. **Security fixes** — highest urgency:
   Tasks 17, 18, 19, 20, 21, 22, 23

3. **Reliability foundation** — unblocks everything else:
   Tasks 8, 9, 10, 39 (response_helpers, validate_schema, error handling)

4. **Architecture** — Blueprint + repository extraction:
   Tasks 1, 2, 3, 4, 5, 6, 7

5. **Backend performance** — caching, rate limiting, leaderboard fixes:
   Tasks 28, 29, 30, 31, 32, 33, 34, 35

6. **Frontend** — apiClient, ui-states, design tokens:
   Tasks 13, 14, 15, 24, 25, 27, 53

7. **Testing** — consolidate + add integration + security tests:
   Tasks 43, 44, 45, 47, 48, 49

8. **LMS Integration** — LTI 1.3 + roster sync:
   Tasks LMS-1 through LMS-6

9. **External Content Import** — multi-format + OER platforms:
   Tasks LIB-1 through LIB-7

10. **Long-term** — accessibility audit, Flask-Smorest migration:
    Tasks 58, 65
