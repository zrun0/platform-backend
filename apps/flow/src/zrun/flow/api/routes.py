"""Flow API routes."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from zrun.auth.types import CurrentUser
from zrun.flow_api.models import FlowCreate, FlowResponse, FlowUpdate

router = APIRouter()

# In-memory store for demonstration purposes.
_FLOWS: dict[str, FlowResponse] = {}


@router.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


@router.get("/me")
def me(user: CurrentUser) -> dict[str, str]:
    """Placeholder endpoint wired to the shared auth package."""
    return {"user": user}


@router.get("/flows", response_model=list[FlowResponse])
def list_flows() -> list[FlowResponse]:
    """List all flows."""
    return list(_FLOWS.values())


@router.get("/flows/{flow_id}", response_model=FlowResponse)
def get_flow(flow_id: str) -> FlowResponse:
    """Retrieve a single flow by ID."""
    if flow_id not in _FLOWS:
        raise HTTPException(status_code=404, detail="Flow not found")
    return _FLOWS[flow_id]


@router.post("/flows", response_model=FlowResponse, status_code=201)
def create_flow(payload: FlowCreate, _user: CurrentUser) -> FlowResponse:
    """Create a new flow."""
    now = datetime.now(UTC)
    flow_id = f"flow_{len(_FLOWS) + 1}"
    flow = FlowResponse(
        id=flow_id,
        name=payload.name,
        status="created",
        created_at=now,
        updated_at=now,
    )
    _FLOWS[flow_id] = flow
    return flow


@router.put("/flows/{flow_id}", response_model=FlowResponse)
def update_flow(
    flow_id: str,
    payload: FlowUpdate,
    _user: CurrentUser,
) -> FlowResponse:
    """Update an existing flow."""
    if flow_id not in _FLOWS:
        raise HTTPException(status_code=404, detail="Flow not found")
    existing = _FLOWS[flow_id]
    update_data = payload.model_dump(exclude_unset=True)
    updated = FlowResponse(
        **{**existing.model_dump(), **update_data},
        updated_at=datetime.now(UTC),
    )
    _FLOWS[flow_id] = updated
    return updated


@router.delete("/flows/{flow_id}", status_code=204)
def delete_flow(
    flow_id: str,
    _user: CurrentUser,
) -> None:
    """Delete a flow by ID."""
    if flow_id not in _FLOWS:
        raise HTTPException(status_code=404, detail="Flow not found")
    del _FLOWS[flow_id]
