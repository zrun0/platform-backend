"""Tests for the Flow service client."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import respx
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
def client() -> FlowServiceClient:
    return FlowServiceClient(base_url=BASE_URL, max_retries=1)


@pytest.mark.asyncio
async def test_get_flow_parses_response(
    client: FlowServiceClient, respx_mock: respx.Router
) -> None:
    """Client should parse a successful response into FlowResponse."""
    flow_data = {
        "id": "flow_1",
        "name": "test-flow",
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    respx_mock.get(f"{BASE_URL}/flows/flow_1").return_value = ok_response(flow_data)

    result = await client.get_flow("flow_1")

    assert isinstance(result, FlowResponse)
    assert result.id == "flow_1"
    assert result.name == "test-flow"
    assert result.status == "active"


@pytest.mark.asyncio
async def test_get_flow_404_raises_not_found(
    client: FlowServiceClient, respx_mock: respx.Router
) -> None:
    """404 responses should map to ServiceNotFoundError."""
    respx_mock.get(f"{BASE_URL}/flows/flow_999").return_value = ok_response(
        {"detail": "Not found"}, status=404
    )

    with pytest.raises(ServiceNotFoundError) as exc_info:
        await client.get_flow("flow_999")

    assert exc_info.value.service_name == "flow"
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_flow_503_raises_unavailable(
    client: FlowServiceClient, respx_mock: respx.Router
) -> None:
    """503 responses should map to ServiceUnavailableError (with retry disabled)."""
    # With max_retries=1 there is no retry, so it fails immediately.
    client = FlowServiceClient(base_url=BASE_URL, max_retries=0)
    respx_mock.get(f"{BASE_URL}/flows/1").return_value = ok_response({"detail": "down"}, status=503)

    with pytest.raises(ServiceUnavailableError) as exc_info:
        await client.get_flow("1")

    assert exc_info.value.service_name == "flow"


@pytest.mark.asyncio
async def test_list_flows(client: FlowServiceClient, respx_mock: respx.Router) -> None:
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
    respx_mock.get(f"{BASE_URL}/flows").return_value = ok_response(flows_data)

    result = await client.list_flows()

    assert len(result) == 3
    assert all(isinstance(f, FlowResponse) for f in result)
    assert result[0].id == "flow_0"


@pytest.mark.asyncio
async def test_create_flow(client: FlowServiceClient, respx_mock: respx.Router) -> None:
    """create_flow should POST and parse the response."""
    now = datetime.now(UTC).isoformat()
    flow_data = {
        "id": "flow_1",
        "name": "new-flow",
        "status": "created",
        "created_at": now,
        "updated_at": now,
    }
    respx_mock.post(f"{BASE_URL}/flows").return_value = ok_response(flow_data, status=201)

    payload = FlowCreate(name="new-flow", description="test")
    result = await client.create_flow(payload)

    assert result.name == "new-flow"
    assert result.status == "created"


@pytest.mark.asyncio
async def test_context_headers_propagated(
    client: FlowServiceClient, respx_mock: respx.Router
) -> None:
    """RequestContext headers should be forwarded to the downstream service."""
    flow_data = {
        "id": "flow_1",
        "name": "test",
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    route = respx_mock.get(f"{BASE_URL}/flows/1")
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
