#!/bin/sh
# Roles: api | worker | migrate
set -eu

ROLE="${1:-${ASSETMIND_ROLE:-api}}"
if [ "$#" -gt 0 ]; then
  shift
fi

case "$ROLE" in
  api)
    exec uvicorn assetmind.main:app --host 0.0.0.0 --port "${PORT:-8000}" "$@"
    ;;
  worker)
    exec python -m assetmind.worker "$@"
    ;;
  migrate)
    exec alembic upgrade head "$@"
    ;;
  *)
    echo "unknown role: $ROLE (expected api|worker|migrate)" >&2
    exit 1
    ;;
esac
