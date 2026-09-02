"""A minimal HTTP mock transport with a respx-like API, built on httpx2.

Replaces respx (which can only patch the legacy `httpx` module) after the
httpx -> httpx2 migration. Pass the router as ``transport=`` to a service
client, register routes, and the router answers matching requests from
canned responses (or side effects) while recording every call for assertions.

Example:
    router = MockRouter()
    client = UcServiceClient(base_url="https://uc.test", transport=router)
    router.get("https://uc.test/users/1").return_value = ok_response(user)

Example with side_effect (first call fails, second succeeds):
    route = router.get("https://uc.test/users/1")
    route.side_effect = [
        error_response("down", status=503),
        ok_response(user),
    ]

Example with TransportError simulation:
    router.get("https://uc.test/users/1").side_effect = httpx2.TimeoutException("timed out")
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator

import httpx2


class MockCall:
    """A single request captured by a MockRoute."""

    def __init__(self, request: httpx2.Request) -> None:
        self.request = request


class MockCallList:
    """List-like record of calls; ``last`` returns the most recent MockCall."""

    def __init__(self) -> None:
        self._calls: list[MockCall] = []

    def record(self, request: httpx2.Request) -> None:
        self._calls.append(MockCall(request))

    def clear(self) -> None:
        """Remove all recorded calls."""
        self._calls.clear()

    @property
    def last(self) -> MockCall:
        if not self._calls:
            raise AssertionError("No calls were made to this route")
        return self._calls[-1]

    def __len__(self) -> int:
        return len(self._calls)

    def __bool__(self) -> bool:
        return bool(self._calls)

    def __iter__(self):
        return iter(self._calls)

    def __getitem__(self, index: int) -> MockCall:
        return self._calls[index]


# Types accepted by MockRoute.side_effect.
SideEffect = (
    httpx2.Response
    | BaseException
    | Callable[[httpx2.Request], httpx2.Response | BaseException]
    | Iterable[httpx2.Response | BaseException]
    | None
)


class MockRoute:
    """A registered (method, URL) pair with a canned response and call log.

    Response resolution order:
    1. If ``side_effect`` is set, use it (exception, callable, or iterable).
    2. Otherwise, use ``return_value``.
    """

    def __init__(self) -> None:
        self.return_value: httpx2.Response | None = None
        self.side_effect: SideEffect = None
        self.calls = MockCallList()
        self._side_effect_iter: Iterator[httpx2.Response | BaseException] | None = None

    @property
    def called(self) -> bool:
        return bool(self.calls)

    @property
    def call_count(self) -> int:
        """Number of times this route has been called."""
        return len(self.calls)

    @property
    def called_once(self) -> bool:
        """True if this route has been called exactly once."""
        return len(self.calls) == 1

    def reset(self) -> None:
        """Reset call history and side_effect iterator state.

        ``return_value`` and ``side_effect`` configuration are preserved.
        """
        self.calls.clear()
        self._side_effect_iter = None

    def _resolve_response(self, request: httpx2.Request) -> httpx2.Response | None:
        """Resolve the response (or exception) for the current call.

        Returns the response if one is configured; raises a ``BaseException``
        if side_effect is an exception or returns one.  Returns ``None`` if
        nothing is configured (caller should raise AssertionError).
        """
        if self.side_effect is not None:
            return self._resolve_side_effect(request)
        if self.return_value is not None:
            return self.return_value
        return None

    def _resolve_side_effect(self, request: httpx2.Request) -> httpx2.Response:
        # Exception instance -> raise it
        if isinstance(self.side_effect, BaseException):
            raise self.side_effect

        # Callable -> invoke with request
        if callable(self.side_effect):
            result = self.side_effect(request)
            if isinstance(result, BaseException):
                raise result
            return result

        # Iterable -> pop next item
        if self._side_effect_iter is None:
            self._side_effect_iter = iter(self.side_effect)  # type: ignore[arg-type]
        assert self._side_effect_iter is not None
        try:
            item = next(self._side_effect_iter)
        except StopIteration:
            raise AssertionError(
                f"side_effect exhausted after {len(self.calls)} call(s); "
                "no more responses to return"
            ) from None
        if isinstance(item, BaseException):
            raise item
        return item


def _route_key(method: str, url: str | httpx2.URL) -> tuple[str, str, str, int | None, str]:
    """Normalize a URL for matching via httpx2.URL component access.

    Tests register bare URLs while clients append query params, so routes
    match on scheme/host/port/path only (same default as respx). Parsing
    with httpx2.URL also normalizes host casing and default ports
    (``http://x:80/`` == ``http://x/``).
    """
    parsed = httpx2.URL(url)
    return (method.upper(), parsed.scheme, parsed.host, parsed.port, parsed.path)


class MockRouter(httpx2.AsyncBaseTransport, httpx2.BaseTransport):
    """Transport that answers requests from registered routes.

    Unregistered requests raise AssertionError so tests fail loudly on
    unexpected downstream traffic instead of hitting real networks.

    Implements both :class:`httpx2.AsyncBaseTransport` and
    :class:`httpx2.BaseTransport` so it works with async and sync clients.
    """

    def __init__(self) -> None:
        self._routes: dict[tuple[str, str, str, int | None, str], MockRoute] = {}

    # ------------------------------------------------------------------
    # Route registration
    # ------------------------------------------------------------------

    def route(self, method: str, url: str) -> MockRoute:
        key = _route_key(method, url)
        if key not in self._routes:
            self._routes[key] = MockRoute()
        return self._routes[key]

    def get(self, url: str) -> MockRoute:
        return self.route("GET", url)

    def post(self, url: str) -> MockRoute:
        return self.route("POST", url)

    def put(self, url: str) -> MockRoute:
        return self.route("PUT", url)

    def patch(self, url: str) -> MockRoute:
        return self.route("PATCH", url)

    def delete(self, url: str) -> MockRoute:
        return self.route("DELETE", url)

    def head(self, url: str) -> MockRoute:
        return self.route("HEAD", url)

    def options(self, url: str) -> MockRoute:
        return self.route("OPTIONS", url)

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset all routes: clear call history and side_effect iterators.

        Route registrations and their ``return_value``/``side_effect``
        configuration are preserved.
        """
        for route in self._routes.values():
            route.reset()

    def clear(self) -> None:
        """Remove all registered routes entirely."""
        self._routes.clear()

    # ------------------------------------------------------------------
    # Transport interface
    # ------------------------------------------------------------------

    def _handle(self, request: httpx2.Request) -> httpx2.Response:
        route = self._routes.get(_route_key(request.method, request.url))
        if route is None:
            raise AssertionError(f"No mock route registered for {request.method} {request.url}")

        # Record the call BEFORE resolving the response so that debugging
        # info is available even when return_value/side_effect is missing
        # or raises an exception.
        route.calls.record(request)

        response = route._resolve_response(request)  # pyright: ignore[reportPrivateUsage]
        if response is None:
            raise AssertionError(
                f"Route for {request.method} {request.url} has no return_value or side_effect set"
            )
        return response

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        return self._handle(request)

    def handle_request(self, request: httpx2.Request) -> httpx2.Response:
        return self._handle(request)
