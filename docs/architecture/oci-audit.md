# OCI Always Free — Phase 1 audit

Date: 2026-11-10. Scope: Dockerfile, Compose, Render blueprint, Python deps, execution model. No OCI resources were provisioned.

## Current state

| Area | Finding |
| --- | --- |
| Host target | ADR 0022 points at OCI Always Free; `infra/render.yaml` is alternate |
| Dockerfile | Single-stage `uv` image; runs as root; migrates on every container start; exposes API only |
| Local Compose | `infra/docker/docker-compose.yml` — api + postgres + ui; no proxy, no worker |
| OCI Compose (prior) | `infra/docker/docker-compose.oci.yml` — api + postgres; published `:8000`; no TLS |
| Terraform | `infra/oci` VCN + A1 Flex + security list (SSH + 80/443/8000) |
| Execution | Analysis runs inside the HTTP request with a 25s deadline (ADR 0017) |
| Persistence | `analyses`, `analysis_events`, `usage_records`, `evidence_records` — no job lease table |
| Logging | JSON via `observability/logging.py`; correlation and analysis ids partially present |
| Redis | Not used (correct for Always Free base) |

## ARM64 compatibility

| Dependency | linux/arm64 |
| --- | --- |
| `python:3.13-slim-bookworm` / `uv:python3.13-bookworm-slim` | Official multiarch |
| `numpy`, `pandas` | PyPI manylinux aarch64 wheels |
| `psycopg[binary]` 3.3.x | `manylinux_2_27_aarch64` / `manylinux_2_28_aarch64` for cp313 |
| `agno`, FastAPI, uvicorn, SQLAlchemy | Pure Python / multiarch |
| `postgres:16` | Official multiarch |
| `caddy:2` | Official multiarch |

No x86 emulation is required for production on Ampere A1. Prefer native `linux/arm64` image builds (GitHub `ubuntu-24.04-arm` or `buildx` on ARM runners). QEMU is acceptable only for CI convenience, not as a production runtime dependency.

## Risks

1. **In-request workflow** — a restart mid-analysis loses the run; HTTP timeout and analysis deadline are coupled. Production target needs a durable worker (Phase 3 / ADR 0024).
2. **Migrate-on-start** — unsafe once API and worker share an image and can race Alembic.
3. **Published API port** — bypasses TLS and security headers when Caddy is intended.
4. **Postgres on the same boot volume** — Always Free disk loss is a disaster; Object Storage off-box backup is required later.
5. **Ampere capacity** — A1 Flex is not guaranteed in every region; OCPU/RAM must be read from the tenancy, not assumed as 4/24.
6. **Memory** — Agno + NumPy + pandas + Postgres on one 12 GB host needs conservative limits and a single worker by default.
7. **Secrets** — still operator-managed `.env`; no Vault in Phase 2.

## Decisions for Phase 2

- One app image, three commands: `api`, `worker`, `migrate`.
- Production Compose under `infra/oci/docker-compose.prod.yml` with Caddy, API, worker, Postgres.
- Postgres and worker stay on the internal Docker network only.
- Host publishes 80/443 (and SSH elsewhere); not 8000 or 5432.
- Worker process ships as an idle-capable entrypoint until the durable queue lands in Phase 3.
- Economic profile defaults: 2 OCPU / 12 GB planning envelope with headroom for the OS.

## Out of scope this phase

Durable `FOR UPDATE SKIP LOCKED` queue, OpenTelemetry exporters, GitHub deploy workflow, Terraform apply, Object Storage backup automation.
