"""HTTP client implementation of the UC service API."""

from __future__ import annotations

from typing import Any

from zrun.core.http.base_client import BaseServiceClient
from zrun.core.http.context import RequestContext
from zrun.core.http.feign import delete, get, post, put
from zrun.uc_api.models import UserCreate, UserResponse, UserUpdate


class UcServiceClient(BaseServiceClient):
    """Typed HTTP client for the UC (User Center) service API.

    Implements the UcApi protocol (structural subtyping).
    Endpoints are declared with Feign-style decorators; the decorators
    handle parameter binding and delegate to BaseServiceClient.request().
    """

    def __init__(self, base_url: str, **kwargs: Any) -> None:
        super().__init__(base_url=base_url, service_name="uc", **kwargs)

    @get("/users/{user_id}")
    async def get_user(
        self,
        user_id: str,
        *,
        ctx: RequestContext | None = None,
    ) -> UserResponse:  # pragma: no cover - decorator provides implementation
        """Retrieve a single user by ID."""
        ...

    @get("/users/by-username")
    async def get_user_by_username(
        self,
        username: str,
        *,
        ctx: RequestContext | None = None,
    ) -> UserResponse:  # pragma: no cover - decorator provides implementation
        """Retrieve a user by username."""
        ...

    @get("/users")
    async def list_users(
        self,
        *,
        ctx: RequestContext | None = None,
    ) -> list[UserResponse]:  # pragma: no cover - decorator provides implementation
        """List all users."""
        ...

    @post("/users")
    async def create_user(
        self,
        payload: UserCreate,
        *,
        ctx: RequestContext | None = None,
    ) -> UserResponse:  # pragma: no cover - decorator provides implementation
        """Create a new user.

        Note: POST is non-idempotent so this call is NOT retried.
        """
        ...

    @put("/users/{user_id}")
    async def update_user(
        self,
        user_id: str,
        payload: UserUpdate,
        *,
        ctx: RequestContext | None = None,
    ) -> UserResponse:  # pragma: no cover - decorator provides implementation
        """Update an existing user."""
        ...

    @delete("/users/{user_id}")
    async def delete_user(
        self,
        user_id: str,
        *,
        ctx: RequestContext | None = None,
    ) -> None:  # pragma: no cover - decorator provides implementation
        """Delete a user by ID."""
        ...
