#!/usr/bin/env bash
# Sync the repo to an OCI host and run the production Compose stack.
# Usage:
#   PUBLIC_IP=x.x.x.x ENV_FILE=./infra/oci/.env ./infra/oci/scripts/remote-up.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
PUBLIC_IP="${PUBLIC_IP:?set PUBLIC_IP to the instance public IP}"
SSH_USER="${SSH_USER:-ubuntu}"
REMOTE_DIR="${REMOTE_DIR:-/opt/assetmind}"
ENV_FILE="${ENV_FILE:-}"

if [[ -z "${ENV_FILE}" ]]; then
  echo "set ENV_FILE to a filled production env (not the example)" >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "missing ENV_FILE: $ENV_FILE" >&2
  exit 1
fi

case "$(basename "$ENV_FILE")" in
  .env.example | .env.oci.example)
    echo "refusing to deploy the example env; copy it and set real secrets" >&2
    exit 1
    ;;
esac

ssh "${SSH_USER}@${PUBLIC_IP}" "sudo mkdir -p '${REMOTE_DIR}' && sudo chown '${SSH_USER}:${SSH_USER}' '${REMOTE_DIR}'"

rsync -az --delete \
  --exclude '.git/' \
  --exclude '.venv/' \
  --exclude 'node_modules/' \
  --exclude '.terraform/' \
  --exclude '*.tfstate*' \
  --exclude '.env' \
  --exclude 'infra/oci/.env' \
  --exclude '.oci-deploy.env' \
  "${ROOT}/" "${SSH_USER}@${PUBLIC_IP}:${REMOTE_DIR}/"

scp "${ENV_FILE}" "${SSH_USER}@${PUBLIC_IP}:${REMOTE_DIR}/infra/oci/.env"

ssh "${SSH_USER}@${PUBLIC_IP}" "bash -s" <<EOF
set -euo pipefail
cd '${REMOTE_DIR}'
chmod +x infra/oci/scripts/*.sh infra/docker/entrypoint.sh
./infra/oci/scripts/deploy.sh
EOF

echo "remote deploy finished"
