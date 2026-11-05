# ADR 0015 — Equity card and headlines

Status: accepted

Context: A complete equity note needs the 52-week quote range and current multiples, plus market headlines. The return window stays about three months. Copying portal prose would mix unverified text into the report.

Decision: The brapi quote supplies `fiftyTwoWeekLow` and `fiftyTwoWeekHigh`. `/api/v2/stocks/statistics?mode=current` supplies price-to-book, trailing P/E, earnings per share, and dividend yield. A null field stays missing. Equity fetches reserve one extra provider call for that endpoint. A headline may be stored only as title, source URL, and publication time, at most three. No news host is called in this slice, so the report says no news source is registered.

Alternatives: Scrape Investidor10, Status Invest, or Investing pages, or ask the model to summarize them.

Consequences: NATU3 and any other B3 ticker can be requested. The 52-week range is not the compound-return window. Tests use documented payload shapes and do not call brapi.
