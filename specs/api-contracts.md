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

Invalid symbols and ambiguous FII tickers return 422. A missing key returns 401. The rate limit returns 429.
