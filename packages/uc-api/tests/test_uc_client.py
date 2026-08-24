"""Tests for the UC service client."""

from __future__ import annotations

import httpx
import pytest
import respx

from zrun.core.errors import ServiceNotFoundError
from zrun.core.http.context import RequestContext
from zrun.uc_api.client import UcServiceClient
from zrun.uc_api.models import UserCreate, UserResponse

BASE_URL = "https://uc.test"


@pytest.fixture
def client() -> UcServiceClient:
    return UcServiceClient(base_url=BASE_URL, max_retries=1)


@pytest.mark.asyncio
async def test_get_user_parses_response(client: UcServiceClient, respx_mock: respx.Router) -> None:
    """Client should parse a successful response into UserResponse."""
    user_data = {
        "id": "user_1",
        "username": "alice",
        "email": "alice@example.com",
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    respx_mock.get(f"{BASE_URL}/users/user_1").return_value = _ok(user_data)

    result = await client.get_user("user_1")

    assert isinstance(result, UserResponse)
    assert result.id == "user_1"
    assert result.username == "alice"
    assert result.email == "alice@example.com"


@pytest.mark.asyncio
async def test_get_user_404_raises_not_found(
    client: UcServiceClient, respx_mock: respx.Router
) -> None:
    """404 responses should map to ServiceNotFoundError."""
    respx_mock.get(f"{BASE_URL}/users/nope").return_value = _not_found()

    with pytest.raises(ServiceNotFoundError) as exc_info:
        await client.get_user("nope")

    assert exc_info.value.service_name == "uc"
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_user_by_username(client: UcServiceClient, respx_mock: respx.Router) -> None:
    """get_user_by_username should pass the username as a query param."""
    user_data = {
        "id": "user_1",
        "username": "bob",
        "email": "bob@example.com",
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    route = respx_mock.get(f"{BASE_URL}/users/by-username")
    route.return_value = _ok(user_data)

    result = await client.get_user_by_username("bob")

    assert result.username == "bob"
    assert route.calls.last.request.url.params.get("username") == "bob"


@pytest.mark.asyncio
async def test_list_users(client: UcServiceClient, respx_mock: respx.Router) -> None:
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
    respx_mock.get(f"{BASE_URL}/users").return_value = _ok(users_data)

    result = await client.list_users()

    assert len(result) == 2
    assert all(isinstance(u, UserResponse) for u in result)


@pytest.mark.asyncio
async def test_create_user(client: UcServiceClient, respx_mock: respx.Router) -> None:
    """create_user should POST and parse the response (no retry for POST)."""
    user_data = {
        "id": "user_1",
        "username": "charlie",
        "email": "charlie@example.com",
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    respx_mock.post(f"{BASE_URL}/users").return_value = _ok(user_data, status=201)

    payload = UserCreate(username="charlie", email="charlie@example.com", password="secret123")
    result = await client.create_user(payload)

    assert result.username == "charlie"


@pytest.mark.asyncio
async def test_context_headers_propagated(
    client: UcServiceClient, respx_mock: respx.Router
) -> None:
    """RequestContext headers should be forwarded to the downstream service."""
    user_data = {
        "id": "user_1",
        "username": "dave",
        "email": "dave@example.com",
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    route = respx_mock.get(f"{BASE_URL}/users/1")
    route.return_value = _ok(user_data)

    ctx = RequestContext(auth_token="Bearer tok", request_id="req-abc")
    await client.get_user("1", ctx=ctx)

    assert route.called
    headers = route.calls.last.request.headers
    assert headers.get("Authorization") == "Bearer tok"
    assert headers.get("X-Request-ID") == "req-abc"


def _ok(data: dict | list, *, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json=data)


def _not_found() -> httpx.Response:
    return httpx.Response(404, json={"detail": "Not found"})
