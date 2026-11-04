# ADR 0005 — PostgreSQL

Status: accepted

Context: Analysis requests, reports, evidence, and usage must survive a restart.

Decision: SQLAlchemy models and an Alembic migration target PostgreSQL. Local development and tests may use SQLite. Agno session tables are left to Agno when a Postgres URL is later attached to a workflow.

Alternatives: Store reports only in Agno tables, or only in SQLite.

Consequences: Render should inject `DATABASE_URL`. The app normalizes the scheme for psycopg.
