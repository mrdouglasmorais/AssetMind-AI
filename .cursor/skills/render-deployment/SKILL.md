---
name: render-deployment
description: Updates Docker or Render configuration for AssetMind. Use when editing infra/docker, infra/render.yaml, health checks, or hosting docs.
---

# Render deployment

1. Keep one web service. Do not add a service per agent.
2. Bind the process to `0.0.0.0` and `$PORT`.
3. Point `ASSETMIND_DATABASE_URL` at Render Postgres with `fromDatabase`.
4. Leave AgentOS disabled on the public service.
5. Mark secrets with `sync: false`.
6. Edit `infra/render.yaml` and `infra/docker/Dockerfile`. Paths are relative to the repo root.
7. Do not claim the deploy succeeded unless a real deploy was checked.
8. Remember that the free web plan spins down and free Postgres expires.
9. Prefer OCI Always Free (ADR 0022) unless the user asks for Render.
