"""Feign-style declarative HTTP endpoint decorators.

Decorators turn a method signature into a typed service call. Path params
are extracted from `{name}` placeholders in the URL template, the first
Pydantic-model argument becomes the JSON body, and everything else is
sent as query parameters.

Usage:
    class FlowClient(BaseServiceClient):
        @get("/flows/{flow_id}")
        async def get_flow(
            self, flow_id: str, *, ctx: RequestContext | None = None
        ) -> FlowResponse: ...
"""

from __future__ import annotations

import inspect
import typing
from functools import wraps
from typing import Any, Callable, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

# Parameter names that are treated as the request body when present.
_BODY_PARAM_NAMES = frozenset({"payload", "body", "data"})

# Parameter name for request context (header propagation).
_CTX_PARAM_NAME = "ctx"


_PARTIAL_UPDATE_METHODS = frozenset({"PUT", "PATCH"})


def _route(method: str, path: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator factory: bind an HTTP method + path template to a method.

    For PUT and PATCH (partial update semantics), Pydantic body models
    are dumped with `exclude_unset=True` so only explicitly-set fields
    are sent in the request.
    """

    body_exclude_unset = method in _PARTIAL_UPDATE_METHODS

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        sig = inspect.signature(func)

        @wraps(func)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            # Resolve return type inside the wrapper so forward refs work
            # (from __future__ import annotations makes them strings at def time).
            type_hints = typing.get_type_hints(func)
            response_model = type_hints.get("return", None)
            bound = sig.bind(self, *args, **kwargs)
            bound.apply_defaults()
            params = dict(bound.arguments)

            # Pull out self and ctx; they never go on the wire.
            params.pop("self", None)
            ctx = params.pop(_CTX_PARAM_NAME, None)

            # Body: first param whose name is in _BODY_PARAM_NAMES.
            json_body = None
            for name in _BODY_PARAM_NAMES:
                if name in params:
                    value = params.pop(name)
                    if hasattr(value, "model_dump"):
                        json_body = value.model_dump(
                            mode="json",
                            exclude_unset=body_exclude_unset,
                        )
                    else:
                        json_body = value
                    break

            # Split remaining params into path vars and query params.
            path_vars: dict[str, Any] = {}
            query_params: dict[str, Any] = {}
            for name, value in params.items():
                if f"{{{name}}}" in path:
                    path_vars[name] = value
                elif value is not None:
                    # Skip None values so httpx doesn't encode them.
                    query_params[name] = value

            formatted_path = path.format(**path_vars)

            return await self.request(
                method,
                formatted_path,
                ctx=ctx,
                json=json_body,
                params=query_params or None,
                response_model=response_model,
            )

        # Cast wrapper to the expected signature. The actual runtime type is
        # an async function that returns a coroutine, but the decorator claims
        # to return the original function's signature (Callable[P, R]).
        return typing.cast(Callable[P, R], wrapper)

    return decorator


def get(path: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Declare a GET endpoint."""
    return _route("GET", path)


def post(path: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Declare a POST endpoint."""
    return _route("POST", path)


def put(path: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Declare a PUT endpoint."""
    return _route("PUT", path)


def delete(path: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Declare a DELETE endpoint."""
    return _route("DELETE", path)


def patch(path: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Declare a PATCH endpoint."""
    return _route("PATCH", path)
