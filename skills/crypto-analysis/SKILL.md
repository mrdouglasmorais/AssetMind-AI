---
name: crypto-analysis
description: Analyze one crypto asset from supplied market evidence and deterministic metrics.
---

# Crypto analysis

## Purpose
Explain price, volume, and market cap for one CoinGecko asset.

## When to apply
The resolved asset class is `crypto`.

## Required inputs
Coin id, price series, and any market-cap or volume evidence.

## Permitted tools
None.

## Domain rules
Volume is not proof of executable liquidity. Annualized volatility uses a 365-period convention and is not a forecast.

## Calculation requirements
Use the supplied historical distribution percentiles as history, not as probabilities.

## Evidence requirements
Keep the provider timestamp. Do not fill a missing market cap with zero.

## Expected output
Brazilian Portuguese prose limited to the supplied metrics and risks.

## Failure conditions
Unknown coin id, stale reference price, or provider failure.

## Examples
`bitcoin` with a fresh close and a market-cap observation.

## Evaluation cases
A null market cap is disclosed as missing.
