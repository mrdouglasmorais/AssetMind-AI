# OCI Always Free deployment

Primary host for AssetMind. See also [oci-audit.md](oci-audit.md), [ADR 0022](../adr/0022-oci-always-free.md), and [ADR 0024](../adr/0024-durable-worker.md).

## Topology (economic profile)

```text
Internet
   │
   ▼
Caddy (:80/:443)  ──►  API (:8000, internal)
                         │
                         ├──► PostgreSQL (internal volume)
                         └──► Worker (internal; queue claim in Phase 3)
```

Planning envelope: **2 OCPU / 12 GB** Ampère A1 Flex. Confirm the tenancy Always Free remaining capacity before raising OCPU/RAM. Do not allocate every megabyte to containers.

| Container | mem_limit | cpus | Notes |
| --- | --- | --- | --- |
| postgres | 1536m | 0.50 | conservative `shared_buffers` / `max_connections` |
| api | 1536m | 0.50 | FastAPI; AgentOS off |
| worker | 2048m | 0.75 | Agno + NumPy headroom; concurrency 1 |
| proxy | 256m | 0.25 | Caddy |
| *(host)* | ~remaining | — | kernel, Docker, page cache, SSH |

Expanded profile (only if free capacity exists): up to 4 OCPU / 24 GB; raise worker concurrency after measuring real memory, not before.

## Deploy commands (no automatic apply)

```bash
# On the VM after SSH + bootstrap
sudo ./infra/oci/scripts/bootstrap.sh
cp infra/oci/.env.example infra/oci/.env   # fill secrets
chmod +x infra/oci/scripts/*.sh
./infra/oci/scripts/deploy.sh
./infra/oci/scripts/healthcheck.sh
```

Migrations run once via Compose profile `migrate`. The API image does **not** migrate on every start.

## Security posture

- OCI + UFW: 22 (admin CIDR), 80, 443 only.
- Postgres and worker: no published ports.
- API: reached only through Caddy.
- Secrets: `infra/oci/.env`, never git.
- Always Free does **not** remove availability or data-loss risk. Same-disk backups are not DR.

## Backup

```bash
./infra/oci/scripts/backup.sh
# Then copy /var/backups/assetmind/*.sql.gz to OCI Object Storage (Always Free tier).
CONFIRM=yes ./infra/oci/scripts/restore.sh /var/backups/assetmind/assetmind-….sql.gz
```

## Credentials

Step-by-step OCI API key + GitHub secrets: [oci-credentials.md](oci-credentials.md).

## Out of host capacity (Ampere A1)

Always Free `VM.Standard.A1.Flex` in the home region often returns `Out of host capacity`. Networking (VCN/subnet) can remain; only the instance is missing.

Preferred path: GitHub Actions workflow **`provision-and-deploy-oci`** tries every 2 hours. If there is no capacity it **exits green** (no deploy). If the VM appears it deploys compose. See [oci-credentials.md](oci-credentials.md).

Local fallback: `infra/oci/scripts/retry-instance.sh` (only while Terraform still has `enable_compute = true`).

Ampere Always Free is limited to the **home region**. Switching region for free A1 is not a general workaround.

## Phase status

| Phase | Status |
| --- | --- |
| 1 Audit | Done — `oci-audit.md` |
| 2 Docker ARM64 + Compose prod | Done |
| 3 Durable worker / job lease | Done — `analysis_jobs`, ADR 0024 |
| 4 Terraform | Authored; `apply` requires operator |
| 5 CI/CD | `ci.yml` ARM64 publish + `deploy-oci.yml` (manual) |
| 6 Live VM validation | Pending your `terraform apply` + first deploy |
