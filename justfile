# zrun monorepo tasks. Run `just --list` to see all recipes.

# Dev server listen ports. The BFF's downstream URLs come from its settings
# defaults (apps/bff/src/zrun/bff/settings.py), which point at these same
# ports — update both sides when changing one.
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
    uv run --package zrun-{{ service }} uvicorn zrun.{{ service }}.main:app --reload --port $(just dev-port {{ service }})

# Run all three dev services together (Ctrl-C stops all)
dev-all:
    #!/bin/sh
    pids=""
    stop() {
        [ -n "$pids" ] && kill $pids 2>/dev/null
        exit "${1:-0}"
    }
    trap 'stop 130' INT TERM
    just dev flow & pids="$pids $!"
    just dev uc & pids="$pids $!"
    just dev bff & pids="$pids $!"
    n=$(echo $pids | wc -w | tr -d ' ')
    while :; do
        sleep 1
        alive=0
        for pid in $pids; do
            kill -0 "$pid" 2>/dev/null && alive=$((alive + 1))
        done
        if [ "$alive" -lt "$n" ]; then
            # A service died (e.g. port already in use): stop the rest
            # and exit nonzero instead of silently running a partial stack.
            stop 1
        fi
    done

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
