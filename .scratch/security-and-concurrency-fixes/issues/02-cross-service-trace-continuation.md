# Trace ID continuation across services is structurally impossible

Status: resolved

## Background

`RequestContext.from_request` (packages/core/src/zrun/core/http/context.py)
always mints a fresh `trace_id` and ignores the inbound `X-Trace-ID` header.
That is the correct edge (BFF) trust-boundary behavior, but the same shared
helper is also the documented pattern for internal services: the BFF mints
T1 and forwards it to flow/uc, and any downstream using `from_request`
discards T1 and mints T2. Every hop fragments the trace, so distributed
waterfalls can never join.

Found by code review of the security-and-concurrency-fixes branch
(2026-09-07). `X-Trace-ID` is currently write-only (no consumer in the
repo), so nothing is broken today — this is a design gap to resolve before
tracing is actually adopted.

## Proposed direction

Make the boundary explicit instead of baking the edge policy into shared
per-hop code:

- At the external edge (BFF): sanitize-and-continue or mint fresh (current
  behavior), and/or
- Internal services: trust `X-Trace-ID` from authenticated internal callers
  (mirroring how `request_id` is validated-and-continued), possibly via an
  opt-in flag on `from_request` or a middleware-owned
  `request.state.trace_id`.

Needs a design decision (ADR candidate) before implementation.

## Resolution

Resolved (2026-09-07) with the boundary-aware design:

- `RequestIDMiddleware` now also resolves a trace ID onto
  `request.state.trace_id`. With `trust_inbound_trace=True` (internal
  services, set via `create_basic_app(..., trust_inbound_trace=True)` in
  uc/flow), a validated inbound `X-Trace-ID` is continued so the BFF's
  trace joins across hops; invalid values are replaced with a fresh UUID.
- The external edge (BFF) keeps the default `False`: client-supplied
  traces are never continued, a fresh UUID is minted per request.
- `RequestContext.from_request` reads `request.state.trace_id` (never the
  raw header), mirroring request_id handling.

The BFF mints T1 -> forwards X-Trace-ID: T1 -> uc/flow continue T1 in
their state, so future downstream calls and span export share one trace.
