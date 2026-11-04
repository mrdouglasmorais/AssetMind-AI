# Analysis contracts

`Evidence` fields: provider, source_url, asset_id, observed_at, retrieved_at, metric, value, unit, currency, period, quality_status.

Quality is one of ok, missing, stale, conflicting, estimated, not_applicable.

Price freshness: 3 days for B3 names, 15 minutes for crypto. Fundamentals: 120 days, or 2 days for crypto market cap and volume. Distributions: 45 days.

Compound return is `close_end / close_start - 1`. Volatility is the sample standard deviation of simple returns times the square root of 252 or 365. Maximum drawdown is the minimum of `close / running_peak - 1`.

Scenarios use `reference_price * (1 + shock)`.
