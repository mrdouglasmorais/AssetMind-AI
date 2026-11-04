# Budget policy

The budget manager counts provider calls, tool calls, estimated tokens, and estimated USD before a model call. Actual token counts are recorded only when a provider returns them.

Defaults live in settings and scale total tokens, provider calls, and estimated cost by the number of assets. LLM call count and narrative output tokens do not scale.

When a limit is crossed, the run stops and keeps any asset result already calculated. The status is `partial` when those results exist.
