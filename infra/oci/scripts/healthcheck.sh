#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${ASSETMIND_HEALTH_URL:-http://127.0.0.1/health}"
READY_URL="${ASSETMIND_READY_URL:-http://127.0.0.1/ready}"
COMPOSE_FILE="${COMPOSE_FILE:-infra/oci/docker-compose.prod.yml}"
COMPOSE_PROFILE="${COMPOSE_PROFILE:-full}"

compose_args=(-f "$COMPOSE_FILE")
if [[ "$COMPOSE_PROFILE" == "micro" ]]; then
  compose_args+=(-f infra/oci/docker-compose.micro.yml)
fi

curl -fsS "$BASE_URL" | tee /dev/stderr >/dev/null
curl -fsS "$READY_URL" | tee /dev/stderr >/dev/null
docker compose "${compose_args[@]}" --project-directory . ps
echo "healthcheck ok"
