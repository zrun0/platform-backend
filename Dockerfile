# syntax=docker/dockerfile:1
# Per-service image: docker build --build-arg SERVICE=bff --build-arg PORT=8000 \
#   --build-arg GIT_SHA=$(git rev-parse --short HEAD) -t lesoon-bff:0.2.0 .
# (GIT_SHA/VERSION default to unknown/dev; compose passes them from the justfile.)
# uv is pinned to the version that authored uv.lock; bump both together.
# Base pinned by digest for reproducible builds; re-resolve with
#   curl -s https://hub.docker.com/v2/repositories/library/python/tags/3.14-slim | jq -r .digest
FROM python:3.14-slim@sha256:cad9a2c871761c413caa6fdd6441c783451e740a48aaeba60ae62a8b53525ef6 AS builder
ARG SERVICE
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0
COPY --from=ghcr.io/astral-sh/uv:0.12.7 /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
COPY apps packages ./
# --no-editable builds real wheels of the member and its workspace deps into
# the venv, so the runtime stage carries only the venv, no source tree.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable --package lesoon-${SERVICE}

FROM python:3.14-slim@sha256:cad9a2c871761c413caa6fdd6441c783451e740a48aaeba60ae62a8b53525ef6
ARG SERVICE
ARG PORT
ENV SERVICE=${SERVICE} \
    PORT=${PORT} \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
RUN useradd --system --uid 1001 app
WORKDIR /app
COPY --from=builder --chown=app:app /app/.venv /app/.venv
# Exact source commit and release version; compose passes them from the
# justfile (GIT_SHA=$(git rev-parse --short HEAD), VERSION=$(uv version --short)).
# Kept after the venv COPY so a new commit never invalidates the heavy layers.
ARG GIT_SHA=unknown
ARG VERSION=dev
LABEL org.opencontainers.image.revision=${GIT_SHA} \
      org.opencontainers.image.version=${VERSION}
USER app
EXPOSE ${PORT}
# exec keeps uvicorn as PID 1 so SIGTERM reaches it; ${SERVICE} needs shell expansion.
# Single worker only: uc/flow keep state in per-process dicts.
# 30s graceful shutdown matches compose stop_grace_period (35s) so in-flight
# requests drain before SIGKILL.
CMD ["sh", "-c", "exec uvicorn lesoon.${SERVICE}.main:app --host 0.0.0.0 --port ${PORT} --timeout-graceful-shutdown 30"]
