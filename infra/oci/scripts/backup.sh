#!/usr/bin/env bash
# Logical Postgres backup. Off-box copy is required for disaster recovery.
# Example Object Storage sync is documented; this script only produces a dump file.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-infra/oci/docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-infra/oci/.env}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/assetmind}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${BACKUP_DIR}/assetmind-${STAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"
# shellcheck disable=SC1090
set -a
source "$ROOT/$ENV_FILE"
set +a

docker compose -f "$ROOT/$COMPOSE_FILE" --env-file "$ROOT/$ENV_FILE" --project-directory "$ROOT" \
  exec -T postgres pg_dump -U "${POSTGRES_USER:-assetmind}" -d "${POSTGRES_DB:-assetmind}" --format=plain \
  | gzip -c >"$OUT"

ln -sfn "$OUT" "$BACKUP_DIR/assetmind-latest.sql.gz"
echo "wrote $OUT"
echo "copy this file off the VM (OCI Object Storage Always Free) before relying on it for DR"
