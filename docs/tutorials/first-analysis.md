# First analysis

1. Run `make init`. It creates `.env` when missing and installs dependencies. The local API key becomes `local-dev-key` only if that line was empty.
2. Confirm `.env` has a non-empty `ASSETMIND_API_KEY` (or `ASSETMIND_OS_SECURITY_KEY`). `make watch` enables AgentOS and refuses to start without one of them.
3. Leave `ASSETMIND_PROVIDER_MODE=fixtures`.
4. Start `make watch`. The API listens on `http://127.0.0.1:8000` and the Agent UI listens on `http://127.0.0.1:3000`. Opening `/` redirects to the Agent UI. API docs are at `/scalar`.
5. In the UI, send a message that names a catalog asset, such as `PETR4`. The reply is the deterministic report. The same request can be sent to `POST /api/v1/analyses`.
6. Optional: list fixture movers with `GET /api/v1/assets/movers` and header `X-API-Key: local-dev-key` (or your key).

The prices in fixture mode are synthetic. Switch to `live` only when you accept the vendor limits documented in `docs/reference/data-sources.md`. A live OCI deploy is a later step and is not required to read this tutorial.

## Local Compose

There is no Compose file at the repository root. Use:

```bash
make up
```

That runs `infra/docker/docker-compose.yml` (API + Postgres + UI). Build contexts are relative to the repo root (`--project-directory .`). Do not run bare `docker compose up` from the root unless you pass `-f infra/docker/docker-compose.yml --project-directory .`.

## Common failures

| Symptom | Fix |
| --- | --- |
| `ASSETMIND_API_KEY or ASSETMIND_OS_SECURITY_KEY is required when AgentOS is enabled` | Set `ASSETMIND_API_KEY=local-dev-key` in `.env`, or re-run `make init` on an empty key line |
| `no configuration file provided: not found` after `docker compose up` | Use `make up` (file is under `infra/docker/`) |
| `401` on `/api/v1/*` | Send `X-API-Key` matching `.env` |
