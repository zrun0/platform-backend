"""Tests for the BFF healthz endpoint."""

import pytest
from fastapi.testclient import TestClient

from zrun.bff.main import create_app


@pytest.fixture
def bff_client() -> TestClient:
    """Test client fixture for BFF health endpoints."""
    return TestClient(create_app())


def test_healthz_returns_ok(bff_client: TestClient) -> None:
    """GET /healthz must return 200 with status ok."""
    response = bff_client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
