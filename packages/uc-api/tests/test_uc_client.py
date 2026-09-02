"""Tests for the UC service client."""

from __future__ import annotations

import inspect
import json

import httpx2
import pytest
from zrun_test_utils import MockRouter
from zrun_test_utils.helpers import error_response, ok_response

from zrun.core.errors import ServiceNotFoundError
from zrun.core.http.context import RequestContext
from zrun.uc_api.client import UcServiceClient
from zrun.uc_api.models import UserCreate, UserResponse, UserUpdate

BASE_URL = "https://uc.test"


@pytest.fixture
def client(mock_router: MockRouter) -> UcServiceClient:
    return UcServiceClient(base_url=BASE_URL, max_retries=1, transport=mock_router)


@pytest.mark.asyncio
async def test_get_user_parses_response(client: UcServiceClient, mock_router: MockRouter) -> None:
    """Client should parse a successful response into UserResponse."""
    user_data = {
        "id": "user_1",
        "username": "alice",
        "email": "alice@example.com",
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    mock_router.get(f"{BASE_URL}/users/user_1").return_value = ok_response(user_data)

    result = await client.get_user("user_1")

    assert isinstance(result, UserResponse)
    assert result.id == "user_1"
    assert result.username == "alice"
    assert result.email == "alice@example.com"


@pytest.mark.asyncio
async def test_get_user_404_raises_not_found(
    client: UcServiceClient, mock_router: MockRouter
) -> None:
    """404 responses should map to ServiceNotFoundError."""
    mock_router.get(f"{BASE_URL}/users/nope").return_value = error_response("Not found", status=404)

    with pytest.raises(ServiceNotFoundError) as exc_info:
        await client.get_user("nope")

    assert exc_info.value.service_name == "uc"
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_user_by_username(client: UcServiceClient, mock_router: MockRouter) -> None:
    """get_user_by_username should pass the username as a query param."""
    user_data = {
        "id": "user_1",
        "username": "bob",
        "email": "bob@example.com",
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    route = mock_router.get(f"{BASE_URL}/users/by-username")
    route.return_value = ok_response(user_data)

    result = await client.get_user_by_username("bob")

    assert result.username == "bob"
    assert route.calls.last.request.url.params.get("username") == "bob"


@pytest.mark.asyncio
async def test_list_users(client: UcServiceClient, mock_router: MockRouter) -> None:
    """list_users should return a list of UserResponse."""
    users_data = [
        {
            "id": f"user_{i}",
            "username": f"user{i}",
            "email": f"user{i}@example.com",
            "status": "active",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        for i in range(2)
    ]
    mock_router.get(f"{BASE_URL}/users").return_value = ok_response(users_data)

    result = await client.list_users()

    assert len(result) == 2
    assert all(isinstance(u, UserResponse) for u in result)


@pytest.mark.asyncio
async def test_create_user(client: UcServiceClient, mock_router: MockRouter) -> None:
    """create_user should POST and parse the response (no retry for POST)."""
    user_data = {
        "id": "user_1",
        "username": "charlie",
        "email": "charlie@example.com",
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    mock_router.post(f"{BASE_URL}/users").return_value = ok_response(user_data, status=201)

    payload = UserCreate(username="charlie", email="charlie@example.com", password="secret123")
    result = await client.create_user(payload)

    assert result.username == "charlie"


@pytest.mark.asyncio
async def test_context_headers_propagated(client: UcServiceClient, mock_router: MockRouter) -> None:
    """RequestContext headers should be forwarded to the downstream service."""
    user_data = {
        "id": "user_1",
        "username": "dave",
        "email": "dave@example.com",
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    route = mock_router.get(f"{BASE_URL}/users/1")
    route.return_value = ok_response(user_data)

    ctx = RequestContext(auth_token="Bearer tok", request_id="req-abc")
    await client.get_user("1", ctx=ctx)

    assert route.called
    headers = route.calls.last.request.headers
    assert headers.get("Authorization") == "Bearer tok"
    assert headers.get("X-Request-ID") == "req-abc"


@pytest.mark.asyncio
async def test_delete_user_returns_none_on_204(
    client: UcServiceClient, mock_router: MockRouter
) -> None:
    """`-> None` delete on a 204 response must return None (no body parsing)."""
    mock_router.delete(f"{BASE_URL}/users/user_1").return_value = httpx2.Response(204)

    result = await client.delete_user("user_1")

    assert result is None


@pytest.mark.asyncio
async def test_update_user_uses_patch_with_partial_body(
    client: UcServiceClient, mock_router: MockRouter
) -> None:
    """Partial updates go over PATCH and only set fields are serialized."""
    route = mock_router.patch(f"{BASE_URL}/users/user_1")
    route.return_value = ok_response(
        {
            "id": "user_1",
            "username": "alice",
            "email": "new@example.com",
            "status": "active",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
        }
    )

    result = await client.update_user("user_1", UserUpdate(email="new@example.com"))

    request = route.calls.last.request
    assert request.method == "PATCH"
    assert json.loads(request.content) == {"email": "new@example.com"}
    assert result.email == "new@example.com"


def test_all_endpoints_have_valid_specs() -> None:
    """Every declared endpoint must carry a validated EndpointSpec.

    Fail-fast guard: decoration-time validation (path placeholders, body
    params, return annotations) runs at import, and this asserts every
    endpoint method actually went through a decorator.
    """
    for _name, func in inspect.getmembers(UcServiceClient, inspect.iscoroutinefunction):
        if func.__qualname__.startswith("UcServiceClient."):
            assert getattr(func, "__endpoint_spec__", None) is not None, (
                f"{func.__qualname__} is not decorated"
            )
