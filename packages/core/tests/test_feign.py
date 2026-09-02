"""Tests for the Feign-style declarative client decorators.

Covers decoration-time fail-fast validation and per-request behavior
(path encoding, body detection, no-content handling, PATCH vs PUT
serialization).
"""

from __future__ import annotations

import json
from typing import Any

import httpx2
import pytest
from pydantic import BaseModel
from zrun_test_utils import MockRouter
from zrun_test_utils.helpers import ok_response

from zrun.core.http import feign
from zrun.core.http.base_client import BaseServiceClient

BASE_URL = "https://demo.test"


class _Item(BaseModel):
    name: str
    note: str | None = None


class _DemoClient(BaseServiceClient):
    """Client exercising every decorator behavior."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(base_url=BASE_URL, service_name="demo", **kwargs)

    @feign.get("/items/{item_id}")
    async def get_item(self, item_id: str, *, ctx: object = None) -> _Item: ...

    @feign.delete("/items/{item_id}")
    async def delete_item(self, item_id: str, *, ctx: object = None) -> None: ...

    # Body parameter deliberately named `item` (not payload/body/data):
    # body detection must be type-based, not name-based.
    @feign.post("/items")
    async def create_item(self, item: _Item, *, ctx: object = None) -> _Item: ...

    @feign.patch("/items/{item_id}")
    async def patch_item(self, item_id: str, payload: _Item, *, ctx: object = None) -> _Item: ...

    @feign.put("/items/{item_id}")
    async def put_item(self, item_id: str, payload: _Item, *, ctx: object = None) -> _Item: ...

    @feign.get("/search")
    async def search(self, q: str | None = None, *, ctx: object = None) -> list[_Item]: ...


@pytest.fixture
def client(mock_router: MockRouter) -> _DemoClient:
    return _DemoClient(max_retries=0, transport=mock_router)


# ---------------------------------------------------------------------------
# Decoration-time fail-fast validation
# ---------------------------------------------------------------------------


def test_missing_return_annotation_fails_at_decoration() -> None:
    """A method without a return annotation must fail at import time."""
    with pytest.raises(TypeError, match="return type annotation"):

        @feign.get("/items/{item_id}")
        async def get_item(self: object, item_id: str):  # no return annotation
            ...


def test_path_placeholder_without_parameter_fails_at_decoration() -> None:
    """A {placeholder} with no matching parameter must fail at import time."""
    with pytest.raises(TypeError, match="undeclared"):

        @feign.get("/items/{item_id}")
        async def get_item(self: object, item_uuid: str) -> _Item: ...


def test_body_method_without_body_model_fails_at_decoration() -> None:
    """POST without a BaseModel parameter must fail at import time."""
    with pytest.raises(TypeError, match="body parameter"):

        @feign.post("/items")
        async def create_item(self: object, name: str) -> _Item: ...


def test_get_with_body_model_fails_at_decoration() -> None:
    """A GET endpoint must not declare a body parameter."""
    with pytest.raises(TypeError, match="must not declare a body"):

        @feign.get("/items")
        async def list_items(self: object, item: _Item) -> list[_Item]: ...


def test_multiple_body_models_fails_at_decoration() -> None:
    """At most one BaseModel body parameter is allowed."""
    with pytest.raises(TypeError, match="multiple BaseModel"):

        @feign.post("/items")
        async def create_item(self: object, a: _Item, b: _Item) -> _Item: ...


# ---------------------------------------------------------------------------
# Per-request behavior
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_no_content_returns_none(client: _DemoClient, mock_router: MockRouter) -> None:
    """`-> None` on a 204 response must return None without parsing a body."""
    mock_router.delete(f"{BASE_URL}/items/i1").return_value = httpx2.Response(204)

    result = await client.delete_item("i1")

    assert result is None


@pytest.mark.asyncio
async def test_body_identified_by_type_not_name(
    client: _DemoClient, mock_router: MockRouter
) -> None:
    """A BaseModel parameter is the body regardless of its name."""
    route = mock_router.post(f"{BASE_URL}/items")
    route.return_value = ok_response({"name": "x", "note": None}, status=201)

    await client.create_item(_Item(name="x"))

    request = route.calls.last.request
    assert json.loads(request.content) == {"name": "x", "note": None}
    # The model must NOT be stringified into query parameters.
    assert "item" not in request.url.params
    assert request.url.path == "/items"


@pytest.mark.asyncio
async def test_path_param_is_percent_encoded(client: _DemoClient, mock_router: MockRouter) -> None:
    """Reserved characters in path params must be percent-encoded."""
    route = mock_router.get(f"{BASE_URL}/items/a%2Fb")
    route.return_value = ok_response({"name": "x", "note": None})

    await client.get_item("a/b")

    assert route.called
    # `.path` decodes percent-encoding; raw_path keeps the encoded segment.
    assert route.calls.last.request.url.raw_path == b"/items/a%2Fb"


@pytest.mark.asyncio
async def test_none_path_param_raises_type_error(client: _DemoClient) -> None:
    """A None path variable must fail fast instead of becoming the literal 'None'."""
    with pytest.raises(TypeError, match="path parameter .* must not be None"):
        await client.get_item(None)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_patch_sends_only_set_fields(client: _DemoClient, mock_router: MockRouter) -> None:
    """PATCH uses partial-update semantics: unset fields are excluded."""
    route = mock_router.patch(f"{BASE_URL}/items/i1")
    route.return_value = ok_response({"name": "new", "note": None})

    await client.patch_item("i1", _Item(name="new"))

    assert json.loads(route.calls.last.request.content) == {"name": "new"}


@pytest.mark.asyncio
async def test_put_sends_full_body(client: _DemoClient, mock_router: MockRouter) -> None:
    """PUT is full replacement: the complete body (including nulls) is sent."""
    route = mock_router.put(f"{BASE_URL}/items/i1")
    route.return_value = ok_response({"name": "new", "note": None})

    await client.put_item("i1", _Item(name="new"))

    assert json.loads(route.calls.last.request.content) == {"name": "new", "note": None}


@pytest.mark.asyncio
async def test_none_query_param_skipped(client: _DemoClient, mock_router: MockRouter) -> None:
    """None query params are omitted; non-None values are sent."""
    route = mock_router.get(f"{BASE_URL}/search")
    route.return_value = ok_response([])

    await client.search(q=None)
    assert "q" not in route.calls.last.request.url.params

    await client.search(q="foo")
    assert route.calls.last.request.url.params.get("q") == "foo"
