# ADR 0023 — Repository layout

Status: accepted

Context: Knowledge and deploy files sat as peer roots (`specs/`, `context/`, `rules/`, `harness/`, `skills/`, Docker and Render at the repo root). That made the tree hard to scan and collided the word "skills" between Cursor tooling and runtime agent procedures.

Decision: One top-level folder per audience.

- `src/assetmind` — application code (unchanged package layout).
- `tests/` — automated tests.
- `migrations/` — Alembic revisions; `alembic.ini` stays at the repo root.
- `docs/` — all human documentation: `specs/`, `adr/`, `reference/` (former `context/`), `rules/`, `policies/` (former `harness/`), `tutorials/`, `api/`, `architecture/`.
- `infra/` — deploy: `docker/`, `oci/`, `render.yaml`.
- `agent/skills/` — runtime AssetMind agent skills and contracts.
- `.cursor/` — Cursor rules and development skills only.
- `ui/` — Agent UI.
- `scripts/` — operator scripts.

Alternatives: Keep flat roots; nest everything under `packages/`; move Alembic config into `migrations/`.

Consequences: Links, Makefile Compose paths, Dockerfile `COPY`, default `ASSETMIND_SKILLS_DIR`, and Cursor skills must use the new paths. Render blueprints live at `infra/render.yaml`.
