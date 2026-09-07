"""Tests for RequestIDMiddleware request/trace ID handling."""

from __future__ import annotations

from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from lesoon.core.middleware import RequestIDMiddleware, sanitize_header_token


def _echo_app(*, trust_inbound_trace: bool = False) -> TestClient:
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware, trust_inbound_trace=trust_inbound_trace)

    @app.get("/echo")
    def echo(request: Request) -> dict[str, str]:
        return {
            "request_id": getattr(request.state, "request_id", ""),
            "trace_id": getattr(request.state, "trace_id", ""),
        }

    return TestClient(app)


def test_valid_request_id_preserved() -> None:
    """A printable single-line token passes through unchanged."""
    with _echo_app() as client:
        response = client.get("/echo", headers={"X-Request-ID": "abc-DEF_123.~x"})

    assert response.json()["request_id"] == "abc-DEF_123.~x"
    assert response.headers["X-Request-ID"] == "abc-DEF_123.~x"


def test_real_world_request_id_formats_preserved() -> None:
    """base64 (with padding) and colon-separated edge IDs pass through."""
    for good in ("YGBg+2==", "edge-1:57f6a2", "a*b#c$d%e&f'g!h"):
        with _echo_app() as client:
            response = client.get("/echo", headers={"X-Request-ID": good})

        assert response.json()["request_id"] == good
        assert response.headers["X-Request-ID"] == good


def test_invalid_request_id_replaced() -> None:
    """Spaces, control characters, non-tokens, and oversized IDs are replaced."""
    for bad in ("bad request id", "abc\ndef", "x" * 513, "id;rm -rf", "id,with,commas"):
        with _echo_app() as client:
            response = client.get("/echo", headers={"X-Request-ID": bad})

        request_id = response.json()["request_id"]
        assert request_id != bad
        UUID(request_id)


def test_missing_request_id_generated() -> None:
    """No inbound header means a fresh UUID4."""
    with _echo_app() as client:
        response = client.get("/echo")

    UUID(response.json()["request_id"])


def test_edge_mints_fresh_trace_id() -> None:
    """Untrusted ingress (default): inbound traces are never continued."""
    with _echo_app() as client:
        response = client.get("/echo", headers={"X-Trace-ID": "evil-trace"})

    trace_id = response.json()["trace_id"]
    assert trace_id != "evil-trace"
    UUID(trace_id)


def test_trusted_ingress_continues_valid_trace_id() -> None:
    """Internal services continue a validated inbound trace so hops join."""
    with _echo_app(trust_inbound_trace=True) as client:
        response = client.get("/echo", headers={"X-Trace-ID": "trace-1abc.~x"})

    assert response.json()["trace_id"] == "trace-1abc.~x"


def test_trusted_ingress_replaces_invalid_trace_id() -> None:
    """Trusted ingress still sanitizes: garbage traces become fresh UUIDs."""
    with _echo_app(trust_inbound_trace=True) as client:
        response = client.get("/echo", headers={"X-Trace-ID": "evil trace\ninjected"})

    trace_id = response.json()["trace_id"]
    assert trace_id != "evil trace\ninjected"
    UUID(trace_id)


def test_sanitize_header_token_unit() -> None:
    """Direct checks of the sanitizer's boundary behavior."""
    assert sanitize_header_token("valid-id.1_~") == "valid-id.1_~"
    assert sanitize_header_token("YGBg+2==") == "YGBg+2=="
    assert sanitize_header_token(None) != ""
    UUID(sanitize_header_token("injection\tattempt"))
