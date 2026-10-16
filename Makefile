.PHONY: help dev services stop flower test test-unit test-integration test-db test-db-reset lint format typecheck migrate shell clean sandbox-image

# ─────────────────────────────────────────────────────────────────────────────
# Help
# ─────────────────────────────────────────────────────────────────────────────

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─────────────────────────────────────────────────────────────────────────────
# Development
# ─────────────────────────────────────────────────────────────────────────────

services:  ## Start PostgreSQL + Redis in Docker (background)
	docker-compose up -d db redis
	@echo "Waiting for services..."
	@sleep 2
	@echo "PostgreSQL: localhost:5432  |  Redis: localhost:6379"

flower:  ## Start Flower Celery monitoring UI (http://localhost:5555)
	docker-compose up -d flower
	@echo "Flower UI: http://localhost:5555"

dev: services  ## Start services + Flask dev server
	@cp -n .env.example .env 2>/dev/null || true
	python3 app.py

stop:  ## Stop Docker services
	docker-compose down

# ─────────────────────────────────────────────────────────────────────────────
# Testing
# ─────────────────────────────────────────────────────────────────────────────

# Integration tests build their schema from migrations/ in a disposable
# database. Override to point somewhere else:
#   make test-integration TEST_DATABASE_URL=postgresql://.../my_scratch_db
# sslmode=disable because the pool requires SSL unless told otherwise, and the
# local postgres container does not speak it.
TEST_DATABASE_URL ?= postgresql://postgres:postgres@localhost:5432/analytiq_test?sslmode=disable

test:  ## Run full test suite (unit + integration, skip e2e)
	pytest tests/ -v --ignore=tests/e2e -x

test-unit:  ## Run unit tests only
	pytest tests/unit/ -v -x

test-integration: test-db  ## Run integration tests against a disposable database
	TEST_DATABASE_URL="$(TEST_DATABASE_URL)" pytest tests/integration/ -v -x

test-e2e:  ## Run end-to-end tests (requires running app)
	pytest tests/e2e/ -v

test-cov:  ## Run tests with coverage report
	pytest tests/ --ignore=tests/e2e \
		--cov=. --cov-report=term-missing --cov-report=html \
		--cov-omit="tests/*,scripts/*,docs/*"

# ─────────────────────────────────────────────────────────────────────────────
# Code quality
# ─────────────────────────────────────────────────────────────────────────────

lint:  ## Run flake8 linter
	flake8 app.py config.py blueprints/ repositories/ core/ services/ workers/ \
		--max-line-length=100 --extend-ignore=E203,W503

format:  ## Auto-format with black
	black app.py config.py blueprints/ repositories/ core/ services/ workers/ tests/

format-check:  ## Check formatting without writing (used in CI)
	black --check app.py config.py blueprints/ repositories/ core/ services/ workers/ tests/

typecheck:  ## Run mypy type checks
	mypy app.py config.py blueprints/ repositories/ core/ services/ workers/ \
		--ignore-missing-imports --no-error-summary

# ─────────────────────────────────────────────────────────────────────────────
# Database
# ─────────────────────────────────────────────────────────────────────────────

migrate:  ## Build the schema from scratch, or apply pending migrations
	python3 db_migrate.py

test-db:  ## Create the integration-test database if it does not exist
	@docker-compose exec -T db psql -U postgres -tc \
		"SELECT 1 FROM pg_database WHERE datname = 'analytiq_test'" \
		| grep -q 1 \
		|| docker-compose exec -T db createdb -U postgres analytiq_test

test-db-reset:  ## Drop and recreate the integration-test database
	-docker-compose exec -T db dropdb -U postgres --if-exists analytiq_test
	docker-compose exec -T db createdb -U postgres analytiq_test

# ─────────────────────────────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────────────────────────────

shell:  ## Open a Python REPL with the app context loaded
	python3 -c "from app import app; ctx = app.app_context(); ctx.push(); import code; code.interact(local=locals())"

install:  ## Install Python dependencies
	pip install -r requirements.txt

clean:  ## Remove cache files and coverage artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/

sandbox-image:  ## Build the locked-down code-execution sandbox image (SANDBOX_USE_CONTAINER)
	docker build -f docker/sandbox.Dockerfile -t $${SANDBOX_CONTAINER_IMAGE:-analytiq-sandbox:latest} docker/
