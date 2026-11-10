# Context policy

Context is assembled in code, not by appending history.

Sections, in order: fixed instructions, the compact metric list, uncertainties, and the output language. Raw price series stay in Python. Provider prose is not included. A character budget truncates the metric block and marks the truncation.

The analysis workflow sends the metric summary. The chat session stores each turn as overlapping chunks and retrieves a budgeted excerpt. The embedder is Groq when configured, and the hashed index otherwise. Raw price series stay out of that excerpt.
