# ADR 0024 — Durable analysis worker

Status: accepted

Context: Analyses previously ran inside the HTTP request with a deadline (ADR 0017). That couples client timeouts to workflow lifetime and loses in-flight work on process restart. OCI production Compose introduces a dedicated worker container.

Decision: Persist jobs in PostgreSQL (`analysis_jobs`) and execute them in `assetmind-worker`. The API enqueues when `ASSETMIND_JOB_QUEUE_ENABLED=true`: create analysis + job, return `status=queued`. Workers claim with atomic SQL (`FOR UPDATE SKIP LOCKED` on PostgreSQL), heartbeats/leases, fencing tokens, exponential backoff, partial results, and configurable concurrency. Redis is not used. Local development keeps the flag false so tests and `make watch` stay inline.

Alternatives: Keep in-request only; add Redis/RQ/Celery (extra memory and operational surface on Always Free).

Consequences: Clients of the OCI stack must poll for reports. Migrations include `0002_analysis_jobs`. Enabling the queue without a healthy worker leaves jobs pending.
