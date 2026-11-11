# Architecture

AssetMind is a modular monolith.

`domain` defines assets, evidence, scenarios, calculations, and mover row types. `providers` adapt brapi, CoinGecko, Banco Central, and a CVM fixture source, including listings and movers. `application` applies budgets and stores the use case. `workflows` is an Agno workflow that calls those functions. `api` is FastAPI with Scalar at `/scalar` and optional AgentOS for the Agent UI. `persistence` holds application tables.

The workflow input is the analysis id. Steps look up an in-process run context so provider clients do not have to be serialized through Agno.

See `docs/adr` for the decisions, `docs/api/http.md` for the HTTP surface, `docs/reference/` for the short index, `docs/policies/` for execution guardrails, and the README for what has actually been executed. Repository layout is ADR 0023.
