.DEFAULT_GOAL := help

HOST ?= 0.0.0.0
PORT ?= 8000
IMAGE ?= assetmind-ai:local
COMPOSE ?= docker compose

.PHONY: help init install ui-install watch run build up down logs test lint format typecheck migrate secrets check clean

help:
	@printf '%s\n' \
		'AssetMind AI' \
		'' \
		'  make init        Create .env when missing and install dependencies' \
		'  make install     Sync the uv environment, including dev tools' \
		'  make ui-install  Install the Agent UI dependencies' \
		'  make watch       API with reload and the Agent UI on port 3000' \
		'  make run         API without reload' \
		'  make build       Build the Docker image $(IMAGE)' \
		'  make up          Build and start the API with local Postgres' \
		'  make down        Stop the Compose stack' \
		'  make logs        Follow API logs from Compose' \
		'  make test        Run pytest' \
		'  make lint        Ruff check' \
		'  make format      Ruff format' \
		'  make typecheck   Pyright' \
		'  make migrate     Apply Alembic migrations' \
		'  make secrets     Scan the tree for obvious secrets' \
		'  make check       Lint, format check, types, tests, and secret scan' \
		'  make clean       Remove local caches and the SQLite file'

init:
	@if [ ! -f .env ]; then cp .env.example .env; echo 'Created .env from .env.example'; else echo '.env already exists'; fi
	@perl -i -pe 's/^ASSETMIND_API_KEY=$$/ASSETMIND_API_KEY=local-dev-key/' .env
	uv sync --all-groups
	$(MAKE) ui-install
	@echo 'Local API key is local-dev-key when that line was empty. Replace it before any shared environment.'
	@echo 'Next: make watch'

install:
	uv sync --all-groups

ui-install:
	cd ui/agent-ui && corepack pnpm install --frozen-lockfile

watch:
	@set -a; [ -f .env ] && . ./.env; set +a; \
	export ASSETMIND_AGENTOS_ENABLED=true; \
	export NEXT_PUBLIC_AGENT_OS_URL="http://127.0.0.1:$(PORT)"; \
	export NEXT_PUBLIC_OS_SECURITY_KEY="$${ASSETMIND_AGENT_UI_TOKEN:-$${ASSETMIND_OS_SECURITY_KEY:-$$ASSETMIND_API_KEY}}"; \
	test -d ui/agent-ui/node_modules || $(MAKE) ui-install; \
	PYTHONPATH=src uv run uvicorn assetmind.main:app --host $(HOST) --port $(PORT) --reload --reload-dir src & \
	api_pid=$$!; \
	trap 'kill $$api_pid' EXIT INT TERM; \
	cd ui/agent-ui && corepack pnpm dev

run:
	ASSETMIND_AGENTOS_ENABLED=$${ASSETMIND_AGENTOS_ENABLED:-true} \
	PYTHONPATH=src uv run uvicorn assetmind.main:app --host $(HOST) --port $(PORT)

build:
	docker build -t $(IMAGE) .

up:
	$(COMPOSE) up --build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f api

test:
	uv run pytest

lint:
	uv run ruff check src tests migrations scripts

format:
	uv run ruff format src tests migrations scripts

typecheck:
	uv run pyright

migrate:
	uv run alembic upgrade head

secrets:
	uv run python scripts/scan_secrets.py

check: lint
	uv run ruff format --check src tests migrations scripts
	uv run pyright
	uv run pytest
	uv run python scripts/scan_secrets.py

clean:
	rm -rf .pytest_cache .ruff_cache htmlcov .coverage
	rm -f assetmind.db
