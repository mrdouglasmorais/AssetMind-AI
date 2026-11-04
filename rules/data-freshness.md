# Data freshness rules

A current-price request uses only a close inside the freshness window. Older closes may remain in the historical series and must be described as history. Cached current prices that are past the window are a cache miss, not a fallback.
