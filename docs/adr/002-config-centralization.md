# ADR-002: Centralize All Config in `config.py`

**Status:** Accepted
**Date:** 2026-03-22

---

## Context

Environment variable reads were scattered across the codebase:
- `blueprints/ai.py`, `blueprints/auth.py`, `blueprints/chapters.py`,
  `blueprints/health.py` all called `os.getenv("GEMINI_API_KEY")` or
  `os.getenv("FRONTEND_URL")` at request time.
- `core/email.py` called `os.getenv("RESEND_API_KEY")` and
  `os.getenv("MAIL_DEFAULT_SENDER")` inside the send function.
- `workers/tasks.py` called `os.getenv("RESEND_API_KEY")` and re-implemented
  Resend API calls rather than delegating to `core/email.py`.

Consequences of scattered reads:
1. No single place to see "what env vars does this app require?"
2. `config.py` already had `validate_config()` but half the code bypassed it.
3. Tests that patched `os.getenv(...)` broke whenever a file was refactored,
   since the patch target depended on call site, not value ownership.
4. Missing keys surfaced as `AttributeError` or silent `None` mid-request
   rather than at startup.

---

## Decision

**Rule:** `os.getenv()` (and `os.environ.*`) is only called inside `config.py`.
All other modules import `config` and read attributes from it.

Enforced exceptions (rationale documented inline):
- `core/auth.py` — reads `os.environ.get("FLASK_ENV")` at request time
  intentionally, to avoid caching the test-mode flag at import time.
- `core/database.py` / `core/sentry.py` — infrastructure modules that
  initialize before `config` is fully loaded; read env directly.
- `workers/tasks.py` `DatabaseTask.get_db_connection()` — reads
  `DATABASE_URL` at worker-startup time, before app context exists.

All other `os.getenv()` calls in blueprints and `core/email.py` were replaced
with `config.*` attribute access.

CI checks (`flake8` + `bandit`) run on every PR and would surface new
violations.

---

## Consequences

**Positive**
- A single `config.py` is the authoritative list of every env var the app uses.
- `validate_config()` runs at startup and fails fast if required vars are absent.
- Tests patch `config.GEMINI_API_KEY` (the attribute), not `os.getenv`
  (the call site), making patches stable across refactors.
- `RESEND_API_KEY` and `FRONTEND_URL` were added to `config.py` as part of
  this work, closing two previously untested missing-key paths.

**Negative / Trade-offs**
- `config` is a module-level singleton; tests that need to vary a value must
  `patch("config.SOME_KEY", ...)` rather than setting env vars. This is the
  trade-off for stability.
