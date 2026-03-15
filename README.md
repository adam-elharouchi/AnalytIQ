# AnalytIQ

AI-powered analytics learning platform. Live at [myanalytiq.org](https://www.myanalytiq.org).

## Tech Stack

- **Backend**: Python 3.9, Flask 3.0, PostgreSQL (Supabase), Redis + Celery
- **AI**: Google Gemini API (exercise generation, code assistant)
- **Auth**: JWT, bcrypt, per-tenant OIDC SSO
- **Deploy**: Render (web + worker), GitHub Actions CI

## Project Structure

```
app.py              Entry point; Flask app factory
config.py           Centralized env-var config

blueprints/         Flask route handlers (auth, exercises, chapters, etc.)
repositories/       Database query layer
core/               Infrastructure (db, auth, cache, middleware, email, etc.)
services/           Business logic (exercise generator, code runner, content extractor)
workers/            Celery async tasks and beat schedule
templates/          Jinja2 HTML templates
static/             JS modules, CSS, course PDFs
migrations/         SQL schema migrations
scripts/            One-off utility scripts
docs/               Documentation
tests/              pytest test suite
```

## Quick Start

```bash
cp .env.example .env          # fill in required env vars
pip install -r requirements.txt
flask --app app run
# in another terminal:
celery -A workers.celery_app.celery_app worker --loglevel=info
```

## Documentation

See [docs/README.md](docs/README.md) for the full documentation index.
