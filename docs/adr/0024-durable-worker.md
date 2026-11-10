# ADR 0024 — Durable analysis worker

Status: accepted (implementation phased)

Context: Analyses currently run inside the HTTP request with a deadline (ADR 0017). That couples client timeouts to workflow lifetime and loses in-flight work on process restart. OCI production Compose introduces a dedicated worker container.

Decision: Persist jobs in PostgreSQL and execute them in `assetmind-worker`. The API stays mostly stateless: create job, query status, stream stored events. Claim jobs with atomic SQL (`FOR UPDATE SKIP LOCKED` where applicable), heartbeats/leases, fencing tokens, exponential backoff, partial results, and configurable concurrency. Redis is not required for the first durable design.

Phase 2 ships the worker process and Compose service in idle mode (`ASSETMIND_JOB_QUEUE_ENABLED=false`). Phase 3 implements the queue schema and claim loop. Until Phase 3 lands, production API continues in-request execution.

Alternatives: Keep in-request only; add Redis/RQ/Celery (extra memory and operational surface on Always Free).

Consequences: New tables/migrations, API contract changes for async job creation, and an ADR update when the public API switches default mode. Coverage and load tests must include restart recovery before enabling the queue in production.
