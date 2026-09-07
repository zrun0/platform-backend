"""Shared exception handlers for service-to-service communication."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from lesoon.core.errors import (
    ServiceBadRequestError,
    ServiceCallError,
    ServiceNotFoundError,
    ServiceResponseError,
    ServiceTimeoutError,
    ServiceUnavailableError,
)

logger = logging.getLogger(__name__)


def map_service_error_to_status(exc: ServiceCallError) -> int:
    """Map ServiceCallError subtypes to HTTP status codes.

    Args:
        exc: ServiceCallError instance to map

    Returns:
        HTTP status code appropriate for the error type

    Example:
        >>> exc = ServiceTimeoutError(service_name="flow")
        >>> map_service_error_to_status(exc)
        504
    """
    if isinstance(exc, ServiceTimeoutError):
        return 504
    if isinstance(exc, ServiceUnavailableError):
        return 502
    if isinstance(exc, ServiceNotFoundError):
        return 404
    if isinstance(exc, ServiceBadRequestError):
        return exc.status_code or 400
    if isinstance(exc, ServiceResponseError):
        # A 2xx with an unreadable body: not an outage, but 502 (invalid
        # gateway payload) is the closest RFC status.
        return 502
    return 502


def register_service_error_handlers(app: FastAPI) -> None:
    """Register standard ServiceCallError exception handlers.

    This registers a global exception handler that converts ServiceCallError
    instances into appropriate HTTP responses with consistent error format.

    Args:
        app: FastAPI application to register handlers on

    Example:
        >>> from fastapi import FastAPI
        >>> from lesoon.core.service_error_handlers import register_service_error_handlers
        >>> app = FastAPI()
        >>> register_service_error_handlers(app)
    """

    @app.exception_handler(ServiceCallError)
    async def service_call_error_handler(
        request: Request,  # noqa: ARG001 - required by FastAPI interface
        exc: ServiceCallError,
    ) -> JSONResponse:
        if isinstance(exc, ServiceResponseError):
            # Contract violations are deterministic bugs, not load events:
            # log loudly (with a truncated body) so they stay
            # distinguishable from outages and diagnosable per endpoint.
            logger.error(
                "Downstream %s violated the response contract: %s; body=%r",
                exc.service_name,
                exc.message,
                (exc.response_body or "")[:1024],
            )
        status = map_service_error_to_status(exc)
        return JSONResponse(
            status_code=status,
            content={
                "error": exc.__class__.__name__,
                "message": exc.message,
                "service": exc.service_name,
                "status_code": exc.status_code,
            },
        )
