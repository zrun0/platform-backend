"""FastAPI dependencies for the BFF service.

Provides injection of downstream service clients and the request context.
Client instances are created at startup and shared across requests
(connection pool reuse).
"""

from __future__ import annotations

from fastapi import Request

from zrun.core.http.context import RequestContext
from zrun.flow_api import FlowApi
from zrun.uc_api import UcApi


def get_flow_client(request: Request) -> FlowApi:
    """Return the shared Flow service client (interface-typed)."""
    return request.app.state.clients.flow  # type: ignore[no-any-return]


def get_uc_client(request: Request) -> UcApi:
    """Return the shared UC service client (interface-typed)."""
    return request.app.state.clients.uc  # type: ignore[no-any-return]


def get_request_context(request: Request) -> RequestContext:
    """Build a RequestContext from the current incoming request."""
    return RequestContext.from_request(request)
