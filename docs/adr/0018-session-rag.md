# ADR 0018 — Session retrieval

Status: accepted

Context: A follow-up question needs an earlier turn, and a report is longer than the characters the session index used to keep. ADR 0010 deferred a vector database until a filing corpus exists. ADR 0013 stored one hashed vector per turn. CVM filings are still not parsed, so there is no document corpus to index.

Decision: Retrieval applies to the chat session. Each turn is split into overlapping chunks, at most six. The question and the chunks are embedded with the same embedder. When `ASSETMIND_EMBEDDING_PROVIDER=groq` and `GROQ_API_KEY` is set, the embedder is Groq `nomic-embed-text-v1.5` (`POST /openai/v1/embeddings`). The call is reserved on the token allowance and written as a usage row of kind `embedding`. Without a key, or when the call fails, the chunk is stored with the hashed 64-bucket embedder from ADR 0013. Recall compares vectors only inside one embedder, always keeps the first user question, and stops at the existing token budget. The index stays in the local SQLite session file. pgvector and a filing corpus stay deferred.

Alternatives: Embed CVM documents now, or move the same hashed vectors into pgvector.

Consequences: A later question can retrieve a paragraph that is not the start of the report. A paraphrase is retrievable only while the Groq embedder is the one that wrote the chunks. Tests parse a recorded embedding response and do not call Groq. Hashed and model vectors are not mixed in one score.
