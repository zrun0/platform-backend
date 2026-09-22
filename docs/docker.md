# Docker Deployment

All three service images are built from the single parameterized `Dockerfile`
at the repo root. Each image is scoped to one workspace member via
`uv sync --frozen --no-dev --no-editable --package lesoon-<service>`, so the
runtime image is `python:3.14-slim` plus a venv — no source tree, no dev tools.

## Commands

```bash
just docker-build        # build lesoon-bff, lesoon-uc, lesoon-flow
just docker-up           # start the stack detached; blocks until healthy
just docker-down         # stop the stack
just docker-logs bff     # tail one service (omit the name for all)
just docker-smoke        # build + up + probe + teardown; needs curl
```

## Topology

- Each container listens on its own port inside the network: bff `8000`,
  uc `8001`, flow `8002` (same as local dev).
- Only the BFF publishes a host port (`8000:8000`). UC and Flow are reachable
  only on the private `lesoon` bridge network.
- The BFF reaches downstream services via
  `FLOW_API_BASE_URL=http://flow:8002` and `UC_API_BASE_URL=http://uc:8001`,
  set in `compose.yaml`. Override them with a compose override file or
  `environment` entries if needed.
- Every service has a healthcheck on `GET /healthz`, implemented with the
  Python stdlib (`urllib`) because `python:*-slim` ships no curl or wget.
  `docker compose up --wait` gates startup on all three being healthy.

## Image versioning

`compose.yaml` runs `lesoon-<svc>:${IMAGE_VERSION:-latest}` — one variable
for all three services (lockstep), unset defaults to `latest`.
`just docker-build` and `just docker-up` set it to the workspace version
(e.g. `lesoon-bff:0.2.0`) from `just _tag`, which reads the root
`pyproject.toml`.

Versions are lockstep: the root `pyproject.toml` is the single version
source; bump the whole workspace with `just release <version>` (rewrites all
member `pyproject.toml` files and `uv.lock` together).

The source commit is baked into the image as OCI labels, not the tag —
`docker build` receives `GIT_SHA` and `VERSION` build args (compose passes
them from the justfile). Inspect with:

```bash
docker inspect lesoon-bff:0.2.0 --format '{{.Config.Labels}}'
# map[org.opencontainers.image.revision:dc1a001 org.opencontainers.image.version:0.2.0]
```

Commit before building — the label records the commit, not the working tree,
so a dirty-tree build wears a clean-tree label. Rebuilding the same version
silently overwrites its tag: always `just release` a new version first.

Pin or roll back to an already-built tag:

```bash
IMAGE_VERSION=0.2.0 docker compose up -d
```

compose refuses nothing when the image exists locally, so the pin is real,
not a re-build of the current tree.

## Production notes

- **Base image is digest-pinned** in the Dockerfile. Bump deliberately: re-resolve
  with the `curl | jq -r .digest` command in the Dockerfile header comment, then
  rebuild. Renovate/dependabot can automate this later.
- **Build for the server arch explicitly**: dev machines are often arm64,
  servers amd64 — `docker buildx build --platform linux/amd64 ...` when the
  image is destined for a server, or images built locally will not run there.
- **Restart + drain**: services run `restart: unless-stopped`; uvicorn gets
  `--timeout-graceful-shutdown 30` and compose `stop_grace_period: 35s`, so
  `docker compose down` drains in-flight requests before SIGKILL.
- Not yet applied (needs a docker host to verify): `read_only: true`,
  `cap_drop: [ALL]`, `security_opt: [no-new-privileges]`. The runtime writes
  nothing, so these should be safe — test before enabling.
- Deferred until there is a measured need: `uvicorn[standard]` (uvloop,
  ~20-30% throughput; a root-constraints + relock change across all members).

## Constraints

- **One uvicorn worker per service, no more.** UC and Flow keep their state in
  per-process dicts; multiple workers would silently split the data. Do not
  add `--workers` until those stores move to shared persistence.
- The uv version in the Dockerfile (`ghcr.io/astral-sh/uv:0.12.7`) is pinned
  to the version that authored `uv.lock`. Bump them together or
  `uv sync --frozen` fails on a lock-revision mismatch.
- The runtime stage may not change base image or venv path: the venv is copied
  from the builder stage, and `pyvenv.cfg` / script shebangs are absolute
  (`/app/.venv` on `python:3.14-slim`). Changing either breaks it silently.
