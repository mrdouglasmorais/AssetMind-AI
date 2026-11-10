# Security spec

Secrets are environment variables. The API key is compared with `hmac.compare_digest`. CORS origins come from an allowlist and are empty by default.

Provider clients reject hosts outside their base URL. User input is not fetched.

AgentOS, including its filesystem and workflow control routes, is not mounted unless `ASSETMIND_AGENTOS_ENABLED=true` and `ASSETMIND_AGENTOS_JWT_SECRET` is set. Product routes are excluded from that JWT check and keep the API key.

The service does not implement trading.
