"""Tests for the Flow healthz endpoint."""

from fastapi.testclient import TestClient

from zrun.flow.main import create_app


def test_healthz_returns_ok() -> None:
    """GET /healthz must return 200 with status ok."""
    client = TestClient(create_app())
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
