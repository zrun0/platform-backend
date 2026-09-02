"""Tests for UC user endpoints (in-memory store)."""

from fastapi.testclient import TestClient

from zrun.uc.main import create_app


def _client() -> TestClient:
    return TestClient(create_app())


def test_create_and_patch_user_partial_update() -> None:
    """PATCH updates only the fields sent; others are preserved."""
    client = _client()
    created = client.post(
        "/users",
        json={"username": "alice", "email": "alice@example.com", "password": "password1"},
    )
    assert created.status_code == 201
    user_id = created.json()["id"]

    patched = client.patch(f"/users/{user_id}", json={"email": "new@example.com"})
    assert patched.status_code == 200
    body = patched.json()
    assert body["email"] == "new@example.com"
    # Unsent fields are preserved.
    assert body["username"] == "alice"
    assert body["updated_at"] >= body["created_at"]


def test_patch_missing_user_returns_404() -> None:
    """PATCH on a non-existent user must 404."""
    response = _client().patch("/users/nope", json={"email": "x@example.com"})
    assert response.status_code == 404


def test_put_is_not_allowed_for_updates() -> None:
    """Updates use PATCH; PUT on the update route must not exist (405)."""
    response = _client().put("/users/user_1", json={"email": "x@example.com"})
    assert response.status_code == 405
