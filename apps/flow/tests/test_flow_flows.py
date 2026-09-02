"""Tests for Flow flow endpoints (in-memory store)."""

from fastapi.testclient import TestClient

from zrun.flow.main import create_app


def _client() -> TestClient:
    return TestClient(create_app())


def test_create_and_patch_flow_partial_update() -> None:
    """PATCH updates only the fields sent; others are preserved."""
    client = _client()
    created = client.post("/flows", json={"name": "build"})
    assert created.status_code == 201
    flow_id = created.json()["id"]
    assert created.json()["status"] == "created"

    patched = client.patch(f"/flows/{flow_id}", json={"status": "active"})
    assert patched.status_code == 200
    body = patched.json()
    assert body["status"] == "active"
    # Unsent fields are preserved.
    assert body["name"] == "build"


def test_patch_missing_flow_returns_404() -> None:
    """PATCH on a non-existent flow must 404."""
    response = _client().patch("/flows/nope", json={"status": "active"})
    assert response.status_code == 404
