# ADR 0007 — Context minimization

Status: accepted

Context: Sending raw history to a model spends tokens and invites the model to misuse source text.

Decision: The context builder sends symbols, metrics, and uncertainties, with a character cap. Provider prose is excluded.

Alternatives: Full transcripts, or a vector store of filings.

Consequences: The default report is reproducible. Semantic summarization is deferred.
