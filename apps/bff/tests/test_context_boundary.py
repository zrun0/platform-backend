"""Integration tests for the BFF ingress trust boundary."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID

import httpx2
from fastapi.testclient import TestClient
from lesoon_test_utils import MockRouter
from lesoon_test_utils.helpers import ok_response

from lesoon.bff.settings import Settings

FLOW_URL = "http://flow-test:8002"


def _flow_payload() -> dict[str, Any]:
    return {
        "id": "flow_1",
        "name": "x",
        "status": "active",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }


def test_inbound_user_id_not_forwarded(
    make_bff_client: Callable[[Settings], TestClient], mock_router: MockRouter
) -> None:
    """A client-supplied X-User-ID must be replaced by the derived identity."""
    route = mock_router.get(f"{FLOW_URL}/flows/1")
    route.return_value = ok_response(_flow_payload())

    client = make_bff_client(Settings(flow_api_base_url=FLOW_URL))
    response = client.get("/flows/1", headers={"X-User-ID": "attacker-evil"})

    assert response.status_code == 200
    forwarded = route.calls.last.request.headers.get("X-User-ID")
    # Placeholder auth derives "anonymous" today; the attacker value must not win.
    assert forwarded == "anonymous"


def test_inbound_trace_id_not_forwarded(
    make_bff_client: Callable[[Settings], TestClient], mock_router: MockRouter
) -> None:
    """A client-supplied X-Trace-ID is dropped; a fresh trace ID is generated."""
    route = mock_router.get(f"{FLOW_URL}/flows/1")
    route.return_value = ok_response(_flow_payload())

    client = make_bff_client(Settings(flow_api_base_url=FLOW_URL))
    response = client.get("/flows/1", headers={"X-Trace-ID": "evil-trace"})

    assert response.status_code == 200
    forwarded = route.calls.last.request.headers.get("X-Trace-ID")
    assert forwarded is not None
    assert forwarded != "evil-trace"
    UUID(forwarded)


def test_invalid_request_id_regenerated_at_boundary(
    make_bff_client: Callable[[Settings], TestClient], mock_router: MockRouter
) -> None:
    """An invalid X-Request-ID is regenerated once and used consistently."""
    route = mock_router.get(f"{FLOW_URL}/flows/1")
    route.return_value = ok_response(_flow_payload())

    client = make_bff_client(Settings(flow_api_base_url=FLOW_URL))
    response = client.get("/flows/1", headers={"X-Request-ID": "bad request id"})

    assert response.status_code == 200
    echoed = response.headers.get("X-Request-ID")
    assert echoed is not None
    assert echoed != "bad request id"
    UUID(echoed)
    assert route.calls.last.request.headers.get("X-Request-ID") == echoed


def test_unreadable_downstream_body_is_distinguishable_502(
    make_bff_client: Callable[[Settings], TestClient], mock_router: MockRouter
) -> None:
    """An unreadable downstream body is 502 with a consistent error contract."""
    route = mock_router.get(f"{FLOW_URL}/flows/1")
    route.return_value = httpx2.Response(200, text="not-json")

    client = make_bff_client(Settings(flow_api_base_url=FLOW_URL))
    response = client.get("/flows/1")

    assert response.status_code == 502
    body = response.json()
    assert body["error"] == "ServiceResponseError"
    assert body["service"] == "flow"
    # Invariant kept by every error type: body status_code == HTTP status.
    assert body["status_code"] == 502
