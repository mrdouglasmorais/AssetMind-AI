# HTTP API

## Browser entry points

| Path | Role |
| --- | --- |
| `/` | Redirects to the Agno Agent UI when `ASSETMIND_AGENT_UI_URL` is set; otherwise JSON with `health` and `docs` |
| `/scalar` | Interactive API reference (Scalar). Public even with AgentOS on. Swagger UI and ReDoc are not mounted |
| `/docs`, `/redoc` | Redirect `307` to `/scalar` |
| `/openapi.json` | Product OpenAPI only (`/health`, `/ready`, `/api/v1/*`). AgentOS control routes stay mounted for the Agent UI but are omitted from this schema |

Chat stays on the Agent UI. Product HTTP routes stay under `/api/v1` and require `X-API-Key` unless noted.

## Auth and local keys

`make watch` sets `ASSETMIND_AGENTOS_ENABLED=true`. The process needs a non-empty `ASSETMIND_API_KEY` or `ASSETMIND_OS_SECURITY_KEY`. `make init` fills an empty `ASSETMIND_API_KEY` with `local-dev-key`.

The Agent UI bearer token is `ASSETMIND_OS_SECURITY_KEY` when set, otherwise `ASSETMIND_API_KEY`. Product routes always use `X-API-Key`.

## Routes

| Method | Path | Auth |
| --- | --- | --- |
| `GET` | `/health` | Public |
| `GET` | `/ready` | Public |
| `GET` | `/api/v1/assets/search?q=` | API key |
| `GET` | `/api/v1/assets/movers` | API key |
| `GET` | `/api/v1/assets/{symbol}/news` | API key |
| `POST` | `/api/v1/analyses` | API key |
| `GET` | `/api/v1/analyses/{id}` | API key |
| `GET` | `/api/v1/analyses/{id}/events` | API key (SSE) |
| `GET` | `/api/v1/analyses/{id}/report` | API key |
| `GET` | `/api/v1/usage/balance` | API key |

Full query and status rules: [specs/api-contracts.md](../specs/api-contracts.md).

## Movers

List assets rising and falling. Quantity, volume filter, type, and pagination are query parameters.

```bash
curl -s "http://127.0.0.1:8000/api/v1/assets/movers?direction=both&type=all&limit=10&page=1&min_volume=0&sort_by=change" \
  -H "X-API-Key: $ASSETMIND_API_KEY"
```

| Query | Values | Default |
| --- | --- | --- |
| `direction` | `up` \| `down` \| `both` | `both` |
| `type` | `equity` \| `real_estate` \| `crypto` \| `all` | `all` |
| `limit` | 1–50 | `10` |
| `page` | ≥1 | `1` |
| `min_volume` | ≥0 | `0` |
| `sort_by` | `change` \| `volume` | `change` |

Response shape:

```json
{
  "rising": [
    {
      "symbol": "PETR4",
      "name": "Petrobras PN",
      "asset_class": "equity",
      "market": "b3",
      "price": 36.65,
      "change_percent": 2.4,
      "volume": 27000000,
      "currency": "BRL"
    }
  ],
  "falling": [],
  "pagination": {
    "page": 1,
    "limit": 10,
    "has_next_rising": false,
    "has_next_falling": false
  },
  "retrieved_at": "2026-11-11T15:00:00+00:00",
  "limitation": "…"
}
```

Fixture mode returns synthetic samples. Live mode reads brapi `quote/list` (`change` / `volume`) and CoinGecko `coins/markets` (24h change). Values are provider quotes, not recommendations. See [reference/data-sources.md](../reference/data-sources.md).

## Create an analysis

```json
{
  "assets": [
    {"symbol": "PETR4"},
    {"symbol": "bitcoin", "asset_class": "crypto"},
    {"symbol": "HGLG11", "asset_class": "real_estate"}
  ],
  "scenarios": {"bear": -0.2, "base": 0, "bull": 0.15}
}
```

The response status is `completed`, `partial`, or `failed`. `partial` means at least one explicit limit or data gap. The report repeats the deterministic metrics in Brazilian Portuguese and includes the disclaimer.

Events are stored rows replayed as `text/event-stream`. They are not a live token stream from a model.
