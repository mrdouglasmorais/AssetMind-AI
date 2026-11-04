# Architecture

AssetMind is a modular monolith.

`domain` defines assets, evidence, scenarios, and calculations. `providers` adapt brapi, CoinGecko, Banco Central, and a CVM fixture source. `application` applies budgets and stores the use case. `workflows` is an Agno workflow that calls those functions. `api` is FastAPI. `persistence` holds application tables.

The workflow input is the analysis id. Steps look up an in-process run context so provider clients do not have to be serialized through Agno.

See `docs/adr` for the decisions and the README for what has actually been executed.
