---
name: scenario-analysis
description: Turn a fresh reference price into bear, base, and bull prices with an explicit shock label.
---

# Scenario analysis

## Purpose
Apply `price * (1 + shock)` to a fresh reference price. The result is a conditional illustration, not a forecast.

## Inputs
A fresh reference price and either the default shocks or caller-supplied shocks. No series, no seed, and no model is required for this formula.

## Procedure
1. Stop when the reference price is missing, stale, or conflicting. Prefer omission to a precise invented path.
2. Default shocks are bear −15%, base 0%, and bull +15%. The label is `illustrative_assumption`. Caller shocks are `user_assumption` and must sit between −95% and +300%.
3. The disclosure string travels with each scenario. The narrative calls the figure an assumption. It does not call it a projection, a target, or a probability.
4. Do not assign 20/60/20 or any other probability. A calibrated probability is not emitted.
5. Monte Carlo, GARCH, DCF, factor betas, and walk-forward backtests are not this skill. They stay out of the report until the engine returns a metric that names that method, its window, and its inputs.
6. A macro event, including a Selic change, is not converted into a price shock by the model. The only shock is the one in the inputs.
7. Percentiles from the historical sample stay in the equity or crypto card. They are not reused here as the chance of the bear or bull case.
8. A Buffett or Barsi lens does not change the shock. Their long holding horizon is not this −15/0/+15 illustration. Say the scenario is a price path under a stated assumption, not the outcome of that horizon.

## Output
Three labeled prices, or an explicit omission. No `probability` field. The report disclaimer states the same limit.

## Tests
A price of 10 and a shock of −0.2 produce 8. A missing price produces no scenario. The words "projecao" and "probabilidade" do not describe the shock.
