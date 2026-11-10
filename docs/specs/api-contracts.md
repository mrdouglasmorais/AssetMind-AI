# API contracts

| Method | Path | Auth |
| --- | --- | --- |
| GET | `/health` | Public |
| GET | `/ready` | Public |
| GET | `/api/v1/assets/search?q=` | API key. Live mode pages the brapi quote list and the CoinGecko coin list, then returns a page in `results` and `by_type`. Fixture mode uses the local sample. |
| POST | `/api/v1/analyses` | API key |
| GET | `/api/v1/analyses/{id}` | API key |
| GET | `/api/v1/analyses/{id}/events` | API key |
| GET | `/api/v1/analyses/{id}/report` | API key |

`POST` accepts up to five assets, an optional scenario block, and an optional `as_of`. Responses include `analysis_id`, `correlation_id`, and `status`.

When `ASSETMIND_JOB_QUEUE_ENABLED=true`, `POST /api/v1/analyses` enqueues work and returns `status=queued` with `report=null`. Poll `GET /api/v1/analyses/{id}` and `GET .../report` until a terminal status. When the flag is false (local default), the request runs inline and returns `completed` / `partial` / `failed` with a report when available.

Invalid symbols and ambiguous FII tickers return 422. A missing key returns 401. The rate limit returns 429.
