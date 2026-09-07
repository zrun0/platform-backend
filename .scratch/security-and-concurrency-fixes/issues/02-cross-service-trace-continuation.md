# Trace ID continuation across services is structurally impossible

Status: needs-triage

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
