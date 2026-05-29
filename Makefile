.PHONY: help install lint test run worker migrate

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -r requirements.txt

lint: ## Run linting (ruff + mypy)
	ruff check src/ tests/
	mypy src/

test: ## Run test suite
	pytest tests/

test-unit: ## Run unit tests only
	pytest tests/unit/

test-integration: ## Run integration tests only
	pytest tests/integration/

run: ## Start FastAPI dev server
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

worker: ## Start Celery worker
	celery -A src.workers.celery_app worker --loglevel=info

migrate: ## Run database migrations
	alembic upgrade head
