"""Flow API routes."""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from lesoon.auth.types import CurrentUser
from lesoon.core.model_utils import partial_update_dict
from lesoon.flow_api.models import FlowCreate, FlowResponse, FlowUpdate

router = APIRouter()

# SCAFFOLD: in-memory store for demo — replace with real persistence (DB + repository layer)
_FLOWS: dict[str, FlowResponse] = {}

# Sync routes run on a threadpool, so every check-then-read/write sequence
# on the store must be atomic: concurrent deletes would otherwise raise
# KeyError and a delete racing an update would resurrect the deleted row.
_FLOWS_LOCK = threading.Lock()


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
    with _FLOWS_LOCK:
        return list(_FLOWS.values())


@router.get("/flows/{flow_id}", response_model=FlowResponse)
def get_flow(flow_id: str) -> FlowResponse:
    """Retrieve a single flow by ID."""
    with _FLOWS_LOCK:
        if flow_id not in _FLOWS:
            raise HTTPException(status_code=404, detail="Flow not found")
        return _FLOWS[flow_id]


@router.post("/flows", response_model=FlowResponse, status_code=201)
def create_flow(payload: FlowCreate, _user: CurrentUser) -> FlowResponse:
    """Create a new flow."""
    now = datetime.now(UTC)
    # UUID-based IDs: length-derived IDs collide under concurrency and
    # get resurrected after deletes.
    flow_id = f"flow_{uuid4()}"
    flow = FlowResponse(
        id=flow_id,
        name=payload.name,
        description=payload.description,
        status="created",
        created_at=now,
        updated_at=now,
    )
    with _FLOWS_LOCK:
        _FLOWS[flow_id] = flow
    return flow


@router.patch("/flows/{flow_id}", response_model=FlowResponse)
def update_flow(
    flow_id: str,
    payload: FlowUpdate,
    _user: CurrentUser,
) -> FlowResponse:
    """Update an existing flow."""
    with _FLOWS_LOCK:
        if flow_id not in _FLOWS:
            raise HTTPException(status_code=404, detail="Flow not found")
        existing = _FLOWS[flow_id]
        # Explicit null clears nullable fields (description) and is treated
        # as omitted for required ones (name, status) — derived from the
        # FlowUpdate schema, not a hand-maintained field list.
        update_data = partial_update_dict(payload, FlowResponse)
        update_data["updated_at"] = datetime.now(UTC)
        updated = existing.model_copy(update=update_data)
        _FLOWS[flow_id] = updated
    return updated


@router.delete("/flows/{flow_id}", status_code=204)
def delete_flow(
    flow_id: str,
    _user: CurrentUser,
) -> None:
    """Delete a flow by ID."""
    with _FLOWS_LOCK:
        if flow_id not in _FLOWS:
            raise HTTPException(status_code=404, detail="Flow not found")
        del _FLOWS[flow_id]
