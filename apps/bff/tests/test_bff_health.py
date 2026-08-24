"""Tests for the BFF healthz endpoint."""

from fastapi.testclient import TestClient

from zrun.bff.main import create_app


def test_healthz_returns_ok() -> None:
    """GET /healthz must return 200 with status ok."""
    with TestClient(create_app()) as client:
        response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
