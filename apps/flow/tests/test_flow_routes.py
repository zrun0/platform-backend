"""Tests for Flow routes (IDs, update null semantics, concurrency)."""

from __future__ import annotations

import threading
from typing import Any

import pytest
from fastapi.testclient import TestClient

from lesoon.flow.api import routes as flow_routes
from lesoon.flow.main import create_app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Fresh app with an empty flow store per test."""
    monkeypatch.setattr(flow_routes, "_FLOWS", {})
    return TestClient(create_app())


def _make_flow(client: TestClient, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"name": "demo"}
    payload.update(overrides)
    response = client.post("/flows", json=payload)
    assert response.status_code == 201
    flow: dict[str, Any] = response.json()
    return flow


def test_create_flow_persists_description(client: TestClient) -> None:
    """The description sent on create is stored and echoed back."""
    flow = _make_flow(client, description="mapping doc")

    assert flow["description"] == "mapping doc"
    got = client.get(f"/flows/{flow['id']}")
    assert got.json()["description"] == "mapping doc"


def test_create_flow_generates_unique_uuid_ids(client: TestClient) -> None:
    """IDs are UUID-based: no length-derived collisions across deletes."""
    first = _make_flow(client)
    client.delete(f"/flows/{first['id']}")
    second = _make_flow(client)

    assert second["id"] != first["id"]
    assert second["id"].startswith("flow_")


def test_update_null_description_clears_it(client: TestClient) -> None:
    """Explicit null on the nullable description clears the stored value."""
    flow = _make_flow(client, description="secret detail")

    response = client.patch(f"/flows/{flow['id']}", json={"description": None})

    assert response.status_code == 200
    assert response.json()["description"] is None
    assert client.get(f"/flows/{flow['id']}").json()["description"] is None


def test_update_null_name_is_ignored(client: TestClient) -> None:
    """Explicit null on required name is treated as omitted, not a clear."""
    flow = _make_flow(client, name="original")

    response = client.patch(f"/flows/{flow['id']}", json={"name": None})

    assert response.status_code == 200
    assert response.json()["name"] == "original"


def test_update_partial_fields_only(client: TestClient) -> None:
    """Unset fields keep their previous values; updated_at advances."""
    flow = _make_flow(client, description="keep me")

    response = client.patch(f"/flows/{flow['id']}", json={"status": "active"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "active"
    assert body["description"] == "keep me"
    assert body["updated_at"] > flow["updated_at"]


def test_concurrent_deletes_never_500(client: TestClient) -> None:
    """Racing deletes of the same flow: one 204, rest 404, never a KeyError 500."""
    flow = _make_flow(client)
    results: list[int] = []
    barrier = threading.Barrier(4)

    def delete() -> None:
        barrier.wait()
        results.append(client.delete(f"/flows/{flow['id']}").status_code)

    threads = [threading.Thread(target=delete) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(results) == [204, 404, 404, 404]


def test_delete_racing_update_cannot_resurrect(client: TestClient) -> None:
    """After a delete returns 204, a racing update must not revive the row."""
    flow = _make_flow(client)
    outcomes: list[bool] = []
    barrier = threading.Barrier(2)

    def delete() -> None:
        barrier.wait()
        outcomes.append(client.delete(f"/flows/{flow['id']}").status_code == 204)

    def update() -> None:
        barrier.wait()
        # 200 (updated before the delete) or 404 (deleted first): both fine,
        # as long as the row is gone once both handlers have returned.
        ok = client.patch(f"/flows/{flow['id']}", json={"name": "x"}).status_code in (200, 404)
        outcomes.append(ok)

    threads = [threading.Thread(target=delete), threading.Thread(target=update)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert all(outcomes)
    assert client.get(f"/flows/{flow['id']}").status_code == 404
