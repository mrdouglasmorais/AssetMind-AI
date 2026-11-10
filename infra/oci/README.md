# OCI Always Free

Terraform provisions the VM and network. Docker Compose runs the application stack.

**No `terraform apply` or production deploy is performed from CI without explicit operator secrets and approval.**

## Layout

| Path | Role |
| --- | --- |
| `docker-compose.prod.yml` | Caddy + API + worker + Postgres |
| `Caddyfile` | HTTPS, security headers, SSE flush |
| `.env.example` | Secrets template → `.env` |
| `scripts/bootstrap.sh` | Docker Engine + UFW on the VM |
| `scripts/deploy.sh` | Build, migrate once, up |
| `scripts/backup.sh` / `restore.sh` | `pg_dump` / restore |
| `scripts/healthcheck.sh` | HTTP + compose ps |
| `*.tf` | VCN, subnet, security list, A1 Flex instance |

Human guide: [`docs/architecture/oci-deployment.md`](../../docs/architecture/oci-deployment.md).

## Always Free planning (not a guarantee)

| Profile | OCPU | RAM | Notes |
| --- | --- | --- | --- |
| Economic (default Compose limits) | 2 | 12 GB | One worker, concurrency 1 |
| Expanded | ≤4 | ≤24 GB | Only if free capacity remains |

Verify remaining Ampere quota in the tenancy console before changing shape_config.

## Terraform

```bash
cd infra/oci
cp terraform.tfvars.example terraform.tfvars
# set tenancy, keys, ssh_allowed_cidr (/32)
terraform init
terraform plan
# terraform apply   # only with operator authorization
```

Security list defaults: SSH from `ssh_allowed_cidr`, HTTP 80, HTTPS 443. The API port is **not** published on the host when using Compose prod.

## Application deploy

```bash
sudo ./scripts/bootstrap.sh
cp .env.example .env   # fill values
cd ../..               # repo root
./infra/oci/scripts/deploy.sh
```

## Local compatibility

Day-to-day development stays on `make watch` / `infra/docker/docker-compose.yml` (API + Postgres + UI). Production Compose is OCI-oriented and disables AgentOS.
