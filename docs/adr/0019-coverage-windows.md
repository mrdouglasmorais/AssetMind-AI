# ADR 0019 — Coverage score and horizon returns

Status: accepted

Context: A short daily series cannot support a 6-month or 12-month return, and a filled card is not a reason to buy. The free brapi history request stays at about three months. CoinGecko stays at 90 daily observations. A longer range is used only when that provider returns it.

Decision: `return_3m`, `return_6m`, and `return_12m` are realized close-to-close changes. Each stays empty unless the series spans the calendar horizon within a small tolerance. `coverage.score` is the count of requested card fields that arrived with a number, divided by the count requested. Missing fields are listed as refused. The score is not a buy or sell grade.

Alternatives: Request one year of history on every call, or map the coverage ratio onto a purchase recommendation.

Consequences: With the current provider windows, 6-month and 12-month returns stay empty. A longer series supplied by a later adapter fills them without a new formula.
