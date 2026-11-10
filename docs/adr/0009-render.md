# ADR 0009 — Render

Status: superseded by ADR 0022

Context: The series needed a cheap, reproducible host.

Decision: Author one Docker web service and one free Postgres instance in `infra/render.yaml`. Bind `0.0.0.0:$PORT`. Leave AgentOS off.

Alternatives: Multiple services, or a platform that requires a cluster.

Consequences: The blueprint matches the current Render plan ids `free` for web and Postgres. It remains in the repo as an alternate. Free web services spin down, and free Postgres expires. Primary hosting is OCI Always Free (ADR 0022). No dollar price is stated here.
