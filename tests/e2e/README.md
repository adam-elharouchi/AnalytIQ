# E2E Tests

End-to-end tests that exercise the live AnalytIQ API against a real running server and database.

## Prerequisites

- Running app (see below)
- Real PostgreSQL database (can be local or Supabase)
- `requests` library: `pip install requests`

## Start the App

```bash
FLASK_ENV=testing python app.py
```

The app will start at `http://localhost:5000`.

> **Note:** `FLASK_ENV=testing` disables Celery async tasks and caching so tests run synchronously.

## Run the Tests

```bash
# Run all E2E tests
pytest tests/e2e/ -m e2e -v

# Run a specific flow
pytest tests/e2e/test_signup_flow.py -m e2e -v
pytest tests/e2e/test_chapter_upload_flow.py -m e2e -v
pytest tests/e2e/test_exercise_flow.py -m e2e -v
pytest tests/e2e/test_ai_chat_flow.py -m e2e -v
```

## Test Flows

| File | What it covers |
|---|---|
| `test_signup_flow.py` | Signup (professor + student), duplicate email, short password, signin, wrong password |
| `test_chapter_upload_flow.py` | Upload .txt chapter, verify list, reject bad extension, student blocked |
| `test_exercise_flow.py` | Exercise list, generate-exercises trigger, 404 on bad chapter, auth guards |
| `test_ai_chat_flow.py` | Valid chat, empty/missing contents, oversized payload, >100 messages, unauth |

## Notes

- Each test creates its own unique data using random UUIDs — no shared state
- AI chat tests (`test_ai_chat_flow.py`) call the real Gemini API unless the app stubs it; set `GEMINI_API_KEY` in the environment
- These tests are **excluded** from the normal CI test run (`pytest tests/ --ignore=tests/e2e`). They run only when explicitly targeting `-m e2e`
- The `e2e` marker is registered in `setup.cfg`
