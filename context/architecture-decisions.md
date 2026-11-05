# Decision index

Accepted decisions are in `docs/adr`. The short version:

- Agno is the only orchestrator.
- One deployable process, not a service per agent.
- The product API is FastAPI. AgentOS is optional and authenticated.
- OpenRouter is the optional model gateway.
- PostgreSQL is the production store. SQLite is the zero-dependency local default.
- Calculations are deterministic.
- Context sent to a model is a metric summary.
- Evidence keeps provenance and is validated before presentation.
- Render is the target host. A live deploy is still pending.
- Chat sessions are chunked and embedded. A filing corpus and pgvector stay deferred.
- Horizon returns stay empty until the series covers them. The coverage score is not a buy grade.
- News cards show a feed image only when the item declares one. The article page stays unopened.
- Live search reads the brapi quote list and the CoinGecko coin list. The chat shows a page of that directory.
