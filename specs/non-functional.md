# Non-functional spec

- One analysis stays inside the request deadline, default 25 seconds.
- Provider calls, token estimates, and estimated USD are bounded.
- Logs include analysis id, correlation id, status, and call counts. They omit prompts and secrets.
- The domain test suite runs without network access to vendors or model gateways.
- Package coverage stays at or above 85%.
- The process binds `0.0.0.0:$PORT` and exposes `/health` and `/ready`.
