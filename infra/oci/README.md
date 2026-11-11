# OCI Always Free

Terraform provisions the network (and optionally the VM). Docker Compose runs the application stack. GitHub Actions owns compute when `enable_compute = false`.

**No `terraform apply` or production deploy is performed from CI without explicit operator secrets and approval.**

Credentials and GitHub secrets: [`docs/architecture/oci-credentials.md`](../../docs/architecture/oci-credentials.md).

Provision with soft capacity skip: `.github/workflows/provision-and-deploy-oci.yml` (schedule + manual). Tries **E2.1.Micro** then **A1.Flex**.

## Layout

| Path | Role |
| --- | --- |
| `docker-compose.prod.yml` | Caddy + API + worker + Postgres (A1 / full) |
| `docker-compose.micro.yml` | Override for E2.1.Micro: low memory, no worker |
| `Caddyfile` | HTTPS, security headers, SSE flush |
| `.env.example` | Secrets template → `.env` |
| `scripts/bootstrap.sh` | Docker Engine + UFW on the VM |
| `scripts/deploy.sh` | Build, migrate once, up (`COMPOSE_PROFILE=micro\|full`) |
| `scripts/ci_try_provision.py` | Dual-shape launch with soft-skip |
| `scripts/backup.sh` / `restore.sh` | `pg_dump` / restore |
| `scripts/healthcheck.sh` | HTTP + compose ps |
| `*.tf` | VCN, subnet, security list, optional instance |

Human guide: [`docs/architecture/oci-deployment.md`](../../docs/architecture/oci-deployment.md).

## Always Free planning (not a guarantee)

| Profile | Shape | RAM | Stack |
| --- | --- | --- | --- |
| Micro (pipeline default) | `VM.Standard.E2.1.Micro` | ~1 GB + 2 GB swap | proxy + api + postgres |
| A1 economic | `VM.Standard.A1.Flex` 1–2 OCPU | 6–12 GB | + worker |
| A1 expanded | ≤4 OCPU | ≤24 GB | only if free Ampere remains |

## Terraform

```bash
cd infra/oci
cp terraform.tfvars.example terraform.tfvars
# set tenancy, keys, ssh_allowed_cidr (/32)
terraform init
terraform plan
# terraform apply   # only with operator authorization
```

`shape_config` applies only to Flex shapes. Security list defaults: SSH from `ssh_allowed_cidr`, HTTP 80, HTTPS 443. The API port is **not** published on the host when using Compose prod.

## Application deploy

```bash
# Full (A1)
./infra/oci/scripts/deploy.sh

# Micro (E2.1.Micro)
COMPOSE_PROFILE=micro ./infra/oci/scripts/deploy.sh
```

## Local compatibility

Day-to-day development stays on `make watch` / `infra/docker/docker-compose.yml` (API + Postgres + UI). Production Compose is OCI-oriented and disables AgentOS.
