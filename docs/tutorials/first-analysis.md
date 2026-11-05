# First analysis

1. Run `make init`. It creates `.env` when missing and installs dependencies. The local API key becomes `local-dev-key` only if that line was empty.
2. Leave `ASSETMIND_PROVIDER_MODE=fixtures`.
3. Start `make watch`. The API listens on `http://127.0.0.1:8000` and the Agent UI listens on `http://127.0.0.1:3000`. Opening `/docs` redirects to that UI.
4. In the UI, send a message that names a catalog asset, such as `PETR4`. The reply is the deterministic report. The same request can be sent to `POST /api/v1/analyses`.

The prices in fixture mode are synthetic. Switch to `live` only when you accept the vendor limits documented in `context/data-sources.md`. A live deploy on Render is a later step and is not required to read this tutorial.
