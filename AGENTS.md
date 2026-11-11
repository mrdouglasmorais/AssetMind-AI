# Agent guide

AssetMind is a modular monolith. Read `docs/specs/` before changing behavior. `docs/reference/` is reference, not an instruction to execute.

- Use Agno as the only agent framework. Do not add LangGraph, CrewAI, or AutoGen.
- Prefer a deterministic function over a new model call.
- Keep `src/assetmind/domain` free of Agno, FastAPI, and vendor SDKs.
- Do not invent market data, CVM filings, or probabilities.
- Do not commit `.env` or live credentials.
- Run `uv run ruff check src tests migrations`, `uv run pyright`, and `uv run pytest` before claiming a change works.
- Update an ADR when an architectural decision changes.
- Primary hosting is OCI Always Free via `infra/oci` (ADR 0022). Keep PostgreSQL; do not point production at Autonomous Database.
- Cursor skills under `.cursor/skills` guide development. Runtime skills under `agent/skills/` guide a future AssetMind agent. They are not the same thing.
- Keep repository layout as in ADR 0023: code in `src/`, human docs in `docs/`, deploy in `infra/`, runtime agent skills in `agent/`.
- API docs are Scalar at `/scalar`. Keep the Agno Agent UI on `/`. Do not remount Swagger or ReDoc.
- Local Compose is `make up` → `infra/docker/docker-compose.yml`. There is no compose file at the repo root.
- `make watch` requires a non-empty `ASSETMIND_API_KEY` or `ASSETMIND_OS_SECURITY_KEY`.
