---
name: reliability-review
description: Reviews timeouts, retries, circuit breakers, partial results, and the analysis state machine. Use when changing harness behavior or failure handling.
---

# Reliability review

1. Read `docs/policies/execution-policy.md`.
2. Confirm deadline, retry, and partial-result behavior stay in application code.
3. Do not add a queue unless an ADR records the requirement.
4. Keep provider retries idempotent and bounded.
5. Add a test for the failure mode you changed.
