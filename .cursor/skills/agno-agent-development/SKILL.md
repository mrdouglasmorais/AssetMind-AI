---
name: agno-agent-development
description: Build or modify Agno agents, teams and workflows in AssetMind AI.
---

# Agno agent development

1. Read `docs/specs/agent-contracts.md`.
2. Read `docs/specs/non-functional.md`.
3. Prefer a deterministic function over a new model call.
4. Keep runtime skill text under `agent/skills/`. Do not confuse with `.cursor/skills/`.
5. Leave AgentOS off on the public host unless an ADR changes that.
6. Add or update tests that do not require a paid model call.
