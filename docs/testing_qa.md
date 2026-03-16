# Testing & QA

## Framework

- **Runner:** `pytest`
- **Plugins:** `pytest-cov` (coverage), `pytest-mock`
- **Config:** `pytest.ini` (root)

## Running Tests

```bash
# All unit tests
pytest tests/unit/ -q

# With coverage
pytest tests/unit/ --cov=. --cov-report=html

# Single file
pytest tests/unit/test_auth.py -v

# Skip slow integration tests
pytest tests/unit/ --ignore=tests/e2e -q
```

## Test Structure

```
tests/
  conftest.py        # Shared fixtures — mocks DB, provides test Flask app
  unit/              # All unit tests (mock DB via monkeypatch)
    test_auth.py
    test_exercises_routes.py
    test_chapters_routes.py
    test_classes_routes.py
    test_users_routes.py
    test_superadmin_*.py
    test_tenant_admin.py
    test_sso_*.py
    test_lti.py
    test_content_extractor.py
    test_pdf_processor.py
    test_tasks.py
    test_flywheel.py
    test_utils.py
    test_security.py
    test_module_init.py
    test_sentry_config.py
    test_zz_app_reload.py
    (+ more)
```

## Auth Bypass in Tests

When `TESTING=True`, any request with `X-Test-User-ID: <uuid>` header skips JWT validation.
The conftest fixture sets this automatically for all test clients.

The bypass requires **both** `app.config["TESTING"] == True` **and** `config.ENV != "production"` — it cannot fire in a production process.

## DB Mocking

All unit tests patch `core.database.get_db_connection` in `conftest.py` and return a `MagicMock` connection. This means:
- No real database required for unit tests
- SQL is never executed
- Return values must be set in individual test mocks

Integration tests (in `tests/integration/`, if present) require a real `DATABASE_URL`.

## Coverage

Current target: **70%** overall.

Priority areas: authentication, authorization, database operations, API endpoints.

```bash
# Generate HTML report
pytest tests/unit/ --cov=. --cov-report=html
open htmlcov/index.html
```

## CI Pipeline

GitHub Actions runs on every push/PR to `main` or `develop`:

1. **test** — spins up Postgres 14 + Redis 7, runs `flake8 + black --check + pytest --cov`
2. **security-scan** — Bandit static analysis
3. **deploy-notification** — logs "ready for Render" on `main` push
