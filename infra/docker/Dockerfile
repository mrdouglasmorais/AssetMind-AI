# syntax=docker/dockerfile:1.7
# Multi-arch (linux/arm64, linux/amd64). Production target is Ampere A1 ARM64.
# Do not rely on x86 emulation at runtime.

FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    UV_PYTHON_DOWNLOADS=0

COPY pyproject.toml uv.lock README.md alembic.ini ./
COPY src ./src
COPY agent ./agent
COPY migrations ./migrations
RUN uv sync --frozen --no-dev


FROM python:3.13-slim-bookworm AS runtime

RUN groupadd --system --gid 10001 assetmind \
    && useradd --system --uid 10001 --gid assetmind --home-dir /app --shell /usr/sbin/nologin assetmind \
    && apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder --chown=assetmind:assetmind /app /app
COPY --chown=assetmind:assetmind infra/docker/entrypoint.sh /app/entrypoint.sh

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ASSETMIND_SKILLS_DIR=agent/skills \
    PORT=8000 \
    ASSETMIND_ROLE=api

RUN chmod 755 /app/entrypoint.sh

USER assetmind:assetmind

EXPOSE 8000

# Health checks are defined per service in Compose (api vs worker roles share this image).

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["api"]
