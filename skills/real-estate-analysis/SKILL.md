---
name: real-estate-analysis
description: Analyze one Brazilian FII quota without confusing it with a CRI or a direct property.
---

# Real estate analysis

## Purpose
Explain a FII quota using price evidence and, when present, labeled fund facts.

## When to apply
The caller set `asset_class` to `real_estate`.

## Required inputs
Ticker, price evidence, fund classification, and any P/VP or distribution evidence.

## Permitted tools
None.

## Domain rules
Do not apply vacancy to a paper fund. Do not treat a CRI or a direct property as a FII. Unknown classification means vacancy is not applied.

## Calculation requirements
Dividend yield requires a trailing distribution, a stated period, and a fresh reference price.

## Evidence requirements
Fixture facts must stay labeled as fixtures. Live CVM informe parsing is not available in this MVP.

## Expected output
Brazilian Portuguese prose that states classification limits and risks.

## Failure conditions
Ambiguous ticker without a class, conflicting prices, or no usable price.

## Examples
A brick fixture may report vacancy. A paper fixture must not.

## Evaluation cases
A paper fund with a vacancy field produces no vacancy metric.
