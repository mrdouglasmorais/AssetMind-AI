# ADR 0011 — Agent UI and Scalar API docs

Status: accepted

Context: The human entry to the running API was the generated Swagger page. The project already uses Agno, and Agno publishes an open-source Agent UI that talks to AgentOS. Operators also need an interactive OpenAPI reference without bringing Swagger or ReDoc back.

Decision: Do not mount Swagger or ReDoc. Redirect `/` to the Agent UI. Serve API documentation with Scalar at `/scalar`. Redirect `/docs` and `/redoc` to `/scalar`. Keep `/openapi.json` as the machine-readable schema. Register one AgentOS agent, AssetMind Analyst, whose reply is the deterministic report for catalog assets named in the message. Local and Compose runs protect AgentOS with the OS security key. A JWT secret remains available. The public Render service keeps AgentOS disabled and leaves the UI URL empty.

Alternatives: Keep Swagger as the only interface, send every chat turn through OpenRouter, or mount Scalar at `/docs` instead of `/scalar`.

Consequences: `make watch` needs Node.js and starts two processes. The vendored UI lives in `ui/agent-ui` with the default endpoint pointed at this API. Render does not serve the UI until a separate deploy is validated. Bookmarks to `/docs` land on Scalar instead of the chat UI.
