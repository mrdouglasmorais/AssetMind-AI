# ADR 0013 — Local session vectors

Status: accepted

Context: The chat agent treated every message as a new request. Replaying full reports would exceed the token budget, and the model then said the session history was unavailable.

Decision: Persist each turn in a SQLite table with a deterministic hashed embedding. Retrieval is cosine similarity over that session, always keeps the first user question, and stops at an estimated budget of 600 tokens. The compact block is injected as Agno knowledge references. Bear, base, and bull remain illustrative shocks. The published sample window is the provider series, about three months, not five years.

Alternatives: Replay every Agno run, or call an embedding model for the index.

Consequences: Follow-ups can reuse the prior asset set without a second model call for retrieval. The index is not a market-data store and does not rank investments. Tests do not call Groq.
