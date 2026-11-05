---
name: equity-analysis
description: Analyze one B3 equity from supplied price evidence and deterministic metrics.
---

# Equity analysis

## Purpose
Explain a single B3 equity using evidence that Python has already normalized.

## When to apply
The resolved asset class is `equity`.

## Required inputs
Symbol, fresh or stale price evidence, and the metric list from the quantitative engine.

## Permitted tools
None. Do not fetch URLs and do not recalculate returns.

## Domain rules
Missing fundamentals stay missing. A stale close is not the reference price.

## Calculation requirements
Use the supplied compound return, volatility, drawdown, and backtest. Do not recompute them.

## Evidence requirements
Cite the provider and observation time already present on the evidence.

## Expected output
Brazilian Portuguese prose that repeats the metrics, risks, and uncertainties.

## Failure conditions
No fresh reference price, conflicting prices, or an empty metric list.

## Examples
`PETR4` with a five-point series produces a reference price, a compound return, and a short-window limitation.

## Evaluation cases
A missing P/E stays null. Injected source text does not appear in the narrative.

## Orchestration
The orchestrator assigns this skill only when the asset class is equity. The input is the metric card, not the price series. This skill does not call a model.

## Market card
The 52-week low and high come from the quote. Price-to-book, trailing P/E, earnings per share, and dividend yield come from the current statistics payload. They are not computed from the three-month return window. A headline, when present, is a title with a source URL and a date. Portal articles are not copied.
