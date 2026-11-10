---
name: equity-analysis
description: Explain one B3 equity from the metric card, the 52-week range, and current statistics.
---

# Equity analysis

## Purpose
Explain a single B3 equity. Python already normalized the evidence. This skill repeats those figures and their limits.

## Inputs
Symbol, asset class `equity`, the metric card, and the provider timestamps. The price series itself is not an input to the narrative.

## Procedure
1. Confirm the share is an equity. A ticker ending in 11 is not an equity until the caller said so.
2. Read the reference price, compound return, annualized volatility, maximum drawdown, return percentiles, and buy-and-hold inside the supplied window. The published window is the daily sample, about three months, not five years.
3. Read the 52-week low and high from the quote. They are a quote field, not the return of that interval.
4. Read price-to-book, trailing P/E, earnings per share, and dividend yield from the current statistics, with the provider's period. They are not recomputed from the three-month window. A missing multiple stays null.
5. Do not emit a DCF, a peer-target price, an analyst consensus, or a buy or sell. Those methods are not in the engine.
6. Attach headlines only through `market-news`. A headline is not a cause of the return.
7. Hand a fresh reference price to `scenario-analysis`. Hand every claim to `evidence-review`.

## Reading patterns
Use a pattern only as a question about a field the card already contains. Name the pattern in the prose. Do not import the analyst's portfolio, a price target, or a slogan as a number.

### Luiz Barsi Filho — dividends and a long holding period
Barsi's public pattern is to be a shareholder and to look at dividends, over many years.
- If dividend yield is present, report it with the provider period. Call it observed income for that period.
- If it is null, say the dividend lens has nothing to read. Do not estimate a payout.
- The return window is about three months of daily bars. Say that this is not his multi-year holding horizon. Do not stretch the sample.
- Do not compute a ceiling price (`preço teto`).

### Warren Buffett and Benjamin Graham — price is not value
Buffett's usable rules here are the circle of competence and the refusal to treat price as value. Graham's margin of safety needs an intrinsic value this engine does not calculate.
- Circle of competence: the prose stays inside the metric card, the 52-week quote field, and the current statistics.
- "Do not lose capital" is reported as the maximum drawdown of the sample, with the window. It is a path inside that window, not a verdict of permanent loss and not a buy level.
- Price versus value: quote trailing P/E and P/VP when they exist. Label them current statistics. Owner earnings, a moat score, and intrinsic value are absent, so margin of safety is not computed. Say that in one sentence.
- A negative earnings figure does not get a repaired P/E.

### Décio Bazin — look at the realized yield before the story
Bazin's pattern is to inspect the trailing dividend yield. Popular retellings add a fixed cutoff. AssetMind has no configured cutoff.
- Show the yield when the card has it.
- Do not grade the share as cheap or expensive against 6% or any other hurdle.
- A headline does not replace the yield.

## Restrictions
A stale close is not the reference price. Negative earnings do not get an invented P/E. Portal pages are not copied. A named investor is not a recommendation.

## Output
Brazilian Portuguese prose with the metrics, the sample window, the risks, and the uncertainties. Fields follow `contracts/report.schema.json`. `return_3m`, `return_6m`, and `return_12m` stay empty unless the received closes cover that calendar window. `coverage.score` is present fields divided by requested fields. It is not a recommendation to buy.

## Tests
A missing P/E stays null. A five-point series states the short-window limit. Injected source text does not appear in the narrative.
