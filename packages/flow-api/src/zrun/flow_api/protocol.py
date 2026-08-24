"""Abstract protocol defining the Flow service API interface.

Both the real HTTP client and test fakes/mocks implement this protocol,
enabling dependency substitution without inheritance coupling.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from zrun.core.http.context import RequestContext
    from zrun.flow_api.models import FlowCreate, FlowResponse, FlowUpdate


class FlowApi(Protocol):
    """Abstract interface for the Flow service API."""

    async def get_flow(
        self,
        flow_id: str,
        *,
        ctx: RequestContext | None = None,
    ) -> FlowResponse:
        """Retrieve a single flow by ID."""
        ...

    async def list_flows(
        self,
        *,
        ctx: RequestContext | None = None,
    ) -> list[FlowResponse]:
        """List all flows."""
        ...

    async def create_flow(
        self,
        payload: FlowCreate,
        *,
        ctx: RequestContext | None = None,
    ) -> FlowResponse:
        """Create a new flow."""
        ...

    async def update_flow(
        self,
        flow_id: str,
        payload: FlowUpdate,
        *,
        ctx: RequestContext | None = None,
    ) -> FlowResponse:
        """Update an existing flow."""
        ...

    async def delete_flow(
        self,
        flow_id: str,
        *,
        ctx: RequestContext | None = None,
    ) -> None:
        """Delete a flow by ID."""
        ...
