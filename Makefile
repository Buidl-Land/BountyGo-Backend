.PHONY: help install dev test lint format clean docker-build docker-up docker-down

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies
	uv pip install -e .

install-dev: ## Install development dependencies
	uv pip install -e ".[dev]"

setup: ## Setup virtual environment and install dependencies
	uv venv
	uv pip install -e ".[dev]"

dev: ## Run development server
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test: ## Run tests
	pytest -v --cov=app --cov-report=term-missing

lint: ## Run linting
	flake8 app tests
	black --check app tests
	isort --check-only app tests

format: ## Format code
	black app tests
	isort app tests

clean: ## Clean cache files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +

docker-build: ## Build Docker image
	docker build -t bountygo-backend .

docker-up: ## Start services with Docker Compose
	docker-compose up -d

docker-down: ## Stop services with Docker Compose
	docker-compose down

docker-logs: ## View Docker logs
	docker-compose logs -f

verify: ## Verify setup
	python scripts/verify_setup.py

migrate: ## Run database migrations
	alembic upgrade head

migrate-create: ## Create new migration
	alembic revision --autogenerate -m "$(name)"

migrate-downgrade: ## Downgrade migration
	alembic downgrade -1

reset-db: ## Reset database (WARNING: destroys all data)
	docker-compose down -v
	docker-compose up -d db redis
	sleep 5
	alembic upgrade head

tools-up: ## Start development tools (pgAdmin, Redis Commander)
	docker-compose --profile tools up -d

tools-down: ## Stop development tools
	docker-compose --profile tools down