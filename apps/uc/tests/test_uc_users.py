"""Tests for UC user routes (store semantics, renames, concurrency)."""

from __future__ import annotations

import threading
from typing import Any

import pytest
from fastapi.testclient import TestClient

from zrun.uc.api import routes as uc_routes
from zrun.uc.main import create_app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Fresh app with an empty user store per test."""
    monkeypatch.setattr(uc_routes, "_USERS", {})
    monkeypatch.setattr(uc_routes, "_USERS_BY_USERNAME", {})
    return TestClient(create_app())


def _make_user(client: TestClient, username: str = "alice") -> dict[str, Any]:
    response = client.post(
        "/users",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "secret-secret",
        },
    )
    assert response.status_code == 201
    user: dict[str, Any] = response.json()
    return user


def test_create_user_generates_unique_uuid_ids(client: TestClient) -> None:
    """IDs are UUID-based: no length-derived collisions across deletes."""
    first = _make_user(client)
    client.delete(f"/users/{first['id']}")
    second = _make_user(client)

    assert second["id"] != first["id"]
    assert second["id"].startswith("user_")


def test_created_user_indexed_by_username(client: TestClient) -> None:
    """A created user resolves through the username index."""
    user = _make_user(client, "alice")

    response = client.get("/users/by-username", params={"username": "alice"})

    assert response.status_code == 200
    assert response.json()["id"] == user["id"]


def test_create_duplicate_username_conflicts(client: TestClient) -> None:
    """A duplicate username is rejected with 409."""
    _make_user(client, "alice")

    response = client.post(
        "/users",
        json={
            "username": "alice",
            "email": "other@example.com",
            "password": "secret-secret",
        },
    )

    assert response.status_code == 409


def test_update_user_rename_keeps_index_consistent(client: TestClient) -> None:
    """Renaming updates the username index atomically (old frees, new resolves)."""
    user = _make_user(client, "alice")

    response = client.patch(f"/users/{user['id']}", json={"username": "alicia"})

    assert response.status_code == 200
    assert response.json()["username"] == "alicia"
    assert client.get("/users/by-username", params={"username": "alicia"}).status_code == 200
    assert client.get("/users/by-username", params={"username": "alice"}).status_code == 404


def test_update_user_rename_to_taken_username_conflicts(client: TestClient) -> None:
    """Renaming onto another user's username is a 409 with no partial state."""
    _make_user(client, "alice")
    bob = _make_user(client, "bob")

    response = client.patch(f"/users/{bob['id']}", json={"username": "alice"})

    assert response.status_code == 409
    # Bob is unchanged and still resolvable by his old username.
    assert client.get("/users/by-username", params={"username": "bob"}).status_code == 200


def test_update_user_ignores_explicit_nulls(client: TestClient) -> None:
    """Required fields treat explicit null as omitted, not as a clear."""
    user = _make_user(client)

    response = client.patch(
        f"/users/{user['id']}",
        json={"email": None, "username": "renamed"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == user["email"]


def test_delete_user_removes_from_username_index(client: TestClient) -> None:
    """Deleting frees the username for later reuse."""
    user = _make_user(client, "alice")

    assert client.delete(f"/users/{user['id']}").status_code == 204
    assert client.get("/users/by-username", params={"username": "alice"}).status_code == 404

    second = _make_user(client, "alice")
    assert second["id"] != user["id"]


def test_concurrent_deletes_never_500(client: TestClient) -> None:
    """Racing deletes of the same user: exactly one 204, the rest 404, no 500."""
    user = _make_user(client)
    results: list[int] = []
    barrier = threading.Barrier(4)

    def delete() -> None:
        barrier.wait()
        results.append(client.delete(f"/users/{user['id']}").status_code)

    threads = [threading.Thread(target=delete) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(results) == [204, 404, 404, 404]


def test_concurrent_creates_same_username_single_winner(client: TestClient) -> None:
    """Racing creates of one username: exactly one 201, others 409."""
    payload = {
        "username": "race",
        "email": "race@example.com",
        "password": "secret-secret",
    }
    results: list[int] = []
    barrier = threading.Barrier(4)

    def create() -> None:
        barrier.wait()
        results.append(client.post("/users", json=payload).status_code)

    threads = [threading.Thread(target=create) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(results) == [201, 409, 409, 409]


def test_patch_missing_user_returns_404(client: TestClient) -> None:
    """PATCH on a non-existent user must 404."""
    response = client.patch("/users/nope", json={"email": "x@example.com"})
    assert response.status_code == 404
