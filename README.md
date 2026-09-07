# lesoon

Python FastAPI monorepo, managed with [uv](https://docs.astral.sh/uv/) workspaces.
Shared packages live under the `lesoon.*` namespace (PEP 420).

## Structure

```
apps/
  bff/    Backend-for-Frontend service (lesoon-bff)
  uc/     User Center service (lesoon-uc)
  flow/   Flow service (lesoon-flow)
packages/
  core/       Shared core utilities (lesoon-core)
  auth/       Shared auth utilities (lesoon-auth)
  uc-api/     UC service API contract: models, protocol, and client (lesoon-uc-api)
  flow-api/   Flow service API contract: models, protocol, and client (lesoon-flow-api)
  test-utils/ Shared test helpers (lesoon-test-utils; top-level module, outside the lesoon.* namespace)
```

## Commands

```bash
just sync       # install all workspace packages + dev tools
just dev bff    # run BFF service (http://127.0.0.1:8000)
just dev uc     # run UC service (http://127.0.0.1:8001)
just dev flow   # run Flow service (http://127.0.0.1:8002)
just dev-all    # run all three services together
just fmt        # ruff format
just lint       # ruff check
just check      # pyright type check
just test       # pytest
```

Start `dev flow` and `dev uc` before `dev bff` — the BFF proxies to them at
`http://127.0.0.1:8002` and `http://127.0.0.1:8001` (or use `dev-all`).
Listen ports are variables at the top of the `justfile`; the BFF's downstream
URLs default to the same ports in `apps/bff/src/lesoon/bff/settings.py`
(override with `FLOW_API_BASE_URL` / `UC_API_BASE_URL`).
