---
name: real-estate-analysis
description: Explain one Brazilian FII quota from price evidence and labeled fund facts.
---

# Real estate analysis

## Purpose
Explain a FII quota. A FII is not a CRI and not a direct property.

## Inputs
Ticker, asset class `real_estate` set by the caller, price evidence, and any labeled fund facts. Live parsing of the CVM monthly informe is not available.

## Procedure
1. Require the class. A ticker ending in 11 without `real_estate` or `equity` is not analyzed as a fund.
2. Read the reference price with the three-day equity freshness window. Distribution evidence older than 45 days is not treated as current.
3. Dividend yield needs a trailing distribution, a stated period, and a fresh reference price. A past distribution is not a promise that it continues. An extraordinary distribution is not relabeled as recurring income.
4. P/VP is shown only when the fact is present. It is not a sufficient valuation rule.
5. Vacancy applies only to a brick fund. A paper fund keeps credit risk and the indexer. An unknown classification does not receive a vacancy metric.
6. Fixture facts stay labeled as fixtures. Do not present them as a live CVM filing.
7. Interest-rate sensitivity is not a computed beta. Describe the fund type and the missing report, and leave the unmeasured channel out of the numbers.
8. Compare segments only on metrics both funds actually have.

## Reading patterns
A FII quota is not read with an equity DCF. The income lenses below only restate fund facts that are present.

### Luiz Barsi Filho — income already paid
Apply his dividend lens to the quota, not to a pretend company.
- Trailing distribution plus a fresh price can be stated as cash already paid in the named period.
- Do not call that yield a future salary, a Barsi pick, or proof the next month repeats.
- An extraordinary distribution stays labeled. It is not recurring income.
- The three-month price sample is not a multi-year holding result.

### FII card — yield, P/VP, and vacancy together
Brazilian fund research, including the card popularized by Professor Baroni, reads dividend yield, P/VP, and portfolio quality in one pass. This engine can read only the first numbers, and vacancy only for brick.
- If yield and P/VP both exist, show both and say neither one is a buy rule. A low P/VP is not a bargain by itself. A high yield is not quality by itself.
- Brick: add vacancy when the fact exists. Missing vacancy stays missing.
- Paper: do not print vacancy. Read credit risk and the indexer when those facts exist.
- Unknown classification: price and any labeled facts only. No vacancy.
- Tenant lists, contract expiry, and leverage are not in the tool. Say they were not read.

### Warren Buffett — do not import the equity valuation
Drawdown of the quota, when the price series produced it, describes the sample path. Owner earnings and a moat do not transfer to a fund quota. Do not invent them.

## Restrictions
Do not assume the next distribution. Do not invent net asset value, vacancy, or tenant concentration. Do not cite a fund manager's portfolio as if it were this report.

## Output
Brazilian Portuguese prose with the classification, the figures that exist, and the limits of what is absent.

## Tests
A brick fixture may report vacancy. A paper fixture with a vacancy field produces no vacancy metric. An unlabeled `*11` ticker is not routed here.
