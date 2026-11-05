---
name: orchestration
description: Route a request to one specialist per asset class without a model call.
---

# Orchestration

## Purpose
Receive one request and hand each asset to the specialist for its class.

## When to apply
The caller named one or more catalog assets, or a follow-up reused the previous set.

## Required inputs
Resolved symbols, asset class, and the token balance before any narrative call.

## Permitted tools
None. Do not fetch URLs and do not choose a class with a model.

## Domain rules
Equity, crypto, and real estate each have one specialist. A ticker ending in 11 is not routed until the class is explicit. Routing records zero model tokens.

## Calculation requirements
The specialist calculates. The orchestrator only groups symbols.

## Evidence requirements
Pass the metric card and the provider name. Do not pass the raw price series.

## Expected output
A route such as `equity: PETR4` and `crypto: bitcoin`, plus the running token balance.

## Failure conditions
No resolvable asset, or the estimated token balance is already above the allowance.

## Examples
`PETR4 and bitcoin` becomes two specialist assignments and one shared ledger line.

## Evaluation cases
The route contains every requested class and the ledger separates estimated tokens from actual tokens.
