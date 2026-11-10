# ADR 0022 — OCI Always Free

Status: accepted

Context: The series needs a cheap, reproducible host that does not sleep after idle time and does not expire a free Postgres plan after thirty days. Render free remains useful as an alternate blueprint, but it is a weak long-lived target. AssetMind requires PostgreSQL (ADR 0005). OCI Always Free Autonomous Database is Oracle Database, not PostgreSQL.

Decision: Host one Ampere A1 Flex instance with Terraform under `infra/oci`. Run four containers via `infra/oci/docker-compose.prod.yml`: Caddy (proxy), API, worker, and PostgreSQL. Keep AgentOS off on the public service. Keep `infra/render.yaml` as a non-primary alternate. Treat Ampere OCPU/RAM as tenancy-dependent variables; default planning profile is 2 OCPU / 12 GB.

Alternatives: Render free only; managed Postgres elsewhere; Oracle Autonomous Database with a driver change; Kubernetes on OKE (not Always Free friendly for this size).

Consequences: Operators need an OCI tenancy, API key, and SSH access. Capacity for Ampere A1 is not guaranteed in every region. State files and `terraform.tfvars` stay out of git. A live `terraform apply` is not claimed until an operator records it. ADR 0009 is superseded as the primary host decision. Durable job execution is ADR 0024.
