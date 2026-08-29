"""Integration tests for BFF flow endpoints (with mocked downstream)."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from zrun_test_utils import MockRouter
from zrun_test_utils.helpers import error_response, ok_response

from zrun.bff.main import AppClients, create_app
from zrun.bff.settings import Settings
from zrun.flow_api import FlowServiceClient

FLOW_URL = "http://flow-test:8001"


@pytest.fixture
def flow_client(mock_router: MockRouter) -> TestClient:
    """Test client fixture for flow endpoints.

    Each test function that uses this fixture will get a fresh TestClient instance.
    """
    settings = Settings(flow_api_base_url=FLOW_URL)
    app = create_app(settings)

    # Manually initialize flow client for test environment
    # (TestClient doesn't trigger lifespan events)
    flow_client = FlowServiceClient(
        base_url=settings.flow_api_base_url,
        timeout=settings.flow_timeout,
        max_connections=settings.max_connections,
        max_keepalive_connections=settings.max_keepalive_connections,
        transport=mock_router,
    )
    # Create a minimal UC client placeholder (not used in flow tests)
    from zrun.uc_api import UcServiceClient

    uc_client = UcServiceClient(
        base_url=settings.uc_api_base_url,
        timeout=settings.uc_timeout,
        max_connections=settings.max_connections,
        max_keepalive_connections=settings.max_keepalive_connections,
        transport=mock_router,
    )
    app.state.clients = AppClients(flow=flow_client, uc=uc_client)

    return TestClient(app)


def test_list_flows_proxies_to_flow_service(
    flow_client: TestClient, mock_router: MockRouter
) -> None:
    """GET /flows should proxy to the flow service and return its response."""
    flow_data = [
        {
            "id": "flow_1",
            "name": "demo",
            "status": "active",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        },
    ]
    mock_router.get(f"{FLOW_URL}/flows").return_value = ok_response(flow_data)

    response = flow_client.get("/flows")

    assert response.status_code == 200
    data: list[dict[str, Any]] = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "flow_1"
    assert data[0]["name"] == "demo"


def test_get_flow_returns_flow(flow_client: TestClient, mock_router: MockRouter) -> None:
    """GET /flows/{id} should return the flow from the downstream service."""
    flow_data = {
        "id": "flow_42",
        "name": "answer",
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    mock_router.get(f"{FLOW_URL}/flows/flow_42").return_value = ok_response(flow_data)

    response = flow_client.get("/flows/flow_42")

    assert response.status_code == 200
    assert response.json()["name"] == "answer"


def test_get_flow_404_propagates(flow_client: TestClient, mock_router: MockRouter) -> None:
    """Downstream 404 should come back as BFF 404 with structured error."""
    mock_router.get(f"{FLOW_URL}/flows/nope").return_value = error_response("Not found", status=404)

    response = flow_client.get("/flows/nope")

    assert response.status_code == 404
    body: dict[str, Any] = response.json()
    assert body["error"] == "ServiceNotFoundError"
    assert body["service"] == "flow"


def test_get_flow_503_returns_502(flow_client: TestClient, mock_router: MockRouter) -> None:
    """Downstream 5xx should come back as 502."""
    mock_router.get(f"{FLOW_URL}/flows/1").return_value = error_response(
        "Service unavailable", status=503
    )

    response = flow_client.get("/flows/1")

    assert response.status_code == 502
    body: dict[str, Any] = response.json()
    assert body["error"] == "ServiceUnavailableError"
    assert body["service"] == "flow"


def test_request_id_propagated(flow_client: TestClient, mock_router: MockRouter) -> None:
    """X-Request-ID should be forwarded to the downstream service."""
    flow_data = {
        "id": "flow_1",
        "name": "x",
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    route = mock_router.get(f"{FLOW_URL}/flows/1")
    route.return_value = ok_response(flow_data)

    response = flow_client.get("/flows/1", headers={"X-Request-ID": "test-req-42"})

    assert response.status_code == 200
    assert route.calls.last.request.headers.get("X-Request-ID") == "test-req-42"
    assert response.headers.get("X-Request-ID") == "test-req-42"


def test_request_id_generated_when_missing(
    flow_client: TestClient, mock_router: MockRouter
) -> None:
    """When X-Request-ID is absent, BFF generates one and forwards it downstream."""
    flow_data = {
        "id": "flow_1",
        "name": "x",
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    route = mock_router.get(f"{FLOW_URL}/flows/1")
    route.return_value = ok_response(flow_data)

    response = flow_client.get("/flows/1")

    assert response.status_code == 200
    # Response echoes the generated ID
    generated_id: str | None = response.headers.get("X-Request-ID")
    assert generated_id is not None
    assert len(generated_id) > 0
    # Downstream call received the same generated ID
    assert route.calls.last.request.headers.get("X-Request-ID") == generated_id


def test_create_flow(flow_client: TestClient, mock_router: MockRouter) -> None:
    """POST /flows should proxy create to the flow service."""
    flow_data = {
        "id": "flow_1",
        "name": "new-flow",
        "status": "created",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    mock_router.post(f"{FLOW_URL}/flows").return_value = ok_response(flow_data, status=201)

    response = flow_client.post("/flows", json={"name": "new-flow", "description": "test"})

    assert response.status_code == 201
    assert response.json()["name"] == "new-flow"
