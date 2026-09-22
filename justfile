# novon monorepo tasks. Run `just --list` to see all recipes.

# Dev server listen ports. The BFF's downstream URLs come from its settings
# defaults (apps/bff/src/novon/bff/settings.py), which point at these same
# ports — also mirrored in compose.yaml (build args, published port, BFF
# downstream URL envs). Update every side together when changing one.
bff-port := "8000"
uc-port := "8001"
flow-port := "8002"

# Per-service dev port lookup (used by `dev` and `dev-all`).
dev-port service:
    @echo {{ if service == "bff" { bff-port } else if service == "uc" { uc-port } else if service == "flow" { flow-port } else { "8000" } }}

default:
    @just --list

# ---- Development Setup ----

# Sync workspace: install all packages and dev tools
sync:
    uv sync --all-packages

# ---- Service Development ----

# Run any service with auto-reload
# Usage: just dev <service-name>
# Examples: just dev bff, just dev uc, just dev flow
dev service:
    uv run --package novon-{{ service }} uvicorn novon.{{ service }}.main:app --reload --port $(just dev-port {{ service }})

# Run all three dev services together (Ctrl-C stops all)
dev-all:
    ./scripts/dev-all.sh

# ---- Code Quality ----

# Format all code with ruff
fmt:
    uv run ruff format .

# Lint all code with ruff
lint:
    uv run ruff check .

# Auto-fix all fixable code quality issues
fix:
    uv run ruff format . && uv run ruff check --fix .

# Type-check all code with pyright
check:
    uv run pyright .

# Run all read-only quality checks (use `fix` to format/auto-fix)
qa: lint check

# ---- Testing ----

# Run all tests
test:
    uv run --all-packages python -m pytest

# Run tests with coverage
test-cov:
    uv run --all-packages python -m pytest --cov=apps --cov=packages --cov-report=term-missing

# ---- Versioning ----

# Bump the whole workspace to one version (lockstep; members never diverge).
# Usage: just release 0.2.0
release v:
    #!/bin/sh
    set -eu
    uv version {{ v }}
    for d in apps/* packages/*; do
        [ -f "$d/pyproject.toml" ] || continue
        uv version --package "novon-${d##*/}" {{ v }}
    done

# ---- Docker ----

# Print the workspace version — the whole image tag (lockstep: root
# pyproject.toml is the single version source). The commit goes into the
# image's OCI labels, not the tag (see Dockerfile GIT_SHA/VERSION args).
[private]
_tag:
    @echo $(NO_COLOR=1 uv version --short)

# Build all three service images, each tagged with the workspace version
docker-build:
    IMAGE_VERSION=$(just _tag) \
    GIT_SHA=$(git rev-parse --short HEAD) \
    docker compose build

# Start the full stack detached (waits for healthchecks; 120s cap so a
# crash-looping container fails the recipe instead of hanging forever).
# IMAGE_VERSION defaults to the current version tag so `up` runs exactly
# what `docker-build` built; an explicitly exported env (rollback pin) wins.
docker-up:
    IMAGE_VERSION=${IMAGE_VERSION:-$(just _tag)} \
    docker compose up -d --wait --wait-timeout 120

# Stop the stack
docker-down:
    docker compose down

# Tail logs for all services, or one: just docker-logs bff
docker-logs service="":
    docker compose logs -f {{ service }}

# End-to-end smoke test: build, start, probe healthz + proxied write, teardown
docker-smoke:
    #!/bin/sh
    set -eu
    just docker-build
    # INT/TERM exit via their own trap so the EXIT trap fires teardown —
    # dash skips EXIT-trap on signal death, leaking the stack otherwise.
    trap 'just docker-down' EXIT
    trap 'exit 130' INT TERM
    just docker-up
    curl -fsS http://localhost:{{ bff-port }}/healthz > /dev/null
    curl -fsS -X POST http://localhost:{{ bff-port }}/flows \
        -H 'content-type: application/json' -d '{"name": "smoke"}' > /dev/null
    curl -fsS http://localhost:{{ bff-port }}/flows | grep -q smoke
    echo "docker smoke test OK"
