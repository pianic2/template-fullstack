SHELL := /bin/bash
.DEFAULT_GOAL := help
COMPOSE := docker compose
BACKEND := cd apps/backend && uv run

.PHONY: help setup init dev dev-storage dev-full down logs reset doctor \
        migrate migrations shell lint typecheck test check api-schema api-client api-check \
        web-test web-e2e mobile-check docker-build format

help: ## Show available commands
	@awk 'BEGIN {FS = ":.*##"}; /^[a-zA-Z_-]+:.*##/ {printf "%-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## Install Python and JavaScript dependencies
	cd apps/backend && uv sync --all-groups
	corepack pnpm install --frozen-lockfile

init: ## Configure this clone as a new product (interactive by default)
	python3 scripts/bootstrap.py

dev: ## Start PostgreSQL, Django API and web app
	$(COMPOSE) up --build postgres backend web

dev-storage: ## Start optional S3-compatible storage and email services
	UV_EXTRA_ARGS="--extra storage" S3_STORAGE_ENABLED=true S3_BUCKET_NAME=uploads EMAIL_ENABLED=true $(COMPOSE) --profile storage --profile email up --build postgres backend web

dev-full: ## Start the core stack with optional storage and email services
	$(MAKE) dev-storage

down: ## Stop services without deleting persistent data
	$(COMPOSE) down

logs: ## Follow service logs
	$(COMPOSE) logs -f --tail=100

reset: ## Remove development containers and database volume
	$(COMPOSE) down --volumes --remove-orphans

doctor: ## Check required tools, environment and mobile compatibility metadata
	python3 scripts/doctor.py

migrate: ## Apply database migrations
	$(COMPOSE) exec backend python manage.py migrate

migrations: ## Create Django migrations for model changes
	$(BACKEND) python manage.py makemigrations

shell: ## Open a Django shell
	$(COMPOSE) exec backend python manage.py shell

api-schema: ## Generate OpenAPI from Django
	cd apps/backend && DATABASE_URL=postgresql://app:app@localhost:5432/app uv run python manage.py spectacular --file ../../openapi/openapi.yaml --validate

api-client: ## Generate TypeScript clients from the committed OpenAPI contract
	corepack pnpm exec orval --config orval.config.ts
	corepack pnpm exec prettier --write packages/api-client/src/generated

api-check: ## Regenerate schema and client and fail on drift
	bash scripts/api-check.sh

lint: ## Run Python and JavaScript lint checks
	cd apps/backend && uv run ruff check . ../../scripts && uv run ruff format --check . ../../scripts
	corepack pnpm exec eslint apps packages

typecheck: ## Type-check web, mobile, and shared TypeScript packages
	corepack pnpm --filter @template/api-client typecheck
	corepack pnpm --filter @template/web typecheck
	corepack pnpm --filter @template/mobile typecheck
	corepack pnpm --filter @template/shared typecheck

web-test: ## Run web unit and component tests
	corepack pnpm --filter @template/web exec vitest run

web-e2e: ## Run the Playwright browser smoke test (requires installed Chromium)
	corepack pnpm --filter @template/web test:e2e

mobile-check: ## Validate Expo config, dependencies, types and Android Metro bundle
	corepack pnpm --filter @template/mobile exec expo-doctor
	corepack pnpm --filter @template/mobile typecheck
	corepack pnpm --filter @template/mobile test
	corepack pnpm --filter @template/mobile exec expo export --platform android

test: ## Run backend, web, mobile, and bootstrap tests
	cd apps/backend && uv run pytest
	corepack pnpm --filter @template/web exec vitest run
	corepack pnpm --filter @template/mobile test
	python3 -m unittest discover -s scripts/tests -v

format: ## Format Python and TypeScript sources
	cd apps/backend && uv run ruff check --fix . && uv run ruff format .
	corepack pnpm exec prettier --write .

check: ## Run the repository quality gate (requires Docker for PostgreSQL)
	$(MAKE) lint typecheck test api-check mobile-check
	cd apps/backend && uv run python manage.py makemigrations --check --dry-run
	cd apps/backend && DJANGO_SECRET_KEY=ci-only-not-a-secret-ci-only-not-a-secret-ci-only-not-a-secret DJANGO_ALLOWED_HOSTS=example.com DJANGO_CORS_ALLOWED_ORIGINS=https://example.com DJANGO_CSRF_TRUSTED_ORIGINS=https://example.com uv run python manage.py check --deploy --settings=config.settings.production
	bash scripts/validate_mobile_library.py
	$(COMPOSE) config --quiet
	DATABASE_URL=postgresql://app:ci-only@localhost:5432/app DJANGO_SECRET_KEY=ci-only-not-a-secret-ci-only-not-a-secret-ci-only-not-a-secret DJANGO_ALLOWED_HOSTS=example.com DJANGO_CORS_ALLOWED_ORIGINS=https://example.com DJANGO_CSRF_TRUSTED_ORIGINS=https://example.com VITE_API_BASE_URL=https://api.example.com/api/v1 $(COMPOSE) -f compose.production.yaml config --quiet
	bash scripts/bootstrap-smoke.sh

docker-build: ## Build production backend and web images
	docker build --target production -f infra/docker/Dockerfile.backend -t template-backend:production .
	docker build --target production -f infra/docker/Dockerfile.web -t template-web:production .
