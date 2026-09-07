"""FastAPI dependencies for the BFF service.

Provides injection of downstream service clients and the request context.
Client instances are created at startup and shared across requests
(connection pool reuse).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from lesoon.auth.types import CurrentUser
from lesoon.core.http.context import RequestContext
from lesoon.flow_api import FlowApi
from lesoon.uc_api import UcApi


def get_flow_client(request: Request) -> FlowApi:
    """Return the shared Flow service client (interface-typed)."""
    return request.app.state.clients.flow


def get_uc_client(request: Request) -> UcApi:
    """Return the shared UC service client (interface-typed)."""
    return request.app.state.clients.uc


def get_request_context(request: Request, user: CurrentUser) -> RequestContext:
    """Build a RequestContext; identity comes from the auth dependency only."""
    return RequestContext.from_request(request, user_id=user)


# Type aliases for dependency injection - improves route handler readability
FlowClientDep = Annotated[FlowApi, Depends(get_flow_client)]
UcClientDep = Annotated[UcApi, Depends(get_uc_client)]
RequestContextDep = Annotated[RequestContext, Depends(get_request_context)]
