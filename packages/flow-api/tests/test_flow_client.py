"""Tests for the Flow service client."""

from __future__ import annotations

import inspect
from datetime import UTC, datetime

import httpx2
import pytest
from zrun_test_utils import MockRouter
from zrun_test_utils.helpers import ok_response

from zrun.core.errors import (
    ServiceNotFoundError,
    ServiceUnavailableError,
)
from zrun.core.http.context import RequestContext
from zrun.flow_api.client import FlowServiceClient
from zrun.flow_api.models import FlowCreate, FlowResponse

BASE_URL = "https://flow.test"


@pytest.fixture
def client(mock_router: MockRouter) -> FlowServiceClient:
    return FlowServiceClient(base_url=BASE_URL, max_retries=1, transport=mock_router)


@pytest.mark.asyncio
async def test_get_flow_parses_response(client: FlowServiceClient, mock_router: MockRouter) -> None:
    """Client should parse a successful response into FlowResponse."""
    flow_data = {
        "id": "flow_1",
        "name": "test-flow",
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    mock_router.get(f"{BASE_URL}/flows/flow_1").return_value = ok_response(flow_data)

    result = await client.get_flow("flow_1")

    assert isinstance(result, FlowResponse)
    assert result.id == "flow_1"
    assert result.name == "test-flow"
    assert result.status == "active"


@pytest.mark.asyncio
async def test_get_flow_404_raises_not_found(
    client: FlowServiceClient, mock_router: MockRouter
) -> None:
    """404 responses should map to ServiceNotFoundError."""
    mock_router.get(f"{BASE_URL}/flows/flow_999").return_value = ok_response(
        {"detail": "Not found"}, status=404
    )

    with pytest.raises(ServiceNotFoundError) as exc_info:
        await client.get_flow("flow_999")

    assert exc_info.value.service_name == "flow"
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_flow_503_raises_unavailable(
    client: FlowServiceClient, mock_router: MockRouter
) -> None:
    """503 responses should map to ServiceUnavailableError (with retry disabled)."""
    # With max_retries=0 there is no retry, so it fails immediately.
    client = FlowServiceClient(base_url=BASE_URL, max_retries=0, transport=mock_router)
    mock_router.get(f"{BASE_URL}/flows/1").return_value = ok_response(
        {"detail": "down"}, status=503
    )

    with pytest.raises(ServiceUnavailableError) as exc_info:
        await client.get_flow("1")

    assert exc_info.value.service_name == "flow"


@pytest.mark.asyncio
async def test_list_flows(client: FlowServiceClient, mock_router: MockRouter) -> None:
    """list_flows should parse a list of FlowResponse objects."""
    flows_data = [
        {
            "id": f"flow_{i}",
            "name": f"flow-{i}",
            "status": "active",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }
        for i in range(3)
    ]
    mock_router.get(f"{BASE_URL}/flows").return_value = ok_response(flows_data)

    result = await client.list_flows()

    assert len(result) == 3
    assert all(isinstance(f, FlowResponse) for f in result)
    assert result[0].id == "flow_0"


@pytest.mark.asyncio
async def test_create_flow(client: FlowServiceClient, mock_router: MockRouter) -> None:
    """create_flow should POST and parse the response."""
    now = datetime.now(UTC).isoformat()
    flow_data = {
        "id": "flow_1",
        "name": "new-flow",
        "status": "created",
        "created_at": now,
        "updated_at": now,
    }
    mock_router.post(f"{BASE_URL}/flows").return_value = ok_response(flow_data, status=201)

    payload = FlowCreate(name="new-flow", description="test")
    result = await client.create_flow(payload)

    assert result.name == "new-flow"
    assert result.status == "created"


@pytest.mark.asyncio
async def test_context_headers_propagated(
    client: FlowServiceClient, mock_router: MockRouter
) -> None:
    """RequestContext headers should be forwarded to the downstream service."""
    flow_data = {
        "id": "flow_1",
        "name": "test",
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    route = mock_router.get(f"{BASE_URL}/flows/1")
    route.return_value = ok_response(flow_data)

    ctx = RequestContext(
        auth_token="Bearer test-token",
        request_id="req-123",
        trace_id="trace-456",
        user_id="user-1",
    )
    await client.get_flow("1", ctx=ctx)

    assert route.called
    headers = route.calls.last.request.headers
    assert headers.get("Authorization") == "Bearer test-token"
    assert headers.get("X-Request-ID") == "req-123"
    assert headers.get("X-Trace-ID") == "trace-456"
    assert headers.get("X-User-ID") == "user-1"


@pytest.mark.asyncio
async def test_delete_flow_returns_none_on_204(
    client: FlowServiceClient, mock_router: MockRouter
) -> None:
    """`-> None` delete on a 204 response must return None (no body parsing)."""
    mock_router.delete(f"{BASE_URL}/flows/flow_1").return_value = httpx2.Response(204)

    result = await client.delete_flow("flow_1")

    assert result is None


def test_all_endpoints_have_valid_specs() -> None:
    """Every declared endpoint must carry a validated EndpointSpec."""
    for _name, func in inspect.getmembers(FlowServiceClient, inspect.iscoroutinefunction):
        if func.__qualname__.startswith("FlowServiceClient."):
            assert getattr(func, "__endpoint_spec__", None) is not None, (
                f"{func.__qualname__} is not decorated"
            )
