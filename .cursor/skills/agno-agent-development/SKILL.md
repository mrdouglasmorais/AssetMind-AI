---
name: agno-agent-development
description: Build or modify Agno agents, teams and workflows in AssetMind AI.
---

# Agno Agent Development

## When to use
Use when creating, modifying or reviewing any Agno
Agent, Team, Workflow or related tool.

## Procedure

1. Read specs/agent-contracts.md.
2. Read specs/non-functional.md.
3. Inspect existing workflow and domain contracts.
4. Verify the installed Agno version and API.
5. Define the component's responsibilities.
6. Prefer deterministic execution where possible.
7. Implement Pydantic input and output schemas.
8. Add explicit tool permissions and execution limits.
9. Enforce token and cost budgets.
10. Add unit and integration tests.
11. Verify errors, timeouts and partial failures.
12. Record relevant design decisions.

## Required acceptance criteria
- No unsupported financial facts.
- No unbounded agent loops.
- No unnecessary model calls.
- No secrets in logs.
- Structured outputs are validated.
- Errors are explicit and traceable.
- Tests are executed and results reported.
