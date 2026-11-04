---
name: scenario-analysis
description: Apply bear, base, and bull price shocks as labeled assumptions.
---

# Scenario analysis

## Purpose
Turn a fresh reference price and three shocks into illustrative prices.

## When to apply
A fresh reference price exists.

## Required inputs
Reference price and either the MVP default shocks or caller-supplied shocks.

## Permitted tools
None. The shock formula is `price * (1 + shock)`.

## Domain rules
Defaults of -15%, 0%, and +15% are illustrative assumptions. Caller shocks are user assumptions. Neither is a calibrated forecast.

## Calculation requirements
Skip scenarios when the reference price is missing or stale.

## Evidence requirements
The disclosure string must travel with the scenario.

## Expected output
Three labeled scenario prices, or an explicit omission.

## Failure conditions
Shock outside the accepted range, or no fresh price.

## Examples
A price of 10 and a shock of -0.2 produce 8.

## Evaluation cases
The narrative calls the figure an assumption, not a probability.
