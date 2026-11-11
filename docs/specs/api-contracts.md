# API contracts

| Method | Path | Auth |
| --- | --- | --- |
| GET | `/health` | Public |
| GET | `/ready` | Public |
| GET | `/api/v1/assets/search?q=` | API key. Live mode pages the brapi quote list and the CoinGecko coin list, then returns a page in `results` and `by_type`. Fixture mode uses the local sample. |
| GET | `/api/v1/assets/movers` | API key. Query: `direction` (`up`\|`down`\|`both`), `type` (`equity`\|`real_estate`\|`crypto`\|`all`), `limit` (1–50), `page` (≥1), `min_volume` (≥0), `sort_by` (`change`\|`volume`). Returns `rising`, `falling`, `pagination`, `retrieved_at`, and `limitation`. Fixture mode uses synthetic samples. Live mode reads brapi quote list change/volume and CoinGecko 24h markets. |
| POST | `/api/v1/analyses` | API key |
| GET | `/api/v1/analyses/{id}` | API key |
| GET | `/api/v1/analyses/{id}/events` | API key |
| GET | `/api/v1/analyses/{id}/report` | API key |

Browser docs: Scalar at `/scalar`. `/` redirects to the Agent UI when configured. `/docs` and `/redoc` redirect to `/scalar`. See [api/http.md](../api/http.md).

`GET /api/v1/assets/movers` returns `rising` and/or `falling` lists of `{symbol, name, asset_class, market, price, change_percent, volume, currency}`, plus `pagination`, `retrieved_at`, and `limitation`. B3 change is the brapi quote-list field; crypto change is CoinGecko 24h. Rows are not recommendations.

`POST` accepts up to five assets, an optional scenario block, and an optional `as_of`. Responses include `analysis_id`, `correlation_id`, and `status`.

When `ASSETMIND_JOB_QUEUE_ENABLED=true`, `POST /api/v1/analyses` enqueues work and returns `status=queued` with `report=null`. Poll `GET /api/v1/analyses/{id}` and `GET .../report` until a terminal status. When the flag is false (local default), the request runs inline and returns `completed` / `partial` / `failed` with a report when available.

Invalid symbols and ambiguous FII tickers return 422. A missing key returns 401. The rate limit returns 429. Invalid movers query values (`limit` out of range, unknown `type`) return 422.
