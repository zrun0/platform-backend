"""A minimal HTTP mock transport with a respx-like API, built on httpx2.

Replaces respx (which can only patch the legacy `httpx` module) after the
httpx -> httpx2 migration. Pass the router as `transport=` to a service
client, register routes, and the router answers matching requests from
canned responses while recording every call for assertions.

Example:
    router = MockRouter()
    client = UcServiceClient(base_url="https://uc.test", transport=router)
    router.get("https://uc.test/users/1").return_value = ok_response(user)
"""

from __future__ import annotations

import httpx2


class MockCall:
    """A single request captured by a MockRoute."""

    def __init__(self, request: httpx2.Request) -> None:
        self.request = request


class MockCallList:
    """List-like record of calls; `last` returns the most recent MockCall."""

    def __init__(self) -> None:
        self._calls: list[MockCall] = []

    def record(self, request: httpx2.Request) -> None:
        self._calls.append(MockCall(request))

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


class MockRoute:
    """A registered (method, URL) pair with a canned response and call log."""

    def __init__(self) -> None:
        self.return_value: httpx2.Response | None = None
        self.calls = MockCallList()

    @property
    def called(self) -> bool:
        return bool(self.calls)


def _route_key(method: str, url: str | httpx2.URL) -> tuple[str, str, str, int | None, str]:
    """Normalize a URL for matching via httpx2.URL component access.

    Tests register bare URLs while clients append query params, so routes
    match on scheme/host/port/path only (same default as respx). Parsing
    with httpx2.URL also normalizes host casing and default ports
    (`http://x:80/` == `http://x/`).
    """
    parsed = httpx2.URL(url)
    return (method.upper(), parsed.scheme, parsed.host, parsed.port, parsed.path)


class MockRouter(httpx2.AsyncBaseTransport):
    """Transport that answers requests from registered routes.

    Unregistered requests raise AssertionError so tests fail loudly on
    unexpected downstream traffic instead of hitting real networks.
    """

    def __init__(self) -> None:
        self._routes: dict[tuple[str, str, str, int | None, str], MockRoute] = {}

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

    def delete(self, url: str) -> MockRoute:
        return self.route("DELETE", url)

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        route = self._routes.get(_route_key(request.method, request.url))
        if route is None:
            raise AssertionError(f"No mock route registered for {request.method} {request.url}")
        if route.return_value is None:
            raise AssertionError(
                f"Route for {request.method} {request.url} has no return_value set"
            )
        route.calls.record(request)
        return route.return_value
