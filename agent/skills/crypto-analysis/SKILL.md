---
name: crypto-analysis
description: Explain one crypto asset from CoinGecko evidence and the 365-period volatility convention.
---

# Crypto analysis

## Purpose
Explain price, volume, and market cap for one CoinGecko asset. Identity is the coin id, not a ticker that collides with another chain.

## Inputs
Coin id (`bitcoin`, `ethereum`, or another id the provider resolved), the metric card, and timestamps. Aliases `btc`, `eth`, and `sol` resolve before this skill runs.

## Procedure
1. Use the resolved coin id. Do not treat a wrapped token or a same-named ticker as this asset unless the id says so.
2. Read the reference price. Crypto price is fresh for 15 minutes. A stale print is not the reference price.
3. Read compound return, maximum drawdown, and the historical percentiles. The percentiles describe the sample. They are not probabilities of a future return.
4. Annualized volatility uses 365 periods. It is not a forecast and not a GARCH path.
5. Market cap and volume stay null when the provider omits them. Volume is not proof of executable liquidity. Depth, funding, open interest, and unlock schedules are not in the feed, so they stay unassessed.
6. On-chain activity, derivatives, and a promised yield are absent. Do not fill them from the coin's name or from a headline.
7. Link a headline only through `market-news`, and do not treat it as a price driver.

## Reading patterns
Crypto commentary is full of price paths this tool cannot see. Use only the lenses that match CoinGecko fields. Name the lens. Do not quote an influencer's target.

### Lyn Alden — measure the series, separate the story
Alden's useful pattern here is to keep a macro or narrative claim apart from the market series.
- Read reference price, compound return, maximum drawdown, percentiles, and 365-period volatility from the card.
- Read market cap and volume only when present.
- A headline may be listed through `market-news`. It is not a factor loading, a halving effect, or a reason the return happened.
- Do not extend the received window into a cycle.

### Andreas M. Antonopoulos — explain, do not instruct
Antonopoulos's public pattern is education without a trade and without a promised yield.
- Describe the series and the gaps.
- Custody, keys, and whether the holder controls the coin are outside this tool. Say they were not assessed.
- No buy, sell, staking pitch, or "get rich" sentence.

### On-chain schools — out of scope
Willy Woo and the Coin Metrics style of research need chain data, realized cap, or dormancy. Those fields are not in the tool. Write that the on-chain lens was not applied. Do not approximate it with volume or market cap.

### Refused price models
Stock-to-flow, a halving calendar, and any published price target are forecasts. They are not computed. Do not mention a target number from memory.

## Restrictions
No guaranteed yield, no intraday target, and no trading instruction. A missing supply or contract check suppresses any valuation sentence. Volume remains a reported figure, not proof of executable liquidity.

## Output
Brazilian Portuguese prose limited to the supplied metrics, the 365-period convention, and the stated gaps.

## Tests
A null market cap is disclosed as missing. `bitcoin` with a fresh close keeps the provider timestamp. A paraphrase of the coin without the id does not invent a second asset.
