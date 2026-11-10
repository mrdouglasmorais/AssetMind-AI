#!/usr/bin/env bash
# Retry Ampere A1 creation when OCI returns Out of host capacity.
# Keeps existing VCN/subnet state. Run from infra/oci.
#
# Prefer GitHub Actions provision-and-deploy-oci when enable_compute=false.
set -euo pipefail

cd "$(dirname "$0")/.."
INTERVAL_SECONDS="${INTERVAL_SECONDS:-180}"
MAX_ATTEMPTS="${MAX_ATTEMPTS:-40}"

if grep -Eq '^[[:space:]]*enable_compute[[:space:]]*=[[:space:]]*false' terraform.tfvars 2>/dev/null; then
  echo "enable_compute=false — Terraform will not create the VM." >&2
  echo "Stop this script and use GitHub Actions: provision-and-deploy-oci" >&2
  exit 1
fi

echo "Retrying oci_core_instance.api every ${INTERVAL_SECONDS}s (max ${MAX_ATTEMPTS}). Ctrl-C to stop."
for attempt in $(seq 1 "$MAX_ATTEMPTS"); do
  echo "=== attempt ${attempt}/${MAX_ATTEMPTS} $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  if terraform apply -input=false -auto-approve -target=oci_core_instance.api; then
    instance_id="$(terraform output -raw instance_id 2>/dev/null || true)"
    public_ip="$(terraform output -raw public_ip 2>/dev/null || true)"
    if [[ -n "${instance_id}" && "${instance_id}" != "null" && -n "${public_ip}" && "${public_ip}" != "null" ]]; then
      echo "Instance created."
      terraform output
      exit 0
    fi
    echo "Apply succeeded but instance_id/public_ip are missing — not treating as success."
  fi
  echo "Still out of capacity (or other error). Sleeping ${INTERVAL_SECONDS}s..."
  sleep "$INTERVAL_SECONDS"
done
echo "Gave up after ${MAX_ATTEMPTS} attempts." >&2
exit 1
