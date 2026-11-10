---
name: financial-data-provider
description: Adds or changes a market-data adapter for AssetMind. Use when working on brapi, CoinGecko, CVM, or Banco Central adapters.
---

# Financial data provider

1. Read the current vendor docs and note the free-tier limits in `docs/reference/data-sources.md`.
2. Keep adapters in `src/assetmind/providers`.
3. Normalize into domain evidence and price points. Do not invent missing values.
4. Cover success and failure with `MockTransport` or recorded JSON.
5. Update `docs/reference/data-sources.md` when a limit or endpoint changes.
