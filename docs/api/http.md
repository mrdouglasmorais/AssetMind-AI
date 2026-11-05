# HTTP API

The browser entry is the Agno Agent UI. `/`, `/docs`, and `/redoc` redirect to it. Swagger is not mounted. The machine-readable schema remains at `/openapi.json`.

Create an analysis:

```json
{
  "assets": [
    {"symbol": "PETR4"},
    {"symbol": "bitcoin", "asset_class": "crypto"},
    {"symbol": "HGLG11", "asset_class": "real_estate"}
  ],
  "scenarios": {"bear": -0.2, "base": 0, "bull": 0.15}
}
```

The response status is `completed`, `partial`, or `failed`. `partial` means at least one explicit limit or data gap. The report repeats the deterministic metrics in Brazilian Portuguese and includes the disclaimer.

Events are stored rows replayed as `text/event-stream`. They are not a live token stream from a model.
