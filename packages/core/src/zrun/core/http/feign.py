"""Feign-style declarative HTTP endpoint decorators.

Decorators turn a method signature into a typed service call. Path params
are extracted from `{name}` placeholders in the URL template, the
Pydantic-model argument becomes the JSON body, and everything else is sent
as query parameters.

The contract between a method signature and its HTTP behavior is validated
**once at decoration time** (i.e. at import / service startup): a missing
return annotation, an unresolvable path placeholder, or a body method
without a Pydantic body parameter raises ``TypeError`` immediately instead
of failing on the first request.

Usage:
    class FlowClient(BaseServiceClient):
        @get("/flows/{flow_id}")
        async def get_flow(
            self, flow_id: str, *, ctx: RequestContext | None = None
        ) -> FlowResponse: ...
"""

from __future__ import annotations

import inspect
import re
import typing
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any, ParamSpec, TypeVar
from urllib.parse import quote

from pydantic import BaseModel

P = ParamSpec("P")
R = TypeVar("R")

# Parameter name for request context (header propagation); never sent on the wire.
_CTX_PARAM_NAME = "ctx"

_PATH_PLACEHOLDER_RE = re.compile(r"{(\w+)}")

# Methods that carry a JSON request body.
_BODY_METHODS = frozenset({"POST", "PUT", "PATCH"})
# Partial-update semantics: only explicitly-set fields are sent (PATCH).
# PUT is full replacement and sends the complete body.
_PARTIAL_UPDATE_METHODS = frozenset({"PATCH"})
_SUPPORTED_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"})


@dataclass(frozen=True)
class EndpointSpec:
    """Validated description of one declared endpoint.

    Built once at decoration time; the per-request wrapper only reads it.
    """

    method: str
    path_template: str
    path_params: tuple[str, ...]
    body_param: str | None
    query_params: tuple[str, ...]
    response_type: Any
    partial_update: bool

    @property
    def no_content(self) -> bool:
        """True for ``-> None`` endpoints (e.g. 204 No Content)."""
        return self.response_type is type(None)


def _build_spec(method: str, path: str, func: Callable[..., Any]) -> EndpointSpec:
    """Validate the decorated signature and build its EndpointSpec.

    Raises:
        TypeError: the signature/path/return annotation violates the contract.
    """
    if method not in _SUPPORTED_METHODS:
        raise TypeError(f"{func.__qualname__}: unsupported HTTP method {method!r}")

    try:
        hints = typing.get_type_hints(func)
    except Exception as exc:
        raise TypeError(f"{func.__qualname__}: cannot resolve type annotations: {exc}") from exc

    if "return" not in hints:
        raise TypeError(
            f"{func.__qualname__}: missing return type annotation; annotate the "
            "response model, or `-> None` for no-content (204) endpoints"
        )

    sig = inspect.signature(func)
    wire_params = {
        name: param
        for name, param in sig.parameters.items()
        if name not in ("self", _CTX_PARAM_NAME)
    }

    # --- Path placeholders must all resolve to declared parameters. ---
    path_params = tuple(_PATH_PLACEHOLDER_RE.findall(path))
    missing = [name for name in path_params if name not in wire_params]
    if missing:
        raise TypeError(
            f"{func.__qualname__}: path template {path!r} references undeclared "
            f"parameter(s) {missing}"
        )

    # --- Body parameter: identified BY TYPE (BaseModel), not by name. ---
    body_params = [
        name
        for name in wire_params
        if name not in path_params
        and isinstance(hints.get(name), type)
        and issubclass(hints[name], BaseModel)
    ]
    if len(body_params) > 1:
        raise TypeError(
            f"{func.__qualname__}: multiple BaseModel parameters {body_params}; "
            "exactly one body parameter is allowed"
        )
    body_param = body_params[0] if body_params else None

    if method in _BODY_METHODS and body_param is None:
        raise TypeError(
            f"{func.__qualname__}: {method} endpoint must declare exactly one "
            "BaseModel body parameter"
        )
    if method not in _BODY_METHODS and body_param is not None:
        raise TypeError(
            f"{func.__qualname__}: {method} endpoint must not declare a body "
            f"parameter ({body_param!r}); bodies are only allowed on "
            "POST/PUT/PATCH"
        )

    query_params = tuple(
        name for name in wire_params if name not in path_params and name != body_param
    )

    return EndpointSpec(
        method=method,
        path_template=path,
        path_params=path_params,
        body_param=body_param,
        query_params=query_params,
        response_type=hints["return"],
        partial_update=method in _PARTIAL_UPDATE_METHODS,
    )


def _route(method: str, path: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator factory: bind an HTTP method + path template to a method."""

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        spec = _build_spec(method, path, func)
        sig = inspect.signature(func)

        @wraps(func)
        async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            bound = sig.bind(self, *args, **kwargs)
            bound.apply_defaults()
            arguments = dict(bound.arguments)

            arguments.pop("self", None)
            ctx = arguments.pop(_CTX_PARAM_NAME, None)

            # Path params: percent-encode each segment; None is a caller bug.
            path_vars: dict[str, str] = {}
            for name in spec.path_params:
                value = arguments.pop(name)
                if value is None:
                    raise TypeError(
                        f"{func.__qualname__}: path parameter {name!r} must not be None"
                    )
                path_vars[name] = quote(str(value), safe="")
            formatted_path = spec.path_template.format_map(path_vars)

            # Body: the single BaseModel parameter.
            json_body = None
            if spec.body_param is not None:
                value = arguments.pop(spec.body_param)
                json_body = (
                    value.model_dump(mode="json", exclude_unset=spec.partial_update)
                    if hasattr(value, "model_dump")
                    else value
                )

            # Query params: everything else; skip None so httpx2 drops them.
            query_params = {
                name: arguments.pop(name)
                for name in spec.query_params
                if arguments.get(name) is not None
            }

            return await self.request(
                spec.method,
                formatted_path,
                ctx=ctx,
                json=json_body,
                params=query_params or None,
                response_model=spec.response_type,
            )

        # Expose the spec for contract self-check tests.
        wrapper.__endpoint_spec__ = spec  # type: ignore[attr-defined]
        return typing.cast(Callable[P, R], wrapper)

    return decorator


def get(path: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Declare a GET endpoint."""
    return _route("GET", path)


def post(path: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Declare a POST endpoint."""
    return _route("POST", path)


def put(path: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Declare a PUT endpoint (full replacement; sends the complete body)."""
    return _route("PUT", path)


def patch(path: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Declare a PATCH endpoint (partial update; sends only set fields)."""
    return _route("PATCH", path)


def delete(path: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Declare a DELETE endpoint. Annotate ``-> None`` for 204 responses."""
    return _route("DELETE", path)
