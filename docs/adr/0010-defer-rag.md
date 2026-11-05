# ADR 0010 — Defer RAG

Status: accepted, amended by ADR 0018 for chat-session retrieval. A filing corpus and a vector database remain deferred.

Context: The MVP answers from structured market data and a few labeled fund facts. It does not search a corpus.

Decision: Do not add a vector database or a retrieval pipeline until a filing-search use case is specified.

Alternatives: Embed CVM documents now.

Consequences: There is no retrieval quality to claim. CVM parsing remains a separate, explicit task.
