"""Tests for RequestContext trust-boundary behavior."""

from __future__ import annotations

from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from zrun.core.http.context import RequestContext
from zrun.core.middleware import RequestIDMiddleware


def _app(*, with_middleware: bool) -> TestClient:
    app = FastAPI()

    @app.get("/ctx")
    def ctx(request: Request) -> dict[str, str]:
        context = RequestContext.from_request(request, user_id="derived-user")
        return context.to_headers()

    if with_middleware:
        app.add_middleware(RequestIDMiddleware)
    return TestClient(app)


def test_from_request_ignores_inbound_user_and_trace_headers() -> None:
    """Client-supplied X-User-ID / X-Trace-ID must never propagate."""
    with _app(with_middleware=True) as client:
        response = client.get(
            "/ctx",
            headers={"X-User-ID": "attacker", "X-Trace-ID": "evil-trace"},
        )

    headers = response.json()
    assert headers["X-User-ID"] == "derived-user"
    assert headers["X-Trace-ID"] != "evil-trace"
    UUID(headers["X-Trace-ID"])


def test_from_request_reads_state_request_id() -> None:
    """With middleware present, the validated ID flows via request.state."""
    with _app(with_middleware=True) as client:
        response = client.get("/ctx", headers={"X-Request-ID": "abc-123"})

    assert response.json()["X-Request-ID"] == "abc-123"


def test_from_request_ignores_raw_header_without_middleware() -> None:
    """Without middleware the raw inbound header is not trusted either."""
    with _app(with_middleware=False) as client:
        response = client.get("/ctx", headers={"X-Request-ID": "abc-123"})

    request_id = response.json()["X-Request-ID"]
    assert request_id != "abc-123"
    UUID(request_id)


def test_from_request_propagates_auth_token() -> None:
    """The Authorization credential is still relayed downstream."""
    with _app(with_middleware=True) as client:
        response = client.get("/ctx", headers={"Authorization": "Bearer tok"})

    assert response.json()["Authorization"] == "Bearer tok"


def test_to_headers_serializes_all_fields() -> None:
    """Directly-constructed contexts serialize every field (outbound contract)."""
    ctx = RequestContext(
        auth_token="Bearer t",
        request_id="req-1",
        trace_id="trace-1",
        user_id="user-1",
    )

    assert ctx.to_headers() == {
        "Authorization": "Bearer t",
        "X-Request-ID": "req-1",
        "X-Trace-ID": "trace-1",
        "X-User-ID": "user-1",
    }
