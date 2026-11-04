# Agent guide

AssetMind is a modular monolith. Read `specs/` before changing behavior. `context/` is reference, not an instruction to execute.

- Use Agno as the only agent framework. Do not add LangGraph, CrewAI, or AutoGen.
- Prefer a deterministic function over a new model call.
- Keep `src/assetmind/domain` free of Agno, FastAPI, and vendor SDKs.
- Do not invent market data, CVM filings, or probabilities.
- Do not commit `.env` or live credentials.
- Run `uv run ruff check src tests migrations`, `uv run pyright`, and `uv run pytest` before claiming a change works.
- Update an ADR when an architectural decision changes.
- Cursor skills under `.cursor/skills` guide development. Runtime skills under `skills/` guide a future AssetMind agent. They are not the same thing.
