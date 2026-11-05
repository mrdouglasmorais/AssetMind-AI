FROM node:22-bookworm-slim

WORKDIR /ui
RUN corepack enable
COPY ui/agent-ui/package.json ui/agent-ui/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY ui/agent-ui ./
ENV NEXT_PUBLIC_AGENT_OS_URL=http://localhost:8000 \
    NEXT_PUBLIC_OS_SECURITY_KEY=local-dev-key
EXPOSE 3000
CMD ["pnpm", "dev", "--hostname", "0.0.0.0", "--port", "3000"]
