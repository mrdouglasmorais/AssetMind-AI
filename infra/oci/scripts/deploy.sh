#!/usr/bin/env bash
# Deploy the production Compose stack on an already bootstrapped host.
# Run from the repository root on the VM (or via SSH after rsync).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-infra/oci/docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-infra/oci/.env}"
PROJECT_DIR="${PROJECT_DIR:-$ROOT}"

cd "$ROOT"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "missing $ENV_FILE — copy infra/oci/.env.example and fill secrets" >&2
  exit 1
fi

docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" --project-directory "$PROJECT_DIR" build
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" --project-directory "$PROJECT_DIR" --profile migrate run --rm migrate
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" --project-directory "$PROJECT_DIR" up -d --remove-orphans
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" --project-directory "$PROJECT_DIR" ps
./infra/oci/scripts/healthcheck.sh
