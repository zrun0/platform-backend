"""Pydantic models for the Flow service API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FlowResponse(BaseModel):
    """Response model for a flow resource."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    status: str
    created_at: datetime
    updated_at: datetime


class FlowCreate(BaseModel):
    """Request model for creating a flow."""

    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class FlowUpdate(BaseModel):
    """Request model for updating a flow."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    status: str | None = None
