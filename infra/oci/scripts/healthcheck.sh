#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${ASSETMIND_HEALTH_URL:-http://127.0.0.1/health}"
READY_URL="${ASSETMIND_READY_URL:-http://127.0.0.1/ready}"

curl -fsS "$BASE_URL" | tee /dev/stderr >/dev/null
curl -fsS "$READY_URL" | tee /dev/stderr >/dev/null
docker compose -f infra/oci/docker-compose.prod.yml --project-directory . ps
echo "healthcheck ok"
