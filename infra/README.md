# Infrastructure

| Path | Role |
| --- | --- |
| [docker/](docker/) | Multi-role Dockerfile (`api` / `worker` / `migrate`) and local Compose |
| [oci/](oci/) | Terraform + production Compose (Caddy, API, worker, Postgres) |
| [render.yaml](render.yaml) | Alternate Render blueprint |

Production entrypoint: [`oci/docker-compose.prod.yml`](oci/docker-compose.prod.yml). Application code stays in `src/`. Do not add Kubernetes or a service per agent.
