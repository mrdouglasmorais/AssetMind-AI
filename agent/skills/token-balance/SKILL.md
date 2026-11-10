---
name: token-balance
description: Reserve and record estimated tokens separately from provider-reported usage.
---

# Token balance

## Purpose
Show what the run estimated, what the provider later reported, and what remains of `ASSETMIND_TOKEN_ALLOWANCE`.

## Inputs
Usage rows already stored, the allowance, and the price rates in configuration. Do not call a model to estimate tokens.

## Procedure
1. Estimate text at four characters per token before the call. Cost uses the configured USD rates and is not an invoice.
2. Refuse the narration when the reservation exceeds the per-call cap or the remaining allowance.
3. Write estimated input and estimated output on the ledger. Leave actual tokens null until the gateway reports a non-zero usage. A missing actual count is not a zero that hides the estimate.
4. A Groq narration is a row of kind `chat`. A news lookup is kind `news`: one provider call and no model tokens. A session embedding, when enabled, is kind `embedding`.
5. Read the public balance at `GET /api/v1/usage/balance`. Remaining tokens subtract the estimated total from the allowance.
6. Cache hits and failed calls stay visible. Do not double-count one reservation as two analyses.

## Output
Estimated tokens, remaining allowance, model calls, provider calls, and estimated USD. Actual tokens appear only after a provider report.

## Tests
Two analyses that estimated 800 tokens against an allowance of 100000 leave 99200. A news row does not increase model tokens. The remaining balance is computed from the estimate.
