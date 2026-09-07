"""UC API routes."""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query

from zrun.auth.types import CurrentUser
from zrun.core.model_utils import partial_update_dict
from zrun.uc_api.models import UserCreate, UserResponse, UserUpdate

router = APIRouter()

# SCAFFOLD: in-memory store for demo — replace with real persistence (DB + repository layer)
_USERS: dict[str, UserResponse] = {}
_USERS_BY_USERNAME: dict[str, str] = {}

# Sync routes run on a threadpool, so every check-then-read/write sequence
# on the store and username index must be atomic to stay consistent and
# keep uniqueness under concurrency.
_USERS_LOCK = threading.Lock()


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
    with _USERS_LOCK:
        return list(_USERS.values())


@router.get("/users/by-username", response_model=UserResponse)
def get_user_by_username(username: Annotated[str, Query(...)]) -> UserResponse:
    """Retrieve a user by username."""
    with _USERS_LOCK:
        user_id = _USERS_BY_USERNAME.get(username)
        if user_id is None or user_id not in _USERS:
            raise HTTPException(status_code=404, detail="User not found")
        return _USERS[user_id]


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: str) -> UserResponse:
    """Retrieve a single user by ID."""
    with _USERS_LOCK:
        if user_id not in _USERS:
            raise HTTPException(status_code=404, detail="User not found")
        return _USERS[user_id]


@router.post("/users", response_model=UserResponse, status_code=201)
def create_user(
    payload: UserCreate,
    _user: CurrentUser,
) -> UserResponse:
    """Create a new user."""
    with _USERS_LOCK:
        if payload.username in _USERS_BY_USERNAME:
            raise HTTPException(status_code=409, detail="Username already exists")

        now = datetime.now(UTC)
        # UUID-based IDs: length-derived IDs collide under concurrency and
        # get resurrected after deletes.
        user_id = f"user_{uuid4()}"
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
    with _USERS_LOCK:
        if user_id not in _USERS:
            raise HTTPException(status_code=404, detail="User not found")
        existing = _USERS[user_id]
        # Explicit nulls are treated as omitted fields: no UserUpdate field
        # is nullable, so nothing can be cleared (derived from the schema).
        update_data = partial_update_dict(payload, UserResponse)
        new_username: str | None = update_data.get("username")
        if new_username is not None and new_username != existing.username:
            # Renames must keep the username index consistent and unique:
            # check first so a 409 never leaves partial state behind.
            owner_id = _USERS_BY_USERNAME.get(new_username)
            if owner_id is not None and owner_id != user_id:
                raise HTTPException(status_code=409, detail="Username already exists")
        # model_copy(update=) overlays already-validated fields (payload
        # constraints were checked at parse time), so no re-validation.
        update_data["updated_at"] = datetime.now(UTC)
        updated = existing.model_copy(update=update_data)
        _USERS[user_id] = updated
        if new_username is not None and new_username != existing.username:
            _USERS_BY_USERNAME.pop(existing.username, None)
            _USERS_BY_USERNAME[new_username] = user_id
    return updated


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: str,
    _user: CurrentUser,
) -> None:
    """Delete a user by ID."""
    with _USERS_LOCK:
        if user_id not in _USERS:
            raise HTTPException(status_code=404, detail="User not found")
        user = _USERS.pop(user_id)
        _USERS_BY_USERNAME.pop(user.username, None)
