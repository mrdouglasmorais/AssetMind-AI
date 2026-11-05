# Agent UI

This directory vendors [agno-agi/agent-ui](https://github.com/agno-agi/agent-ui), the open-source chat interface for AgentOS. The only local change is the default endpoint in `agent-ui/src/store.ts`: `NEXT_PUBLIC_AGENT_OS_URL`, or `http://127.0.0.1:8000` when that variable is empty.

`make watch` starts this UI on port 3000 and the API on port 8000. The API redirects `/`, `/docs`, and `/redoc` here. Swagger is not served.

The UI sends `NEXT_PUBLIC_OS_SECURITY_KEY` as a bearer token. Locally that is the same value as `ASSETMIND_API_KEY` unless `ASSETMIND_OS_SECURITY_KEY` is set. The product routes still use `X-API-Key`.
