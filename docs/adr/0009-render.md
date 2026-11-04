# ADR 0009 — Render

Status: provisional

Context: The series needs a cheap, reproducible host.

Decision: Author one Docker web service and one free Postgres instance in `render.yaml`. Bind `0.0.0.0:$PORT`. Leave AgentOS off.

Alternatives: Multiple services, or a platform that requires a cluster.

Consequences: The blueprint matches the current Render plan ids `free` for web and Postgres. It has not been synced. Free web services spin down, and free Postgres expires. No dollar price is stated here.
