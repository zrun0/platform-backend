"""Shared exception handlers for service-to-service communication."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from zrun.core.errors import (
    ServiceBadRequestError,
    ServiceCallError,
    ServiceNotFoundError,
    ServiceTimeoutError,
    ServiceUnavailableError,
)


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
    return 502


def register_service_error_handlers(app: FastAPI) -> None:
    """Register standard ServiceCallError exception handlers.

    This registers a global exception handler that converts ServiceCallError
    instances into appropriate HTTP responses with consistent error format.

    Args:
        app: FastAPI application to register handlers on

    Example:
        >>> from fastapi import FastAPI
        >>> from zrun.core.service_error_handlers import register_service_error_handlers
        >>> app = FastAPI()
        >>> register_service_error_handlers(app)
    """

    @app.exception_handler(ServiceCallError)
    async def service_call_error_handler(
        request: Request,  # noqa: ARG001 - required by FastAPI interface
        exc: ServiceCallError,
    ) -> JSONResponse:
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
