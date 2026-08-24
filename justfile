# zrun monorepo tasks. Run `just --list` to see all recipes.

default:
    @just --list

# Sync workspace: install all packages and dev tools
sync:
    uv sync --all-packages

# Run the BFF service with auto-reload
dev-bff:
    uv run --package zrun-bff uvicorn zrun.bff.main:app --reload

# Run the UC service with auto-reload
dev-uc:
    uv run --package zrun-uc uvicorn zrun.uc.main:app --reload

# Run the Flow service with auto-reload
dev-flow:
    uv run --package zrun-flow uvicorn zrun.flow.main:app --reload

# Format all code with ruff
fmt:
    uv run ruff format .

# Lint all code with ruff
lint:
    uv run ruff check .

# Type-check all code with pyright
check:
    uv run pyright .

# Run all tests
test:
    python -m pytest
