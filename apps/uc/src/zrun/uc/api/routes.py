"""UC API routes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from zrun.auth.types import CurrentUser
from zrun.uc_api.models import UserCreate, UserResponse, UserUpdate

router = APIRouter()

# In-memory store for demonstration purposes.
_USERS: dict[str, UserResponse] = {}
_USERS_BY_USERNAME: dict[str, str] = {}


@router.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


@router.get("/me")
def me(user: CurrentUser) -> dict[str, str]:
    """Placeholder endpoint wired to the shared auth package."""
    return {"user": user}


@router.get("/users", response_model=list[UserResponse])
def list_users() -> list[UserResponse]:
    """List all users."""
    return list(_USERS.values())


@router.get("/users/by-username", response_model=UserResponse)
def get_user_by_username(username: Annotated[str, Query(...)]) -> UserResponse:
    """Retrieve a user by username."""
    user_id = _USERS_BY_USERNAME.get(username)
    if user_id is None or user_id not in _USERS:
        raise HTTPException(status_code=404, detail="User not found")
    return _USERS[user_id]


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: str) -> UserResponse:
    """Retrieve a single user by ID."""
    if user_id not in _USERS:
        raise HTTPException(status_code=404, detail="User not found")
    return _USERS[user_id]


@router.post("/users", response_model=UserResponse, status_code=201)
def create_user(
    payload: UserCreate,
    _user: CurrentUser,
) -> UserResponse:
    """Create a new user."""
    if payload.username in _USERS_BY_USERNAME:
        raise HTTPException(status_code=409, detail="Username already exists")

    now = datetime.now(UTC)
    user_id = f"user_{len(_USERS) + 1}"
    user = UserResponse(
        id=user_id,
        username=payload.username,
        email=payload.email,
        status="active",
        created_at=now,
        updated_at=now,
    )
    _USERS[user_id] = user
    _USERS_BY_USERNAME[payload.username] = user_id
    return user


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    payload: UserUpdate,
    _user: CurrentUser,
) -> UserResponse:
    """Update an existing user."""
    if user_id not in _USERS:
        raise HTTPException(status_code=404, detail="User not found")
    existing = _USERS[user_id]
    update_data = payload.model_dump(exclude_unset=True)
    updated = existing.model_copy(update={**update_data, "updated_at": datetime.now(UTC)})
    _USERS[user_id] = updated
    return updated


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: str,
    _user: CurrentUser,
) -> None:
    """Delete a user by ID."""
    if user_id not in _USERS:
        raise HTTPException(status_code=404, detail="User not found")
    user = _USERS.pop(user_id)
    _USERS_BY_USERNAME.pop(user.username, None)
