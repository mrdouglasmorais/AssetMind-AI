# ADR 0021 — Provider listings

Status: accepted

Context: The chat and the search route only knew eight sample assets. A word such as "web" is not a ticker. News cards failed when the model rewrote the headline JSON and the output budget cut a Google News URL in half.

Decision: Live mode reads `brapi /api/quote/list` for stocks and for funds whose subtype is `fii`, and `CoinGecko /coins/list` for crypto ids. The directory is cached in memory for six hours. Search returns a page of that directory. The chat page shows at most twelve names and still accepts any ticker from the directory. Fixture mode keeps the sample catalog. Headline cards render from the `get_asset_news` tool result. A truncated JSON blob is not shown.

Alternatives: Keep the eight-name sample, or ask the model to copy every listing and every headline URL.

Consequences: The first live catalog question spends several brapi pages and one CoinGecko call. Later questions reuse the cache. Tests parse fixture payloads and do not call the providers.
