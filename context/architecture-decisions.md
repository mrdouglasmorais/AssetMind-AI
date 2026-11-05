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
