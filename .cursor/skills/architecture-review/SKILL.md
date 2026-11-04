---
name: architecture-review
description: Reviews AssetMind changes against modular-monolith boundaries, ADRs, and domain isolation. Use when changing packages, dependencies, or orchestration.
---

# Architecture review

1. Read `specs/product.md` and `docs/adr/`.
2. Confirm `domain` does not import Agno, FastAPI, or a vendor SDK.
3. Reject a new service, queue, or database unless an ADR records the requirement.
4. Check that the README status matches the code.
5. Report the files reviewed and any decision that still needs an ADR.
