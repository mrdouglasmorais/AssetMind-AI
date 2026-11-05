---
name: orchestration
description: Route each asset to one specialist in code, with budgets, a deadline, and zero model calls.
---

# Orchestration

## Purpose
Turn one request into a typed plan. Group symbols by class, run independent fetches together, and stop when the budget or the deadline is crossed.

## Inputs
Symbols already resolved, `asset_class` when the ticker is ambiguous, `as_of`, and the token balance before any narrative call. A follow-up may reuse the previous symbol set. The HTTP API accepts at most five assets.

## Procedure
1. Validate the symbol against the catalog or the B3 pattern. Do not guess a class.
2. A ticker ending in 11 waits until the caller says equity or real estate.
3. Map the class in code: `equity`, `crypto`, or `real_estate`. One specialist per class. No second model chooses the route.
4. Fetch independent classes in parallel. Pass the metric card and the provider name. Do not pass the raw price series.
5. Run evidence review before the report is shown. Run scenarios only when a fresh reference price exists.
6. News is optional. A missing feed still allows the quantitative report, with the news lookup marked unavailable.
7. If the deadline is crossed, cancel the provider call in flight. Usable metrics finish as `partial`. An empty result finishes as `failed`.
8. Record the route, the omissions, and the usage row. Routing itself records zero model tokens.

## Decision rules
Unknown symbol, missing class on `*11`, or an allowance already spent stops the run with a structured error. A stale or conflicting close is not replaced by a quieter number. Do not ask a model to replan after the budget fails.

## Output
Lines such as `equity: PETR4` and `crypto: bitcoin`, a status `completed`, `partial`, or `failed`, and the shared ledger. The shape is `contracts/report.schema.json`.

## Tests
`PETR4` and `bitcoin` become two assignments and one ledger line. `ABCD11` without a class is not routed. A repeated request with the same snapshot does not invent a new route.
