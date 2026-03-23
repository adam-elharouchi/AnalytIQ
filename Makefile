.PHONY: help dev services stop flower frontend frontend-dev frontend-build frontend-typecheck test test-unit test-integration lint format typecheck migrate shell clean

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
# Frontend (React + TypeScript)
# ─────────────────────────────────────────────────────────────────────────────

frontend-dev:  ## Start Vite dev server (proxies /api to Flask on :5001)
	cd frontend && npm run dev

frontend-build:  ## Build React app to static/react/
	cd frontend && npm run build

frontend-typecheck:  ## Run TypeScript type check on frontend
	cd frontend && npm run typecheck

frontend:  ## Install frontend deps + build
	cd frontend && npm install && npm run build

# ─────────────────────────────────────────────────────────────────────────────
# Testing
# ─────────────────────────────────────────────────────────────────────────────

test:  ## Run full test suite (unit + integration, skip e2e)
	pytest tests/ -v --ignore=tests/e2e -x

test-unit:  ## Run unit tests only
	pytest tests/unit/ -v -x

test-integration:  ## Run integration tests (requires live DB + Redis)
	pytest tests/integration/ -v -x

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

migrate:  ## Apply pending SQL migrations
	python3 db_migrate.py

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
