"""Request context that propagates across service boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from fastapi import Request

_HEADER_AUTH = "Authorization"
_HEADER_REQUEST_ID = "X-Request-ID"
_HEADER_TRACE_ID = "X-Trace-ID"
_HEADER_USER_ID = "X-User-ID"


@dataclass
class RequestContext:
    """Carries cross-cutting request data between services.

    Use `from_request` to extract context from an incoming FastAPI request,
    and `to_headers` to attach it to an outbound service call.
    """

    auth_token: str | None = None
    request_id: str | None = None
    trace_id: str | None = None
    user_id: str | None = None

    @classmethod
    def from_request(cls, request: Request) -> RequestContext:
        """Build a RequestContext from an incoming FastAPI request.

        The request ID is resolved with the following priority:
        1. Upstream-supplied ``X-Request-ID`` header.
        2. Middleware-generated ID stored on ``request.state.request_id``.
        """
        auth_header = request.headers.get(_HEADER_AUTH)
        request_id = request.headers.get(_HEADER_REQUEST_ID)
        if request_id is None:
            request_id = getattr(request.state, "request_id", None)
        return cls(
            auth_token=auth_header,
            request_id=request_id,
            trace_id=request.headers.get(_HEADER_TRACE_ID),
            user_id=request.headers.get(_HEADER_USER_ID),
        )

    def to_headers(self) -> dict[str, str]:
        """Serialize context fields into HTTP headers for outbound calls."""
        headers: dict[str, str] = {}
        if self.auth_token:
            headers[_HEADER_AUTH] = self.auth_token
        if self.request_id:
            headers[_HEADER_REQUEST_ID] = self.request_id
        if self.trace_id:
            headers[_HEADER_TRACE_ID] = self.trace_id
        if self.user_id:
            headers[_HEADER_USER_ID] = self.user_id
        return headers

    def ensure_request_id(self) -> str:
        """Return the request_id, generating one if missing."""
        if self.request_id is None:
            self.request_id = str(uuid4())
        return self.request_id
