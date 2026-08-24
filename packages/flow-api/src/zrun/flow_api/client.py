"""HTTP client implementation of the Flow service API."""

from __future__ import annotations

from typing import Any

from zrun.core.http.base_client import BaseServiceClient
from zrun.core.http.context import RequestContext
from zrun.core.http.feign import delete, get, post, put
from zrun.flow_api.models import FlowCreate, FlowResponse, FlowUpdate


class FlowServiceClient(BaseServiceClient):
    """Typed HTTP client for the Flow service API.

    Implements the FlowApi protocol (structural subtyping).
    Endpoints are declared with Feign-style decorators; the decorators
    handle parameter binding and delegate to BaseServiceClient.request().
    """

    def __init__(self, base_url: str, **kwargs: Any) -> None:
        super().__init__(base_url=base_url, service_name="flow", **kwargs)

    @get("/flows/{flow_id}")
    async def get_flow(
        self,
        flow_id: str,
        *,
        ctx: RequestContext | None = None,
    ) -> FlowResponse:  # pragma: no cover - decorator provides implementation
        """Retrieve a single flow by ID."""
        ...

    @get("/flows")
    async def list_flows(
        self,
        *,
        ctx: RequestContext | None = None,
    ) -> list[FlowResponse]:  # pragma: no cover - decorator provides implementation
        """List all flows."""
        ...

    @post("/flows")
    async def create_flow(
        self,
        payload: FlowCreate,
        *,
        ctx: RequestContext | None = None,
    ) -> FlowResponse:  # pragma: no cover - decorator provides implementation
        """Create a new flow.

        Note: POST is non-idempotent so this call is NOT retried.
        """
        ...

    @put("/flows/{flow_id}")
    async def update_flow(
        self,
        flow_id: str,
        payload: FlowUpdate,
        *,
        ctx: RequestContext | None = None,
    ) -> FlowResponse:  # pragma: no cover - decorator provides implementation
        """Update an existing flow."""
        ...

    @delete("/flows/{flow_id}")
    async def delete_flow(
        self,
        flow_id: str,
        *,
        ctx: RequestContext | None = None,
    ) -> None:  # pragma: no cover - decorator provides implementation
        """Delete a flow by ID."""
        ...
