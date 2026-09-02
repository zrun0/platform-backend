"""Tests for MockRouter, MockRoute, and MockCallList."""

from __future__ import annotations

import asyncio

import httpx2
import pytest
from zrun_test_utils.helpers import error_response, ok_response
from zrun_test_utils.mock_router import MockCallList, MockRouter

# ---------------------------------------------------------------------------
# MockCallList
# ---------------------------------------------------------------------------


class TestMockCallList:
    def test_empty(self) -> None:
        cl = MockCallList()
        assert len(cl) == 0
        assert not cl
        assert list(cl) == []

    def test_record_and_last(self) -> None:
        cl = MockCallList()
        req = httpx2.Request("GET", "https://test/x")
        cl.record(req)
        assert len(cl) == 1
        assert cl
        assert cl.last.request is req

    def test_last_empty_raises(self) -> None:
        cl = MockCallList()
        with pytest.raises(AssertionError, match="No calls"):
            _ = cl.last  # noqa: B018 - testing the property raises

    def test_iteration(self) -> None:
        cl = MockCallList()
        for i in range(3):
            cl.record(httpx2.Request("GET", f"https://test/{i}"))
        assert [c.request.url.path for c in cl] == ["/0", "/1", "/2"]

    def test_getitem(self) -> None:
        cl = MockCallList()
        for i in range(3):
            cl.record(httpx2.Request("GET", f"https://test/{i}"))
        assert cl[0].request.url.path == "/0"
        assert cl[1].request.url.path == "/1"
        assert cl[-1].request.url.path == "/2"

    def test_clear(self) -> None:
        cl = MockCallList()
        cl.record(httpx2.Request("GET", "https://test/x"))
        cl.clear()
        assert len(cl) == 0
        assert not cl


# ---------------------------------------------------------------------------
# MockRoute
# ---------------------------------------------------------------------------


class TestMockRoute:
    def test_default_state(self) -> None:
        router = MockRouter()
        route = router.get("https://test/x")
        assert route.return_value is None
        assert route.side_effect is None
        assert not route.called
        assert route.call_count == 0
        assert not route.called_once

    def test_return_value(self) -> None:
        router = MockRouter()
        route = router.get("https://test/x")
        route.return_value = ok_response({"key": "val"})
        assert route.called is False

    def test_called_once(self) -> None:
        router = MockRouter()
        route = router.get("https://test/x")
        route.return_value = ok_response({})

        async def run() -> None:
            client = httpx2.AsyncClient(transport=router)
            await client.get("https://test/x")
            assert route.called_once
            await client.get("https://test/x")
            assert not route.called_once

        asyncio.run(run())

    def test_reset_clears_calls_and_side_effect_iter(self) -> None:
        router = MockRouter()
        route = router.get("https://test/x")
        route.side_effect = [ok_response({"i": 1}), ok_response({"i": 2})]

        async def run() -> None:
            client = httpx2.AsyncClient(transport=router)
            await client.get("https://test/x")
            await client.get("https://test/x")
            assert route.call_count == 2

            route.reset()
            assert route.call_count == 0
            assert not route.called
            # After reset, side_effect iterator should restart from the beginning
            resp = await client.get("https://test/x")
            assert resp.json()["i"] == 1

        asyncio.run(run())


# ---------------------------------------------------------------------------
# MockRouter route registration and matching
# ---------------------------------------------------------------------------


class TestMockRouterMatching:
    def test_route_method_normalization(self) -> None:
        router = MockRouter()
        route1 = router.route("get", "https://test/x")
        route2 = router.route("GET", "https://test/x")
        assert route1 is route2

    def test_host_case_normalized(self) -> None:
        router = MockRouter()
        route1 = router.get("https://Example.COM/x")
        route2 = router.get("https://example.com/x")
        assert route1 is route2

    def test_default_port_normalized(self) -> None:
        router = MockRouter()
        route1 = router.get("http://test.com/x")
        route2 = router.get("http://test.com:80/x")
        assert route1 is route2

    def test_query_params_ignored_in_matching(self) -> None:
        router = MockRouter()
        route = router.get("https://test/users")
        route.return_value = ok_response({})

        async def run() -> None:
            client = httpx2.AsyncClient(transport=router)
            resp = await client.get("https://test/users?foo=bar")
            assert resp.status_code == 200
            assert route.call_count == 1

        asyncio.run(run())

    def test_path_case_sensitive(self) -> None:
        router = MockRouter()
        route_upper = router.get("https://test/Users")
        route_lower = router.get("https://test/users")
        assert route_upper is not route_lower

    def test_trailing_slash_root_path_normalized(self) -> None:
        router = MockRouter()
        route1 = router.get("https://test.com")
        route2 = router.get("https://test.com/")
        assert route1 is route2


# ---------------------------------------------------------------------------
# MockRouter async transport
# ---------------------------------------------------------------------------


class TestMockRouterAsync:
    def test_basic_get(self) -> None:
        router = MockRouter()
        router.get("https://test/users/1").return_value = ok_response({"id": "1", "name": "alice"})

        async def run() -> None:
            client = httpx2.AsyncClient(transport=router)
            resp = await client.get("https://test/users/1")
            assert resp.status_code == 200
            assert resp.json() == {"id": "1", "name": "alice"}

        asyncio.run(run())

    def test_post_with_json_body(self) -> None:
        router = MockRouter()
        router.post("https://test/users").return_value = ok_response({"id": "1"}, status=201)

        async def run() -> None:
            client = httpx2.AsyncClient(transport=router)
            resp = await client.post("https://test/users", json={"name": "alice"})
            assert resp.status_code == 201
            body = router.post("https://test/users").calls.last.request.content
            assert b"alice" in body

        asyncio.run(run())

    def test_unregistered_route_raises(self) -> None:
        router = MockRouter()

        async def run() -> None:
            client = httpx2.AsyncClient(transport=router)
            with pytest.raises(AssertionError, match="No mock route registered"):
                await client.get("https://test/nope")

        asyncio.run(run())

    def test_no_return_value_records_call_before_raising(self) -> None:
        """Call must be recorded even when return_value/side_effect is missing."""
        router = MockRouter()
        route = router.get("https://test/x")  # registered, no return_value

        async def run() -> None:
            client = httpx2.AsyncClient(transport=router)
            with pytest.raises(AssertionError, match="no return_value"):
                await client.get("https://test/x")
            # The call should still be recorded for debugging
            assert route.called
            assert route.call_count == 1
            assert route.calls.last.request.url.path == "/x"

        asyncio.run(run())

    def test_patch_method(self) -> None:
        router = MockRouter()
        router.patch("https://test/users/1").return_value = ok_response({"id": "1"})

        async def run() -> None:
            client = httpx2.AsyncClient(transport=router)
            resp = await client.patch("https://test/users/1", json={"name": "new"})
            assert resp.status_code == 200
            assert router.patch("https://test/users/1").call_count == 1

        asyncio.run(run())

    def test_head_and_options_methods(self) -> None:
        router = MockRouter()
        router.head("https://test/x").return_value = ok_response({})
        router.options("https://test/x").return_value = ok_response({})

        async def run() -> None:
            client = httpx2.AsyncClient(transport=router)
            h = await client.head("https://test/x")
            o = await client.options("https://test/x")
            assert h.status_code == 200
            assert o.status_code == 200

        asyncio.run(run())

    def test_request_id_propagated(self) -> None:
        router = MockRouter()
        route = router.get("https://test/x")
        route.return_value = ok_response({})

        async def run() -> None:
            client = httpx2.AsyncClient(transport=router)
            await client.get("https://test/x", headers={"X-Request-ID": "req-42"})
            assert route.calls.last.request.headers.get("X-Request-ID") == "req-42"

        asyncio.run(run())


# ---------------------------------------------------------------------------
# MockRouter side_effect
# ---------------------------------------------------------------------------


class TestMockRouterSideEffect:
    def test_side_effect_list(self) -> None:
        router = MockRouter()
        route = router.get("https://test/x")
        route.side_effect = [
            ok_response({"n": 1}),
            ok_response({"n": 2}),
            ok_response({"n": 3}),
        ]

        async def run() -> None:
            client = httpx2.AsyncClient(transport=router)
            assert (await client.get("https://test/x")).json()["n"] == 1
            assert (await client.get("https://test/x")).json()["n"] == 2
            assert (await client.get("https://test/x")).json()["n"] == 3
            assert route.call_count == 3

        asyncio.run(run())

    def test_side_effect_exception(self) -> None:
        """side_effect with a TransportError raises it directly."""
        router = MockRouter()
        route = router.get("https://test/x")
        route.side_effect = httpx2.TimeoutException("timed out")

        async def run() -> None:
            client = httpx2.AsyncClient(transport=router)
            with pytest.raises(httpx2.TimeoutException):
                await client.get("https://test/x")
            assert route.called

        asyncio.run(run())

    def test_side_effect_mixed_responses_and_exceptions(self) -> None:
        """side_effect list can mix responses and exceptions (retry scenario)."""
        router = MockRouter()
        route = router.get("https://test/x")
        route.side_effect = [
            httpx2.TimeoutException("timeout 1"),
            httpx2.TimeoutException("timeout 2"),
            ok_response({"recovered": True}),
        ]

        async def run() -> None:
            client = httpx2.AsyncClient(transport=router)
            with pytest.raises(httpx2.TimeoutException):
                await client.get("https://test/x")
            with pytest.raises(httpx2.TimeoutException):
                await client.get("https://test/x")
            resp = await client.get("https://test/x")
            assert resp.json()["recovered"] is True
            assert route.call_count == 3

        asyncio.run(run())

    def test_side_effect_callable(self) -> None:
        """side_effect callable receives the request and returns a response."""
        router = MockRouter()
        route = router.get("https://test/echo")

        def echo(req: httpx2.Request) -> httpx2.Response:
            return ok_response({"path": req.url.path, "header": req.headers.get("X-Echo")})

        route.side_effect = echo

        async def run() -> None:
            client = httpx2.AsyncClient(transport=router)
            resp = await client.get("https://test/echo", headers={"X-Echo": "hello"})
            data = resp.json()
            assert data["path"] == "/echo"
            assert data["header"] == "hello"

        asyncio.run(run())

    def test_side_effect_callable_raises(self) -> None:
        """side_effect callable can raise an exception."""
        router = MockRouter()
        route = router.get("https://test/x")
        route.side_effect = lambda req: httpx2.ConnectError("nope")

        async def run() -> None:
            client = httpx2.AsyncClient(transport=router)
            with pytest.raises(httpx2.ConnectError):
                await client.get("https://test/x")

        asyncio.run(run())

    def test_side_effect_exhausted_raises_assertion_error(self) -> None:
        router = MockRouter()
        route = router.get("https://test/x")
        route.side_effect = [ok_response({"n": 1})]

        async def run() -> None:
            client = httpx2.AsyncClient(transport=router)
            await client.get("https://test/x")
            with pytest.raises(AssertionError, match="side_effect exhausted"):
                await client.get("https://test/x")

        asyncio.run(run())

    def test_side_effect_takes_priority_over_return_value(self) -> None:
        router = MockRouter()
        route = router.get("https://test/x")
        route.return_value = ok_response({"from": "return_value"})
        route.side_effect = [ok_response({"from": "side_effect"})]

        async def run() -> None:
            client = httpx2.AsyncClient(transport=router)
            resp = await client.get("https://test/x")
            assert resp.json()["from"] == "side_effect"

        asyncio.run(run())


# ---------------------------------------------------------------------------
# MockRouter sync transport
# ---------------------------------------------------------------------------


class TestMockRouterSync:
    def test_sync_get(self) -> None:
        router = MockRouter()
        router.get("https://test/x").return_value = ok_response({"sync": True})

        client = httpx2.Client(transport=router)
        resp = client.get("https://test/x")
        assert resp.status_code == 200
        assert resp.json() == {"sync": True}

    def test_sync_post(self) -> None:
        router = MockRouter()
        router.post("https://test/submit").return_value = ok_response({"ok": True}, status=201)

        client = httpx2.Client(transport=router)
        resp = client.post("https://test/submit", json={"data": "value"})
        assert resp.status_code == 201
        assert router.post("https://test/submit").called_once

    def test_sync_unregistered_raises(self) -> None:
        router = MockRouter()
        client = httpx2.Client(transport=router)
        with pytest.raises(AssertionError, match="No mock route registered"):
            client.get("https://test/nope")

    def test_sync_side_effect_exception(self) -> None:
        router = MockRouter()
        router.get("https://test/x").side_effect = httpx2.TimeoutException("sync timeout")

        client = httpx2.Client(transport=router)
        with pytest.raises(httpx2.TimeoutException):
            client.get("https://test/x")


# ---------------------------------------------------------------------------
# MockRouter reset / clear
# ---------------------------------------------------------------------------


class TestMockRouterReset:
    def test_reset_preserves_routes(self) -> None:
        router = MockRouter()
        router.get("https://test/a").return_value = ok_response({"a": 1})
        router.get("https://test/b").return_value = ok_response({"b": 2})

        async def run() -> None:
            client = httpx2.AsyncClient(transport=router)
            await client.get("https://test/a")
            await client.get("https://test/b")
            assert router.get("https://test/a").call_count == 1
            assert router.get("https://test/b").call_count == 1

            router.reset()

            assert router.get("https://test/a").call_count == 0
            assert router.get("https://test/b").call_count == 0
            # Routes still work after reset
            resp = await client.get("https://test/a")
            assert resp.json() == {"a": 1}

        asyncio.run(run())

    def test_clear_removes_all_routes(self) -> None:
        router = MockRouter()
        router.get("https://test/x").return_value = ok_response({})
        router.clear()

        async def run() -> None:
            client = httpx2.AsyncClient(transport=router)
            with pytest.raises(AssertionError, match="No mock route registered"):
                await client.get("https://test/x")

        asyncio.run(run())


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_ok_response_default_status(self) -> None:
        resp = ok_response({"key": "val"})
        assert resp.status_code == 200
        assert resp.json() == {"key": "val"}

    def test_ok_response_custom_status(self) -> None:
        resp = ok_response({"created": True}, status=201)
        assert resp.status_code == 201

    def test_error_response_default_status(self) -> None:
        resp = error_response("Not found")
        assert resp.status_code == 404
        assert resp.json() == {"detail": "Not found"}

    def test_error_response_custom_status(self) -> None:
        resp = error_response("Server error", status=500)
        assert resp.status_code == 500
        assert resp.json() == {"detail": "Server error"}
