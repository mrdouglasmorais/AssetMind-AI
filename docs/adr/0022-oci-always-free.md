# ADR 0022 — OCI Always Free

Status: accepted

Context: The series needs a cheap, reproducible host that does not sleep after idle time and does not expire a free Postgres plan after thirty days. Render free remains useful as an alternate blueprint, but it is a weak long-lived target. AssetMind requires PostgreSQL (ADR 0005). OCI Always Free Autonomous Database is Oracle Database, not PostgreSQL. Ampere A1 Flex capacity in the home region is frequently unavailable for long stretches.

Decision: Host one Always Free compute instance with Terraform networking under `infra/oci` and GitHub Actions owning the VM (`enable_compute = false`). Prefer **VM.Standard.E2.1.Micro** (x86) when Ampere is unavailable; fall back to **VM.Standard.A1.Flex** when capacity appears. Run containers via `infra/oci/docker-compose.prod.yml`. On Micro, apply `docker-compose.micro.yml`: Caddy + API + PostgreSQL, no worker, `ASSETMIND_JOB_QUEUE_ENABLED=false`, low memory limits, and a 2 GB swapfile from cloud-init. On A1, run the full stack including the worker. Keep AgentOS off on the public service. Keep `infra/render.yaml` as a non-primary alternate. Treat Ampere OCPU/RAM as tenancy-dependent variables; default A1 planning profile is 2 OCPU / 12 GB (pipeline often uses 1 / 6).

Alternatives: Render free only; managed Postgres elsewhere; Oracle Autonomous Database with a driver change; Kubernetes on OKE (not Always Free friendly for this size); paid OCI shapes.

Consequences: Operators need an OCI tenancy, API key, and SSH access. Micro is ~1 GB RAM and must build amd64 images on the host. Ampere capacity is not guaranteed. Soft-skip in CI happens only after Micro and A1 both fail with Out of host capacity. State files and `terraform.tfvars` stay out of git. A live `terraform apply` for compute is not claimed until an operator records it. ADR 0009 is superseded as the primary host decision. Durable job execution is ADR 0024 (enabled on A1; disabled on Micro).
