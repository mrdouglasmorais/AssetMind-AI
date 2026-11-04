# First analysis

1. Install dependencies with `uv sync --all-groups`.
2. Copy `.env.example` to `.env` and set `ASSETMIND_API_KEY`.
3. Leave `ASSETMIND_PROVIDER_MODE=fixtures`.
4. Start `uv run uvicorn assetmind.main:app --host 0.0.0.0 --port 8000`.
5. Call `POST /api/v1/analyses` with the example in the README.

The prices in fixture mode are synthetic. Switch to `live` only when you accept the vendor limits documented in `context/data-sources.md`. A live deploy on Render is a later step and is not required to read this tutorial.
