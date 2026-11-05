# ADR 0017 — Chat ledger and deadline cancellation

Status: accepted

Context: The usage row was written only when the deterministic workflow finished. A Groq narration in the Agent UI spent tokens outside that ledger and outside the allowance check. The 25 second deadline was read between workflow steps, so a provider call already in flight could run past it.

Decision: Before the Groq agent calls its model, a pre-hook reserves the narration on the per-call token cap and on the remaining allowance. The run is refused when either check fails. The post-hook writes a separate usage row for that narration. Estimated tokens stay the reservation. Actual tokens are filled only from the run metrics. A news lookup writes a provider-call row and does not spend model tokens. The analysis task and each provider fetch are wrapped in a timeout of the time still left. `asyncio` cancels the in-flight operation when that timeout fires. Usable metrics already collected finish as `partial`.

Alternatives: Leave narration uncounted, or block the event loop until every HTTP retry returns.

Consequences: `GET /api/v1/usage/balance` includes chat narrations and news lookups. A slow provider cannot hold the request until its own retries finish. Tests cancel a sleeping fetch and do not call Groq.
