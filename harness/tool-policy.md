# Tool policy

Workflow steps may call the provider registry. They may not accept a URL from a user or a model.

Outbound hosts are limited to the configured brapi, CoinGecko, and Banco Central base URLs. Skill scripts are not exposed as model tools.

No tool can place an order or sign a transaction.
