# Data sources

brapi documents a free plan of about 15,000 requests per month, one ticker per request, one concurrent request, and about three months of history. PETR4, VALE3, MGLU3, and ITUB4 can be queried without a token. Quotes on that plan are delayed. `GET /api/quote/list` pages stocks and funds; a fund is a FII only when `subType` is `fii`. The same list endpoint supplies movers via `sortBy=change|volume`, `sortOrder`, `page`, and `limit`. This is not permission to resell the data.

CoinGecko's public API is rate limited. A demo key is sent only when `COINGECKO_API_KEY` is set. `GET /coins/list` is the crypto directory. The id is the symbol the quote call uses. `GET /coins/markets` ordered by `price_change_percentage_24h_desc|asc` (or volume) supplies crypto movers.

Banco Central SGS series 432 is the Selic target. A live call on 4 Nov 2026 returned HTTP 200. The value is macro context.

CVM monthly FII files are not parsed. Fixture mode uses labeled samples for HGLG11 and MXRF11. Live mode returns an unknown classification.
