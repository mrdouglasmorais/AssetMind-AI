#!/usr/bin/env bash
# Restore a gzipped pg_dump into the running Postgres container.
# DANGEROUS: replaces application data. Requires explicit CONFIRM=yes.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-infra/oci/docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-infra/oci/.env}"
DUMP="${1:?usage: restore.sh /path/to/assetmind-....sql.gz}"

if [[ "${CONFIRM:-}" != "yes" ]]; then
  echo "refusing restore without CONFIRM=yes" >&2
  exit 1
fi

# shellcheck disable=SC1090
set -a
source "$ROOT/$ENV_FILE"
set +a

gunzip -c "$DUMP" | docker compose -f "$ROOT/$COMPOSE_FILE" --env-file "$ROOT/$ENV_FILE" --project-directory "$ROOT" \
  exec -T postgres psql -U "${POSTGRES_USER:-assetmind}" -d "${POSTGRES_DB:-assetmind}"

echo "restore completed from $DUMP — run healthcheck and a smoke analysis"
