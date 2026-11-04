FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    PORT=10000 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock README.md alembic.ini ./
COPY src ./src
COPY skills ./skills
COPY migrations ./migrations
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 10000
CMD ["sh", "-c", "alembic upgrade head && uvicorn assetmind.main:app --host 0.0.0.0 --port ${PORT}"]
