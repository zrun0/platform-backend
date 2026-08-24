"""Middleware for request ID propagation."""

from __future__ import annotations

from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

_HEADER_REQUEST_ID = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Read or generate a request ID and attach it to the request state.

    If the incoming request carries an `X-Request-ID` header, its value is
    used. Otherwise a new UUID4 is generated. The ID is also set on the
    response so callers can correlate logs and traces.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get(_HEADER_REQUEST_ID) or str(uuid4())
        request.state.request_id = request_id

        response = await call_next(request)

        response.headers[_HEADER_REQUEST_ID] = request_id
        return response
