# Novon Platform

FastAPI monorepo for the Novon backend, managed with [uv](https://docs.astral.sh/uv/) workspaces.
All runtime packages share the `novon.*` PEP 420 namespace.

## Structure

```
apps/
  bff/    Backend-for-Frontend service (novon-bff)
  uc/     User Center service (novon-uc)
  flow/   Flow service (novon-flow)
packages/
  core/       Shared core utilities (novon-core)
  auth/       Shared auth utilities (novon-auth)
  uc-api/     UC service API contract: models, protocol, and client (novon-uc-api)
  flow-api/   Flow service API contract: models, protocol, and client (novon-flow-api)
  test-utils/ Shared test helpers (novon-test-utils; top-level module, outside the novon.* namespace)
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
just docker-build  # build the three service images
just docker-up     # start the full stack (waits for healthchecks)
just docker-down   # stop the stack
just docker-logs   # tail service logs (omit name for all)
just docker-smoke  # end-to-end smoke test (build, up, probe, teardown)
```

Docker details (topology, env overrides, constraints) live in
[docs/docker.md](docs/docker.md).

Start `dev flow` and `dev uc` before `dev bff` — the BFF proxies to them at
`http://127.0.0.1:8002` and `http://127.0.0.1:8001` (or use `dev-all`).
Listen ports are variables at the top of the `justfile`; the BFF's downstream
URLs default to the same ports in `apps/bff/src/novon/bff/settings.py`
(override with `FLOW_API_BASE_URL` / `UC_API_BASE_URL`).
