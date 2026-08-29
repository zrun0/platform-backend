"""Base class for typed HTTP service clients.

Provides connection pooling, timeout, retry with exponential backoff,
request context propagation, error mapping, and response model parsing.
"""

from __future__ import annotations

import logging
from functools import cache
from typing import Any, TypeVar, cast, overload

import httpx2
from pydantic import TypeAdapter
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from zrun.core.errors import (
    ServiceBadRequestError,
    ServiceCallError,
    ServiceNotFoundError,
    ServiceTimeoutError,
    ServiceUnavailableError,
)
from zrun.core.http.context import RequestContext

logger = logging.getLogger(__name__)

T = TypeVar("T")


@cache
def _type_adapter(model: Any) -> TypeAdapter[Any]:
    """Build and cache a TypeAdapter for a response model.

    TypeAdapter construction is not free; caching keeps per-request parsing
    allocation-free for repeated models.
    """
    return TypeAdapter(model)


# HTTP methods that are safe to retry (idempotent).
_IDEMPOTENT_METHODS = {"GET", "HEAD", "OPTIONS", "PUT", "DELETE"}


def _map_http_error(
    exc: httpx2.HTTPStatusError,
    *,
    service_name: str,
) -> ServiceCallError:
    """Map an httpx2 HTTP status error to the appropriate ServiceCallError subtype."""
    status = exc.response.status_code
    body = exc.response.text

    if status == 404:
        return ServiceNotFoundError(
            f"Resource not found from {service_name}",
            service_name=service_name,
            response_body=body,
        )
    if 400 <= status < 500:
        return ServiceBadRequestError(
            f"{service_name} returned {status}",
            service_name=service_name,
            status_code=status,
            response_body=body,
        )
    if status >= 500:
        return ServiceUnavailableError(
            f"{service_name} returned {status}",
            service_name=service_name,
        )
    return ServiceCallError(
        f"{service_name} returned {status}",
        service_name=service_name,
        status_code=status,
        response_body=body,
    )


def _map_transport_error(
    exc: httpx2.TransportError,
    *,
    service_name: str,
) -> ServiceCallError:
    """Map an httpx2 transport error to the appropriate ServiceCallError subtype."""
    if isinstance(exc, httpx2.TimeoutException):
        return ServiceTimeoutError(
            f"Call to {service_name} timed out",
            service_name=service_name,
        )
    return ServiceUnavailableError(
        f"Cannot reach {service_name}: {exc}",
        service_name=service_name,
    )


class BaseServiceClient:
    """Base class for typed service-to-service HTTP clients.

    Subclasses implement domain-specific methods that call `request()`
    with the appropriate path, method, and response model.
    """

    def __init__(
        self,
        base_url: str,
        *,
        service_name: str,
        timeout: float = 10.0,
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
        max_retries: int = 3,
        retry_min_delay: float = 0.1,
        retry_max_delay: float = 5.0,
        transport: httpx2.AsyncBaseTransport | None = None,
    ) -> None:
        self.service_name = service_name
        self._max_retries = max_retries
        self._retry_min_delay = retry_min_delay
        self._retry_max_delay = retry_max_delay
        self._client = httpx2.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            transport=transport,
            limits=httpx2.Limits(
                max_connections=max_connections,
                max_keepalive_connections=max_keepalive_connections,
            ),
        )

    async def aclose(self) -> None:
        """Close the underlying HTTP client and release connections."""
        await self._client.aclose()

    async def request(
        self,
        method: str,
        path: str,
        *,
        ctx: RequestContext | None = None,
        response_model: type[T] | None = None,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> T:
        """Make an HTTP request to the downstream service.

        Idempotent methods (GET, PUT, DELETE, etc.) are retried on
        transient failures (5xx, network errors). Non-idempotent methods
        (POST, PATCH) are never retried.

        Args:
            method: HTTP method (uppercase).
            path: URL path relative to base_url.
            ctx: Request context for header propagation.
            response_model: Pydantic model (or builtin type) to parse the
                response body into. If None, returns the raw httpx2.Response.
            json: JSON request body.
            params: Query parameters.
            headers: Additional request headers (merged with ctx headers).

        Returns:
            Parsed response if response_model is provided, else httpx2.Response.

        Raises:
            ServiceCallError: Subtype indicating the failure mode.
        """
        merged_headers = {**(ctx.to_headers() if ctx else {}), **(headers or {})}

        if self._should_retry(method):
            return await self._request_with_retry(
                method,
                path,
                merged_headers,
                json,
                params,
                response_model,
            )
        return await self._request_once(
            method,
            path,
            merged_headers,
            json,
            params,
            response_model,
        )

    def _should_retry(self, method: str) -> bool:
        return method.upper() in _IDEMPOTENT_METHODS and self._max_retries > 0

    async def _request_once(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        json_body: dict[str, Any] | None,
        params: dict[str, Any] | None,
        response_model: type[T] | None,
    ) -> T:
        try:
            response = await self._client.request(
                method,
                path,
                headers=headers,
                json=json_body,
                params=params,
            )
        except httpx2.TransportError as exc:
            raise _map_transport_error(exc, service_name=self.service_name) from exc

        try:
            response.raise_for_status()
        except httpx2.HTTPStatusError as exc:
            raise _map_http_error(exc, service_name=self.service_name) from exc

        return cast(T, self._parse_response(response, response_model))

    async def _request_with_retry(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        json_body: dict[str, Any] | None,
        params: dict[str, Any] | None,
        response_model: type[T] | None,
    ) -> T:
        """Wrap _request_once with exponential-backoff retry."""
        result: T | None = None
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(
                multiplier=1, min=self._retry_min_delay, max=self._retry_max_delay
            ),
            retry=retry_if_exception_type((ServiceUnavailableError, ServiceTimeoutError)),
            reraise=True,
        ):
            with attempt:
                if attempt.retry_state.attempt_number > 1:
                    logger.warning(
                        "Retrying %s %s (attempt %d/%d)",
                        method,
                        path,
                        attempt.retry_state.attempt_number,
                        self._max_retries,
                        extra={"service": self.service_name},
                    )
                result = await self._request_once(
                    method,
                    path,
                    headers,
                    json_body,
                    params,
                    response_model,
                )
        # The loop always returns inside `with attempt:` or raises.
        # This assert satisfies type checkers.
        assert result is not None
        return result

    @staticmethod
    @overload
    def _parse_response(
        response: httpx2.Response, response_model: None = None
    ) -> httpx2.Response: ...

    @staticmethod
    @overload
    def _parse_response(response: httpx2.Response, response_model: type[T]) -> T: ...

    @staticmethod
    def _parse_response(
        response: httpx2.Response,
        response_model: type[T] | None = None,
    ) -> T | httpx2.Response:
        """Parse response body into a model, or return raw response."""
        if response_model is None:
            return response
        return _type_adapter(response_model).validate_python(response.json())
