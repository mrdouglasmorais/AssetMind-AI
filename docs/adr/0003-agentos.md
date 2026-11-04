# ADR 0003 — Product API beside optional AgentOS

Status: accepted

Context: AgentOS exposes a large control surface, including filesystem and workflow routes. The product needs a small analysis API.

Decision: FastAPI owns `/health`, `/ready`, and `/api/v1`. AgentOS is mounted only when explicitly enabled, with JWT authorization, and it must not replace `/health`.

Alternatives: Use only AgentOS routes, or leave AgentOS open.

Consequences: Operators do not get the control plane on the public Render service by default.
