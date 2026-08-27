"""BFF service application factory."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from zrun.bff.api.routes import router
from zrun.bff.settings import Settings
from zrun.core.errors import (
    ServiceBadRequestError,
    ServiceCallError,
    ServiceNotFoundError,
    ServiceTimeoutError,
    ServiceUnavailableError,
)
from zrun.core.middleware import RequestIDMiddleware
from zrun.flow_api import FlowServiceClient
from zrun.uc_api import UcServiceClient


@dataclass
class AppClients:
    """Container for shared downstream service clients."""

    flow: FlowServiceClient
    uc: UcServiceClient


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Manage service client lifecycle.

    Creates shared client instances on startup and gracefully closes
    HTTP connections on shutdown.
    """
    settings: Settings = app.state.settings

    flow_client = FlowServiceClient(
        base_url=settings.flow_api_base_url,
        timeout=settings.flow_timeout,
        max_connections=settings.max_connections,
        max_keepalive_connections=settings.max_keepalive_connections,
    )
    uc_client = UcServiceClient(
        base_url=settings.uc_api_base_url,
        timeout=settings.uc_timeout,
        max_connections=settings.max_connections,
        max_keepalive_connections=settings.max_keepalive_connections,
    )

    app.state.clients = AppClients(flow=flow_client, uc=uc_client)

    try:
        yield
    finally:
        await flow_client.aclose()
        await uc_client.aclose()


def _service_error_status(exc: ServiceCallError) -> int:
    """Map a ServiceCallError to the appropriate HTTP status code."""
    if isinstance(exc, ServiceTimeoutError):
        return 504
    if isinstance(exc, ServiceUnavailableError):
        return 502
    if isinstance(exc, ServiceNotFoundError):
        return 404
    if isinstance(exc, ServiceBadRequestError):
        return exc.status_code or 400
    return 502


def _register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers for downstream errors."""

    @app.exception_handler(ServiceCallError)
    async def service_call_error_handler(
        request: Request,
        exc: ServiceCallError,
    ) -> JSONResponse:
        status = _service_error_status(exc)
        return JSONResponse(
            status_code=status,
            content={
                "error": exc.__class__.__name__,
                "message": exc.message,
                "service": exc.service_name,
                "status_code": exc.status_code,
            },
        )


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the FastAPI application for the BFF service."""
    settings = settings or Settings()
    app = FastAPI(title=settings.service_name, lifespan=lifespan)
    app.state.settings = settings

    app.add_middleware(RequestIDMiddleware)
    _register_exception_handlers(app)
    app.include_router(router)

    return app


app = create_app()
