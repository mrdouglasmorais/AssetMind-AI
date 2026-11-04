# Security

AssetMind is a research and education API. It does not place orders, sign wallets, or move funds.

Report a vulnerability privately to the repository owner. Do not open a public issue with exploit detail.

Controls in this MVP:

- API keys come from the environment. Write routes require `X-API-Key`.
- Provider URLs are allowlisted. A prompt cannot choose a URL.
- External text is stored as data and is not copied into the narrative.
- AgentOS routes are disabled unless a JWT secret is configured.
- Logs are JSON and omit prompts and credentials.
- CI runs `scripts/scan_secrets.py`.

The in-process rate limit is per process. It is not a global control across many instances.
