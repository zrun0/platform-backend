# zrun-test-utils

Shared test utilities and fixtures for zrun platform backend.

## Usage

```python
from zrun_test_utils.helpers import ok_response, error_response


def test_api_client():
    # Create successful response
    response = ok_response({"user": "alice"})

    # Create error response
    error = error_response("User not found", status=404)
```

## Mocking downstream HTTP (replaces respx)

respx only patches the legacy `httpx` module and cannot intercept httpx2
clients. Use `MockRouter` — an `httpx2.AsyncBaseTransport` with a
respx-like API — injected via the `transport=` parameter:

```python
from zrun_test_utils import MockRouter

router = MockRouter()
client = UcServiceClient(base_url="https://uc.test", transport=router)

route = router.get("https://uc.test/users/1")
route.return_value = ok_response(user_data)

result = await client.get_user("1")

assert route.called
assert route.calls.last.request.headers["Authorization"] == "Bearer tok"
```

URLs are parsed with `httpx2.URL` and match on scheme/host/port/path — query
strings are ignored, host casing and default ports are normalized (like
respx's default). Unregistered requests, and routes registered without a
`return_value`, raise `AssertionError` so failures are loud.

## Installation

Part of the zrun uv workspace. A member package that wants these helpers in its tests declares them in the dev dependency group with a workspace source (see `packages/uc-api/pyproject.toml` for a live example):

```toml
[dependency-groups]
dev = ["zrun-test-utils"]

[tool.uv.sources]
zrun-test-utils = { workspace = true }
```
