"""Abstract protocol defining the UC service API interface.

Both the real HTTP client and test fakes/mocks implement this protocol,
enabling dependency substitution without inheritance coupling.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from zrun.core.http.context import RequestContext
    from zrun.uc_api.models import UserCreate, UserResponse, UserUpdate


class UcApi(Protocol):
    """Abstract interface for the UC (User Center) service API."""

    async def get_user(
        self,
        user_id: str,
        *,
        ctx: RequestContext | None = None,
    ) -> UserResponse:
        """Retrieve a single user by ID."""
        ...

    async def get_user_by_username(
        self,
        username: str,
        *,
        ctx: RequestContext | None = None,
    ) -> UserResponse:
        """Retrieve a user by username."""
        ...

    async def list_users(
        self,
        *,
        ctx: RequestContext | None = None,
    ) -> list[UserResponse]:
        """List all users."""
        ...

    async def create_user(
        self,
        payload: UserCreate,
        *,
        ctx: RequestContext | None = None,
    ) -> UserResponse:
        """Create a new user."""
        ...

    async def update_user(
        self,
        user_id: str,
        payload: UserUpdate,
        *,
        ctx: RequestContext | None = None,
    ) -> UserResponse:
        """Update an existing user."""
        ...

    async def delete_user(
        self,
        user_id: str,
        *,
        ctx: RequestContext | None = None,
    ) -> None:
        """Delete a user by ID."""
        ...
