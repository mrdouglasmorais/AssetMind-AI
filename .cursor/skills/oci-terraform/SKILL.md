---
name: oci-terraform
description: Provisions or changes AssetMind hosting on Oracle Cloud Always Free with Terraform. Use when editing infra/oci, docker-compose.prod.yml, Caddy, OCI networking, or Ampere deploy docs.
---

# OCI Terraform (Always Free)

1. Keep one compute host. Do not add Kubernetes or a service per agent.
2. Prefer `VM.Standard.A1.Flex` within the tenancy Ampere budget. Confirm remaining free capacity; do not assume 4 OCPU / 24 GB.
3. Run PostgreSQL in Docker on the host. Do not switch the app to Autonomous Database.
4. Production Compose is `infra/oci/docker-compose.prod.yml` (Caddy + API + worker + Postgres).
5. Publish only 80/443 on the host. Do not publish Postgres, worker, or API ports.
6. Leave AgentOS disabled on the public host.
7. Keep secrets in gitignored `terraform.tfvars` and `infra/oci/.env`.
8. Restrict SSH with `ssh_allowed_cidr` (`/32` preferred).
9. Migrate once via Compose profile `migrate`; never race Alembic from API and worker.
10. Do not claim `terraform apply` or a live deploy succeeded unless an operator recorded it.
11. Durable job claim is ADR 0024 / Phase 3 — do not enable `ASSETMIND_JOB_QUEUE_ENABLED` until that lands.
