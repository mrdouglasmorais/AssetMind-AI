---
name: financial-data-provider
description: Adds or changes a market-data adapter for AssetMind. Use when working on brapi, CoinGecko, CVM, Banco Central, evidence, or provider errors.
---

# Financial data provider

1. Read the current vendor docs and note the free-tier limits in `context/data-sources.md`.
2. Allowlist the host. Set a timeout and a bounded retry only for idempotent GET requests.
3. Map the payload into `Evidence` and `PricePoint`. Leave missing values as null.
4. Store `observed_at` and `retrieved_at` separately.
5. Add a recorded fixture and a mock-transport test.
6. Do not treat free access as a license to redistribute the data.
