# Tool policy

Workflow steps may call the provider registry. They may not accept a URL from a user or a model.

Outbound hosts are limited to the configured brapi, CoinGecko, and Banco Central base URLs, plus `news.google.com` for headline search and `api.groq.com` for chat and embeddings. The news tool returns title, publisher, date, link, and an image URL only when the feed item already includes one. It does not fetch the article. Skill scripts are not exposed as model tools.

No tool can place an order or sign a transaction.
