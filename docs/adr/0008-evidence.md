# ADR 0008 — Evidence provenance

Status: accepted

Context: A financial report without a source and a time is not reviewable.

Decision: Every observation records provider, source URL when known, observation time, and retrieval time. Conflicts and stale values change quality instead of being coerced.

Alternatives: Keep the latest vendor payload as an opaque blob.

Consequences: The report can show what was refused. Validators are ordinary Python.
