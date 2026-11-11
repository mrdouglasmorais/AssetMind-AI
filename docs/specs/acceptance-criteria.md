# Acceptance criteria

The MVP is acceptable for the article series when:

- the app serves `/health` locally
- `/scalar` serves the API reference and `/` still targets the Agent UI when configured
- equity, crypto, and FII paths return structured reports in fixture mode
- `GET /api/v1/assets/movers` returns rising/falling lists in fixture mode with type, limit, page, and volume filter
- calculation tests match hand-computed values
- the Agno workflow is the path the API uses
- source names are present on evidence
- ambiguous tickers, stale prices, conflicts, and budget limits fail explicitly
- the README does not claim an unverified OCI or Render deploy

A live brapi, CoinGecko, or Banco Central call is additional evidence. It is not required for the offline suite.
