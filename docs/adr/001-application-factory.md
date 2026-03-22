# ADR-001: Flask Application Factory Pattern

**Status:** Accepted
**Date:** 2026-03-22

---

## Context

`app.py` was a 5,391-line monolith that handled every concern inline: Flask
initialization, logging setup, CSRF, rate limiting, Sentry, Celery bootstrap,
request hooks, error handlers, blueprint registration, frontend routes, and API
versioning aliases — all interleaved in a single file.

This made the startup sequence opaque, caused circular import risks whenever
a blueprint needed to reference `app`, and made the file essentially impossible
to test in isolation.

---

## Decision

Introduce a `core/factory.py` module that exposes one focused function per
startup concern:

| Function | Responsibility |
|---|---|
| `setup_logging(app)` | JSON logging + request-ID filter |
| `configure_app(app)` | Flask config from `config.py` |
| `setup_sentry(app)` | Sentry SDK init |
| `setup_rate_limiting(app)` | Flask-Limiter with Redis/memory |
| `setup_csrf(app)` | Flask-WTF CSRF protection |
| `setup_swagger(app)` | Swagger UI blueprint + spec endpoint |
| `setup_celery(app)` | Celery task registration |
| `register_request_hooks(app)` | before/after request: CORS, headers, request-ID |
| `register_error_handlers(app)` | Global exception handler |
| `register_blueprints(app)` | Domain blueprint registration |
| `register_frontend_routes(app)` | SPA catch-all + React route handling |
| `register_api_versioning(app)` | `/api/v1/*` aliases |
| `run_migrations(app)` | Apply pending SQL migrations at startup |

`app.py` is reduced to a `create_app()` function that calls these helpers in
sequence, plus the `if __name__ == "__main__"` entry point.

---

## Consequences

**Positive**
- Each concern can be read, reasoned about, and tested independently.
- Circular imports are eliminated: `core/factory.py` imports blueprints, not
  the other way around.
- The startup sequence is self-documenting in `app.py`.
- New features (e.g., adding a health-check warming step) require adding one
  function to `factory.py` and one line to `create_app()`.

**Negative / Trade-offs**
- One more file to be aware of (`core/factory.py`); contributors must know to
  look there, not in `app.py`, for startup logic.
- Functions are stateless helpers, not a class — slightly less OOP-idiomatic
  than Flask's `Application` class pattern, but avoids the `self` complexity.

---

## Alternatives Considered

- **Flask-CLI + `application.py` class** — more ceremony, not needed at this
  scale.
- **Keep monolith, add comments** — doesn't solve testability or import order.
