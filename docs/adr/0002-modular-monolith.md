# ADR 0002 — Modular monolith

Status: accepted

Context: The MVP has one API and one database. A network hop per specialist would add cost without a scaling requirement.

Decision: One Python process with package boundaries.

Alternatives: A service per agent, or a queue between fetch and report.

Consequences: Parallelism is in-process. A queue can be added later if a run no longer fits the request.
