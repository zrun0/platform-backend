# zrun

Python FastAPI monorepo, managed with [uv](https://docs.astral.sh/uv/) workspaces.
Shared packages live under the `zrun.*` namespace (PEP 420).

## Structure

```
apps/
  bff/    Backend-for-Frontend service (zrun-bff)
  uc/     User Center service (zrun-uc)
  flow/   Flow service (zrun-flow)
packages/
  core/       Shared core utilities (zrun-core)
  auth/       Shared auth utilities (zrun-auth)
  uc-api/     UC service API contract: models, protocol, and client (zrun-uc-api)
  flow-api/   Flow service API contract: models, protocol, and client (zrun-flow-api)
  test-utils/ Shared test helpers (zrun-test-utils; top-level module, outside the zrun.* namespace)
```

## Commands

```bash
just sync       # install all workspace packages + dev tools
just dev bff    # run BFF service (http://127.0.0.1:8000)
just dev uc     # run UC service
just dev flow   # run Flow service
just fmt        # ruff format
just lint       # ruff check
just check      # pyright type check
just test       # pytest
```
