# ADR 0014 — Orchestrator ledger

Status: accepted

Context: A model that routes work and a specialist model per asset class would multiply token spend. The project already calculates in Python and stores estimated usage apart from actual usage.

Decision: One Agno workflow receives the request. The orchestrate step groups assets by class and assigns the equity, crypto, or real-estate specialist. Those specialists stay Python executors. The optional narrator is a single later call over the metric card, not over the price series. Every finished analysis writes a usage row. `GET /api/v1/usage/balance` sums that ledger against `ASSETMIND_TOKEN_ALLOWANCE`. Runtime skills `orchestration` and `token-balance` describe the same contract.

Alternatives: An Agno Team of model agents, or replaying full reports into the next turn.

Consequences: Routing costs no model tokens. The balance is an engineering ledger, not a provider invoice. Actual tokens appear only when a gateway reports them.
