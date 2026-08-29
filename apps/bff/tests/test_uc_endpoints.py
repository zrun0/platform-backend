"""Integration tests for BFF UC endpoints (with mocked downstream)."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from zrun_test_utils import MockRouter
from zrun_test_utils.helpers import error_response, ok_response

from zrun.bff.main import AppClients, create_app
from zrun.bff.settings import Settings
from zrun.uc_api import UcServiceClient

UC_URL = "http://uc-test:8002"


@pytest.fixture
def uc_client(mock_router: MockRouter) -> TestClient:
    """Test client fixture for UC endpoints.

    Each test function that uses this fixture will get a fresh TestClient instance.
    """
    settings = Settings(uc_api_base_url=UC_URL)
    app = create_app(settings)

    # Manually initialize UC client for test environment
    # (TestClient doesn't trigger lifespan events)
    uc_client = UcServiceClient(
        base_url=settings.uc_api_base_url,
        timeout=settings.uc_timeout,
        max_connections=settings.max_connections,
        max_keepalive_connections=settings.max_keepalive_connections,
        transport=mock_router,
    )
    # Create a minimal flow client placeholder (not used in UC tests)
    from zrun.flow_api import FlowServiceClient

    flow_client = FlowServiceClient(
        base_url=settings.flow_api_base_url,
        timeout=settings.flow_timeout,
        max_connections=settings.max_connections,
        max_keepalive_connections=settings.max_keepalive_connections,
        transport=mock_router,
    )
    app.state.clients = AppClients(flow=flow_client, uc=uc_client)

    return TestClient(app)


def test_get_user_proxies_to_uc_service(uc_client: TestClient, mock_router: MockRouter) -> None:
    """GET /users/{id} should proxy to the UC service and return its response."""
    user_data = {
        "id": "user_1",
        "username": "alice",
        "email": "alice@example.com",
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    mock_router.get(f"{UC_URL}/users/user_1").return_value = ok_response(user_data)

    response = uc_client.get("/users/user_1")

    assert response.status_code == 200
    data: dict[str, Any] = response.json()
    assert data["id"] == "user_1"
    assert data["username"] == "alice"
    assert data["email"] == "alice@example.com"
    assert data["status"] == "active"


def test_get_user_by_username_proxies_to_uc_service(
    uc_client: TestClient, mock_router: MockRouter
) -> None:
    """GET /users/by-username should proxy to UC service and return response."""
    user_data = {
        "id": "user_42",
        "username": "bob",
        "email": "bob@example.com",
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    route = mock_router.get(f"{UC_URL}/users/by-username")
    route.return_value = ok_response(user_data)

    response = uc_client.get("/users/by-username/bob")

    assert response.status_code == 200
    data: dict[str, Any] = response.json()
    assert data["id"] == "user_42"
    assert data["username"] == "bob"
    assert data["email"] == "bob@example.com"
    # Verify the username was passed as query parameter
    assert route.calls.last.request.url.params.get("username") == "bob"


def test_get_user_404_propagates(uc_client: TestClient, mock_router: MockRouter) -> None:
    """Downstream 404 should come back as BFF 404 with structured error."""
    mock_router.get(f"{UC_URL}/users/nope").return_value = error_response("Not found", status=404)

    response = uc_client.get("/users/nope")

    assert response.status_code == 404
    body: dict[str, Any] = response.json()
    assert body["error"] == "ServiceNotFoundError"
    assert body["service"] == "uc"


def test_get_user_503_returns_502(uc_client: TestClient, mock_router: MockRouter) -> None:
    """Downstream 5xx should come back as 502."""
    mock_router.get(f"{UC_URL}/users/1").return_value = error_response(
        "Service unavailable", status=503
    )

    response = uc_client.get("/users/1")

    assert response.status_code == 502
    body: dict[str, Any] = response.json()
    assert body["error"] == "ServiceUnavailableError"
    assert body["service"] == "uc"


def test_request_id_propagated_to_uc(uc_client: TestClient, mock_router: MockRouter) -> None:
    """X-Request-ID should be forwarded to the UC service."""
    user_data = {
        "id": "user_1",
        "username": "x",
        "email": "x@example.com",
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    route = mock_router.get(f"{UC_URL}/users/1")
    route.return_value = ok_response(user_data)

    response = uc_client.get("/users/1", headers={"X-Request-ID": "test-req-42"})

    assert response.status_code == 200
    assert route.calls.last.request.headers.get("X-Request-ID") == "test-req-42"
    assert response.headers.get("X-Request-ID") == "test-req-42"


def test_request_id_generated_when_missing_for_uc(
    uc_client: TestClient, mock_router: MockRouter
) -> None:
    """When X-Request-ID is absent, BFF generates one and forwards it to UC service."""
    user_data = {
        "id": "user_1",
        "username": "x",
        "email": "x@example.com",
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    route = mock_router.get(f"{UC_URL}/users/1")
    route.return_value = ok_response(user_data)

    response = uc_client.get("/users/1")

    assert response.status_code == 200
    # Response echoes the generated ID
    generated_id: str | None = response.headers.get("X-Request-ID")
    assert generated_id is not None
    assert len(generated_id) > 0
    # Downstream call received the same generated ID
    assert route.calls.last.request.headers.get("X-Request-ID") == generated_id


def test_get_user_by_username_404_propagates(
    uc_client: TestClient, mock_router: MockRouter
) -> None:
    """Downstream 404 for username lookup should come back as BFF 404."""
    route = mock_router.get(f"{UC_URL}/users/by-username")
    route.return_value = error_response("Not found", status=404)

    response = uc_client.get("/users/by-username/nonexistent")

    assert response.status_code == 404
    body: dict[str, Any] = response.json()
    assert body["error"] == "ServiceNotFoundError"
    assert body["service"] == "uc"
    # Verify the username was passed as query parameter
    assert route.calls.last.request.url.params.get("username") == "nonexistent"
