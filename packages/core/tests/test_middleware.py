"""Tests for RequestIDMiddleware validation."""

from __future__ import annotations

from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from zrun.core.middleware import RequestIDMiddleware, sanitize_request_id


def _echo_app() -> TestClient:
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    @app.get("/echo")
    def echo(request: Request) -> dict[str, str]:
        return {"request_id": getattr(request.state, "request_id", "")}

    return TestClient(app)


def test_valid_request_id_preserved() -> None:
    """A conservative unreserved-character token passes through unchanged."""
    with _echo_app() as client:
        response = client.get("/echo", headers={"X-Request-ID": "abc-DEF_123.~x"})

    assert response.json()["request_id"] == "abc-DEF_123.~x"
    assert response.headers["X-Request-ID"] == "abc-DEF_123.~x"


def test_invalid_request_id_replaced() -> None:
    """Spaces, control characters, and oversized IDs are replaced."""
    for bad in ("bad request id", "abc\ndef", "x" * 129, "id;rm -rf"):
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


def test_sanitize_request_id_unit() -> None:
    """Direct checks of the sanitizer's boundary behavior."""
    assert sanitize_request_id("valid-id.1_~") == "valid-id.1_~"
    assert sanitize_request_id(None) != ""
    UUID(sanitize_request_id("injection\tattempt"))
