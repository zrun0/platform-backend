# X-Request-ID charset may be too narrow for real-world client IDs

Status: ready-for-human

## Background

`sanitize_request_id` (packages/core/src/zrun/core/middleware.py) accepts
only `[A-Za-z0-9._~-]{1,128}`. IDs using base64 (`+`, `/`, `=`), colon
separation (`edge-1:57f6a2`), or longer than 128 chars are silently replaced
with a fresh UUID4 — the response echoes a different ID than the client sent,
breaking client-side log correlation with only a server-side warning.

Found by code review of the security-and-concurrency-fixes branch
(2026-09-07); the injection hardening itself is sound, this issue is only
about the compatibility window.

## Options

1. Widen to the RFC 9110 token charset (still CRLF/whitespace safe but
   accepts `+:/=` etc.).
2. Keep the strict charset and document it as an intentional breaking change
   in the API docs / changelog.

## Constraint

Whatever charset is chosen must stay single-line and header-safe; the
decision needs a human call on which real-world ID formats we must honor.
