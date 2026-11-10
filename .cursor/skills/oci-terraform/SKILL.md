---
name: oci-terraform
description: Provisions or changes AssetMind hosting on Oracle Cloud Always Free with Terraform. Use when editing infra/oci, infra/docker/docker-compose.oci.yml, OCI networking, or Ampere deploy docs.
---

# OCI Terraform (Always Free)

1. Keep one compute host. Do not add a service per agent.
2. Prefer `VM.Standard.A1.Flex` within the tenancy Ampere budget (4 OCPU / 24 GB).
3. Run PostgreSQL in Docker on the host. Do not switch the app to Autonomous Database.
4. Bind the API to `0.0.0.0` and `$PORT` (compose publishes 8000).
5. Leave AgentOS disabled on the public host.
6. Keep secrets in gitignored `terraform.tfvars` and the host `.env`. Never commit state or live keys.
7. Restrict SSH with `ssh_allowed_cidr`. Prefer the operator `/32`.
8. Deploy with `infra/docker/docker-compose.oci.yml` from the repo root.
9. Do not claim `terraform apply` or a live deploy succeeded unless an operator recorded it.
10. Update ADR 0022 when the hosting decision changes. Keep `infra/render.yaml` as an alternate unless the user asks to remove it.
