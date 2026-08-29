# Dependency Management

How third-party dependencies are added and upgraded in this workspace. For why
version constraints are centralized at the root, see
[ADR 0003](./adr/0003-centralized-version-constraints-at-workspace-root.md).

## Rules

- Version constraints for third-party packages live **only** in the root
  `pyproject.toml` under `[tool.uv] constraint-dependencies`.
- Workspace members declare **bare names** in their `dependencies`. A version
  specifier in a member package is a review blocker (`fastapi` ✅,
  `fastapi>=0.100` ❌).
- Workspace-internal packages (`zrun-*`) are wired in `[tool.uv.sources]` with
  `workspace = true`.

## Adding or upgrading a dependency

1. Add or adjust the constraint in the root `pyproject.toml`
   (`constraint-dependencies`).
2. Add the bare name to the member package's `dependencies` (plus a
   `[tool.uv.sources]` entry if it is a workspace package).
3. Re-lock and install: `just sync` (runs `uv sync --all-packages`).

The resulting `uv.lock` diff shows the blast radius across all consumers.
