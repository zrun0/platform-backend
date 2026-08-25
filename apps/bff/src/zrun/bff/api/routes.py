"""BFF API routes.

Aggregates data from downstream services (flow, uc) and exposes
frontend-friendly endpoints.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from zrun.auth.types import CurrentUser
from zrun.bff.dependencies import get_flow_client, get_request_context, get_uc_client
from zrun.core.http.context import RequestContext
from zrun.flow_api import FlowApi, FlowCreate, FlowResponse
from zrun.uc_api import UcApi, UserResponse

router = APIRouter()


@router.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


@router.get("/me")
def me(user: CurrentUser) -> dict[str, str]:
    """Placeholder endpoint wired to the shared auth package."""
    return {"user": user}


# ---------------------------------------------------------------------------
# Flow proxy endpoints (demonstrate BFF -> flow service calls)
# ---------------------------------------------------------------------------


@router.get("/flows", response_model=list[FlowResponse])
async def list_flows(
    flow_client: Annotated[FlowApi, Depends(get_flow_client)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> list[FlowResponse]:
    """List all flows (proxied from flow service)."""
    return await flow_client.list_flows(ctx=ctx)


@router.get("/flows/{flow_id}", response_model=FlowResponse)
async def get_flow(
    flow_id: str,
    flow_client: Annotated[FlowApi, Depends(get_flow_client)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> FlowResponse:
    """Get a single flow (proxied from flow service)."""
    return await flow_client.get_flow(flow_id, ctx=ctx)


@router.post("/flows", response_model=FlowResponse, status_code=201)
async def create_flow(
    payload: FlowCreate,
    flow_client: Annotated[FlowApi, Depends(get_flow_client)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> FlowResponse:
    """Create a flow (proxied to flow service)."""
    return await flow_client.create_flow(payload, ctx=ctx)


# ---------------------------------------------------------------------------
# User proxy endpoints (demonstrate BFF -> uc service calls)
# ---------------------------------------------------------------------------


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    uc_client: Annotated[UcApi, Depends(get_uc_client)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> UserResponse:
    """Get a single user (proxied from uc service)."""
    return await uc_client.get_user(user_id, ctx=ctx)


@router.get("/users/by-username/{username}", response_model=UserResponse)
async def get_user_by_username(
    username: str,
    uc_client: Annotated[UcApi, Depends(get_uc_client)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> UserResponse:
    """Get a user by username (proxied from uc service)."""
    return await uc_client.get_user_by_username(username, ctx=ctx)


# ---------------------------------------------------------------------------
# Aggregation endpoint (demonstrate BFF calling multiple services)
# ---------------------------------------------------------------------------


@router.get("/flows/{flow_id}/with-owner")
async def get_flow_with_owner(
    flow_id: str,
    flow_client: Annotated[FlowApi, Depends(get_flow_client)],
    uc_client: Annotated[UcApi, Depends(get_uc_client)],
    ctx: Annotated[RequestContext, Depends(get_request_context)],
) -> dict[str, object]:
    """Aggregate a flow with its owner info.

    Demonstrates a BFF pattern: call multiple downstream services
    and combine the results.
    """
    flow = await flow_client.get_flow(flow_id, ctx=ctx)
    # In a real app, the flow would have an owner_id; here we demo
    # the pattern by fetching a user alongside the flow.
    return {
        "flow": flow.model_dump(),
        "owner": None,
    }
