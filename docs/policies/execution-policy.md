# Execution policy

Runs move `created → validating → planning → fetching → analyzing → verifying → completed`.

`failed`, `cancelled`, and `partial` are terminal. A deadline or provider error with any usable metrics finishes as `partial`. A run with no metrics finishes as `failed`.

Retries apply only to idempotent GET requests, at most two extra attempts, with exponential backoff and jitter. HTTP 4xx other than 429 is not retried. The circuit opens after three consecutive provider failures and resets after 30 seconds.

The workflow runs inside the HTTP request. There is no separate queue in this MVP. When the deadline passes, the workflow task and the provider call in progress are cancelled. A cancelled run with usable metrics finishes as `partial`.
