# ADR 0004 — OpenRouter

Status: superseded as the default provider by ADR 0012. The OpenRouter constructor remains.

Context: The series needs one model gateway and a place to enforce token limits.

Decision: Construct `agno.models.openrouter.OpenRouter` when a model id and API key are configured. The default analysis does not call it.

Alternatives: A direct vendor SDK, or no model gateway.

Consequences: Narrative spend stays optional. No production cost has been measured.
