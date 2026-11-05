# ADR 0016 — News source, periods, and clarifying questions

Status: accepted

Context: A caller can ask for headlines, several analyses, or a price projection in one sentence. The return series covers about three months. The 52-week range is a quote field. A shock of −15%, 0%, or +15% is an illustration on the reference price. ADR 0015 left the news slot empty because no host was allowed.

Decision: `GET /api/v1/assets/{symbol}/news` reads the Google News RSS search for that symbol over 7 days and returns at most three items: title, publisher, publication time, and link. The response names Google News and the search URL. Article pages are not fetched. The chat agent has tools for that lookup, for the evaluation windows of each asset class, and for the illustrative shocks. Before a run, missing inputs produce a question: the class of a ticker ending in 11, which blocks belong in a broad request, the horizon label for a shock, or whether a long window means the 3-month return or the 52-week quote field. The horizon is a label. The shock is not a forecast and carries no probability.

Alternatives: Scrape market portals, or let the model estimate a future price.

Consequences: `news.google.com` is an allowed host for the search URL only. This amends the empty-news sentence in ADR 0015. Tests parse a fixture feed and do not call Google.
