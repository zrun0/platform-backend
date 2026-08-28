# zrun monorepo tasks. Run `just --list` to see all recipes.

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
    uv run --package zrun-{{ service }} uvicorn zrun.{{ service }}.main:app --reload

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

# Run all quality checks: format, lint, and type-check
qa: fmt lint check

# ---- Testing ----

# Run all tests
test:
    python -m pytest

# Run tests with coverage
test-cov:
    python -m pytest --cov=apps --cov=packages --cov-report=term-missing
