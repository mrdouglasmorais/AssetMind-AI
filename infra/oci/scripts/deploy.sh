#!/usr/bin/env bash
# Deploy the production Compose stack on an already bootstrapped host.
# Run from the repository root on the VM (or via SSH after rsync).
#
# COMPOSE_PROFILE=micro|full (default full)
#   micro → prod + docker-compose.micro.yml (no worker, low memory)
#   full  → docker-compose.prod.yml only
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
COMPOSE_PROFILE="${COMPOSE_PROFILE:-full}"
ENV_FILE="${ENV_FILE:-infra/oci/.env}"
PROJECT_DIR="${PROJECT_DIR:-$ROOT}"
COMPOSE_FILE="${COMPOSE_FILE:-infra/oci/docker-compose.prod.yml}"

cd "$ROOT"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "missing $ENV_FILE — copy infra/oci/.env.example and fill secrets" >&2
  exit 1
fi

compose_args=(-f "$COMPOSE_FILE")
if [[ "$COMPOSE_PROFILE" == "micro" ]]; then
  compose_args+=(-f infra/oci/docker-compose.micro.yml)
  # Ensure queue stays off even if .env sets true.
  if grep -q '^ASSETMIND_JOB_QUEUE_ENABLED=' "$ENV_FILE"; then
    sed -i.bak 's/^ASSETMIND_JOB_QUEUE_ENABLED=.*/ASSETMIND_JOB_QUEUE_ENABLED=false/' "$ENV_FILE"
  else
    echo 'ASSETMIND_JOB_QUEUE_ENABLED=false' >>"$ENV_FILE"
  fi
fi

echo "deploy profile=$COMPOSE_PROFILE files=${compose_args[*]}"

docker compose "${compose_args[@]}" --env-file "$ENV_FILE" --project-directory "$PROJECT_DIR" build
docker compose "${compose_args[@]}" --env-file "$ENV_FILE" --project-directory "$PROJECT_DIR" --profile migrate run --rm migrate
docker compose "${compose_args[@]}" --env-file "$ENV_FILE" --project-directory "$PROJECT_DIR" up -d --remove-orphans
# Stop worker if a previous full deploy left it running on a micro host.
if [[ "$COMPOSE_PROFILE" == "micro" ]]; then
  docker compose "${compose_args[@]}" --env-file "$ENV_FILE" --project-directory "$PROJECT_DIR" stop worker 2>/dev/null || true
  docker compose "${compose_args[@]}" --env-file "$ENV_FILE" --project-directory "$PROJECT_DIR" rm -f worker 2>/dev/null || true
fi
docker compose "${compose_args[@]}" --env-file "$ENV_FILE" --project-directory "$PROJECT_DIR" ps
COMPOSE_FILE="$COMPOSE_FILE" COMPOSE_PROFILE="$COMPOSE_PROFILE" ./infra/oci/scripts/healthcheck.sh
