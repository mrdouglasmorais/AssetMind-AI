---
name: reliability-review
description: Reviews timeouts, retries, circuit breakers, partial results, and the analysis state machine. Use when changing harness behavior or failure handling.
---

# Reliability review

1. Read `harness/execution-policy.md`.
2. Confirm retries are bounded and only used for idempotent GET calls.
3. Confirm a budget or deadline ends in `partial` or `failed`, not a silent success.
4. Add a test for the failure you touched: timeout, 429, conflict, stale price, or budget.
5. Report the commands you ran.
