---
name: token-balance
description: Read the running token ledger before adding a model call.
---

# Token balance

## Purpose
Show how many tokens an analysis has estimated and how many remain in the allowance.

## When to apply
Before a narrative model call, and whenever the caller asks about consumption.

## Required inputs
The usage rows already stored for this database and `ASSETMIND_TOKEN_ALLOWANCE`.

## Permitted tools
None. Do not estimate tokens by calling a model.

## Domain rules
Estimated usage and actual provider usage stay in separate fields. Remaining tokens subtract the estimated total from the allowance. A missing actual count stays zero until the provider reports it. A Groq narration is its own ledger row. The call is refused when the reservation exceeds the per-call cap or the remaining allowance. A news lookup counts as one provider call and does not spend model tokens.

## Calculation requirements
Estimate text at four characters per token. Cost uses the configured USD rates and is not an invoice.

## Evidence requirements
Cite the analysis count and the call counts. Do not invent a provider invoice.

## Expected output
Estimated tokens, remaining allowance, model calls, provider calls, and estimated USD.

## Failure conditions
The next estimated call would pass the per-analysis token cap or the allowance.

## Examples
Two analyses that estimated 800 tokens against an allowance of 100000 leave 99200.

## Evaluation cases
Actual tokens are absent until recorded. The remaining balance never uses the actual field to hide estimated spend.
