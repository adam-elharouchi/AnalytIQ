# ADR-004: Celery Task Retry Strategy

**Status:** Accepted
**Date:** 2026-03-22

---

## Context

All six Celery tasks (`process_pdf_and_extract_text`, `generate_exercises_async`,
`send_email_async`, `compute_exercise_quality_scores`, `cleanup_expired_lti_sessions`,
`process_chapter_upload`) previously had no retry logic. On any exception they
returned `{"success": False, "error": str(e)}` and terminated. Transient
failures — network blips to Supabase, momentary Gemini API rate limits, SMTP
timeouts — permanently failed without any automatic recovery.

Additionally:
- `generate_exercises_async` used a 6-column SQL INSERT that was missing
  `function_name`, `test_cases`, and `language`, writing incomplete rows.
- `send_email_async` re-implemented the Resend API call inline with
  `os.getenv()` calls, bypassing `core/email.py` and `config.py`.
- `cleanup_expired_lti_sessions` opened its own `psycopg2.connect()` rather
  than using the `DatabaseTask` base class.
- No Celery monitoring UI (`flower`) was deployed.

---

## Decision

### Retry pattern

Each task uses Celery's `self.retry()` with exponential backoff, wrapped in a
`try/except MaxRetriesExceededError` block that returns the error dict on final
failure:

```python
except Exception as e:
    logger.warning("task failed (attempt %d): %s", self.request.retries + 1, e)
    try:
        raise self.retry(exc=e, countdown=DELAY * (2 ** self.request.retries))
    except self.MaxRetriesExceededError:
        return {"success": False, "error": str(e), ...}
```

This means:
- In production (Celery worker): `Retry` propagates to the worker machinery,
  which re-queues the task after `countdown` seconds.
- After `max_retries` are exhausted: `MaxRetriesExceededError` is caught,
  task terminates with an error dict (not an exception).
- In unit tests (direct call): `retry` is mocked to raise
  `MaxRetriesExceededError` immediately, so tests get the error dict
  deterministically without any retry delay.

### Per-task limits

| Task | `max_retries` | Base `countdown` |
|---|---|---|
| `process_pdf_and_extract_text` | 2 | 30 s |
| `generate_exercises_async` | 3 | 60 s |
| `send_email_async` | 3 | 30 s |
| `process_chapter_upload` | 1 | 60 s |

### Other fixes included in this change

- `generate_exercises_async` — INSERT now includes all 11 columns
  (`function_name`, `test_cases`, `language`, `exercise_id` as UUID,
  `exercise_number` queried from DB).
- `send_email_async` — delegates to `core.email.send_email()` instead of
  re-implementing Resend calls.
- `cleanup_expired_lti_sessions` — converted to `DatabaseTask` base class
  for consistent connection management.

### Flower monitoring

- Added `flower==2.0.1` to `requirements.txt`.
- Added `flower` service to `docker-compose.yml` (port 5555, depends on Redis).
- Added `make flower` target to `Makefile`.
- Flower UI: `http://localhost:5555` in local dev.

---

## Consequences

**Positive**
- Transient Gemini/SMTP/Supabase errors recover automatically without
  manual re-triggering.
- Exponential backoff reduces thundering-herd pressure during outages.
- `generate_exercises_async` no longer writes incomplete exercise rows.
- All tasks use a consistent connection/config/email pattern.
- Flower gives real-time visibility into task queues and failure rates.

**Negative / Trade-offs**
- A failing task now occupies a worker slot for longer (up to
  `countdown * (2^max_retries)` seconds total delay).
- The `try/except MaxRetriesExceededError` pattern is Celery-specific
  boilerplate; test mocking of `self.retry` requires an explicit
  `patch.object(task, 'retry', side_effect=MaxRetriesExceededError())`.

---

## Alternatives Considered

- **`autoretry_for=(Exception,)`** — simpler decorator syntax; ruled out
  because it raises `MaxRetriesExceededError` to the caller rather than
  returning an error dict, which breaks callers that check `result["success"]`.
- **Dead-letter queue (DLQ)** — better for async failure auditing; deferred
  as a future enhancement once Flower confirms failure patterns.
