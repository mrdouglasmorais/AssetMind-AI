---
name: token-optimization
description: Reviews token budgets, context size, and model calls in AssetMind. Use when adding a prompt, agent, or context builder.
---

# Token optimization

1. Calculate in Python before calling a model.
2. Send metrics and disclosures, not raw price series.
3. Check the call against `BudgetManager` before it starts.
4. Keep estimated usage separate from actual usage.
5. Prefer a partial report over exceeding the configured USD guardrail.
