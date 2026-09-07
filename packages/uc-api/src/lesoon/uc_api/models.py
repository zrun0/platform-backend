"""Pydantic models for the UC (User Center) service API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserResponse(BaseModel):
    """Response model for a user resource."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    email: str
    status: str
    created_at: datetime
    updated_at: datetime


class UserCreate(BaseModel):
    """Request model for creating a user."""

    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    """Request model for updating a user."""

    username: str | None = Field(default=None, min_length=3, max_length=50)
    email: str | None = Field(default=None, min_length=3, max_length=254)
    status: str | None = None
