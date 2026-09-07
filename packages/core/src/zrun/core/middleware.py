"""Middleware for request ID propagation."""

from __future__ import annotations

import logging
import re
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

_HEADER_REQUEST_ID = "X-Request-ID"

logger = logging.getLogger(__name__)

# Client-supplied request IDs are echoed into logs, downstream headers, and
# responses, so only accept single-line printable tokens. The charset is
# RFC 9110 tchar plus ':' (LB/edge-generated IDs such as "edge-1:57f6a2")
# and '=' (base64 padding); CR/LF, spaces, and non-ASCII stay excluded, so
# log and header injection remain impossible. Length capped well below the
# h11 header-size limit.
_REQUEST_ID_PATTERN = re.compile(r"[!#$%&'*+.=:^_`|~A-Za-z0-9-]{1,512}")


def sanitize_request_id(raw: str | None) -> str:
    """Return the raw request ID if it is safe, else a fresh UUID4."""
    if raw and _REQUEST_ID_PATTERN.fullmatch(raw):
        return raw
    return str(uuid4())


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Read or generate a validated request ID and attach it to request state.

    If the incoming request carries an `X-Request-ID` header, its value is
    used only when it matches a printable single-line token (RFC 9110 tchar
    plus ':'); anything else (missing, oversized, whitespace, control or
    non-ASCII characters) is replaced with a fresh UUID4 to prevent log or
    header injection. The ID is also set on the response so callers can
    correlate logs and traces.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        raw_id = request.headers.get(_HEADER_REQUEST_ID)
        request_id = sanitize_request_id(raw_id)
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

        response = await call_next(request)

        response.headers[_HEADER_REQUEST_ID] = request_id
        return response
