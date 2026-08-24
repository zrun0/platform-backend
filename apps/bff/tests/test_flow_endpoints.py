"""Integration tests for BFF flow endpoints (with mocked downstream)."""

from __future__ import annotations

import httpx
import respx
from fastapi.testclient import TestClient

from zrun.bff.main import create_app
from zrun.bff.settings import Settings

FLOW_URL = "http://flow-test:8001"
UC_URL = "http://uc-test:8002"


def _client() -> TestClient:
    settings = Settings(flow_api_base_url=FLOW_URL, uc_api_base_url=UC_URL)
    return TestClient(create_app(settings))


def test_list_flows_proxies_to_flow_service(respx_mock: respx.Router) -> None:
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
    respx_mock.get(f"{FLOW_URL}/flows").return_value = _ok(flow_data)

    with _client() as client:
        response = client.get("/flows")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "flow_1"
    assert data[0]["name"] == "demo"


def test_get_flow_returns_flow(respx_mock: respx.Router) -> None:
    """GET /flows/{id} should return the flow from the downstream service."""
    flow_data = {
        "id": "flow_42",
        "name": "answer",
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    respx_mock.get(f"{FLOW_URL}/flows/flow_42").return_value = _ok(flow_data)

    with _client() as client:
        response = client.get("/flows/flow_42")

    assert response.status_code == 200
    assert response.json()["name"] == "answer"


def test_get_flow_404_propagates(respx_mock: respx.Router) -> None:
    """Downstream 404 should come back as BFF 404 with structured error."""
    respx_mock.get(f"{FLOW_URL}/flows/nope").return_value = _not_found()

    with _client() as client:
        response = client.get("/flows/nope")

    assert response.status_code == 404
    body = response.json()
    assert body["error"] == "ServiceNotFoundError"
    assert body["service"] == "flow"


def test_get_flow_503_returns_502(respx_mock: respx.Router) -> None:
    """Downstream 5xx should come back as 502."""
    respx_mock.get(f"{FLOW_URL}/flows/1").return_value = _server_error()

    with _client() as client:
        response = client.get("/flows/1")

    assert response.status_code == 502
    body = response.json()
    assert body["error"] == "ServiceUnavailableError"
    assert body["service"] == "flow"


def test_request_id_propagated(respx_mock: respx.Router) -> None:
    """X-Request-ID should be forwarded to the downstream service."""
    flow_data = {
        "id": "flow_1",
        "name": "x",
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    route = respx_mock.get(f"{FLOW_URL}/flows/1")
    route.return_value = _ok(flow_data)

    with _client() as client:
        response = client.get("/flows/1", headers={"X-Request-ID": "test-req-42"})

    assert response.status_code == 200
    assert route.calls.last.request.headers.get("X-Request-ID") == "test-req-42"
    assert response.headers.get("X-Request-ID") == "test-req-42"


def test_request_id_generated_when_missing(respx_mock: respx.Router) -> None:
    """When X-Request-ID is absent, BFF generates one and forwards it downstream."""
    flow_data = {
        "id": "flow_1",
        "name": "x",
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    route = respx_mock.get(f"{FLOW_URL}/flows/1")
    route.return_value = _ok(flow_data)

    with _client() as client:
        response = client.get("/flows/1")

    assert response.status_code == 200
    # Response echoes the generated ID
    generated_id = response.headers.get("X-Request-ID")
    assert generated_id is not None
    assert len(generated_id) > 0
    # Downstream call received the same generated ID
    assert route.calls.last.request.headers.get("X-Request-ID") == generated_id


def test_create_flow(respx_mock: respx.Router) -> None:
    """POST /flows should proxy create to the flow service."""
    flow_data = {
        "id": "flow_1",
        "name": "new-flow",
        "status": "created",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    respx_mock.post(f"{FLOW_URL}/flows").return_value = _ok(flow_data, status=201)

    with _client() as client:
        response = client.post("/flows", json={"name": "new-flow", "description": "test"})

    assert response.status_code == 201
    assert response.json()["name"] == "new-flow"


def _ok(data: dict | list, *, status: int = 200) -> httpx.Response:
    return httpx.Response(status, json=data)


def _not_found() -> httpx.Response:
    return httpx.Response(404, json={"detail": "Not found"})


def _server_error() -> httpx.Response:
    return httpx.Response(503, json={"detail": "Service unavailable"})
