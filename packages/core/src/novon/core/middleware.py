"""Middleware for request ID and trace ID propagation."""

from __future__ import annotations

import logging
import re
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

_HEADER_REQUEST_ID = "X-Request-ID"
_HEADER_TRACE_ID = "X-Trace-ID"

logger = logging.getLogger(__name__)

# Client-supplied request IDs are echoed into logs, downstream headers, and
# responses, so only accept single-line printable tokens. The charset is
# RFC 9110 tchar plus ':' (LB/edge-generated IDs such as "edge-1:57f6a2")
# and '=' (base64 padding); CR/LF, spaces, and non-ASCII stay excluded, so
# log and header injection remain impossible. Length capped well below the
# h11 header-size limit.
_TOKEN_PATTERN = re.compile(r"[!#$%&'*+.=:^_`|~A-Za-z0-9-]{1,512}")


def sanitize_header_token(raw: str | None) -> str:
    """Return the raw header token if it is safe, else a fresh UUID4."""
    if raw and _TOKEN_PATTERN.fullmatch(raw):
        return raw
    return str(uuid4())


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Read or generate a request ID and trace ID, attached to request state.

    Request IDs: an inbound `X-Request-ID` is used only when it matches a
    printable single-line token; anything else (missing, oversized,
    whitespace, control or non-ASCII characters) is replaced with a fresh
    UUID4 to prevent log or header injection. The ID is also set on the
    response so callers can correlate logs and traces.

    Trace IDs: with ``trust_inbound_trace`` (internal services reached only
    from the private network), a valid inbound `X-Trace-ID` is continued so
    traces join across service hops; without it (the external edge, e.g.
    the BFF), a fresh UUID4 is minted per request and client-supplied
    traces are never continued.
    """

    def __init__(self, app: ASGIApp, *, trust_inbound_trace: bool = False) -> None:
        super().__init__(app)
        self._trust_inbound_trace = trust_inbound_trace

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        raw_id = request.headers.get(_HEADER_REQUEST_ID)
        request_id = sanitize_header_token(raw_id)
        if raw_id is not None and request_id != raw_id:
            # Replacing a caller-supplied ID silently breaks their log
            # correlation; leave a diagnostic trace of the substitution.
            # Truncate: the raw value is attacker-controllable and can be
            # kilobytes long, and this fires on every offending request.
            logger.warning(
                "Replaced invalid X-Request-ID %r with a generated UUID",
                raw_id[:64],
            )
        request.state.request_id = request_id

        if self._trust_inbound_trace:
            trace_id = sanitize_header_token(request.headers.get(_HEADER_TRACE_ID))
        else:
            trace_id = str(uuid4())
        request.state.trace_id = trace_id

        response = await call_next(request)

        response.headers[_HEADER_REQUEST_ID] = request_id
        return response
