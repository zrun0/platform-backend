"""BFF service application factory."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI

from zrun.bff.api.routes import router
from zrun.bff.settings import Settings
from zrun.core.app_factory import create_basic_app
from zrun.core.service_error_handlers import register_service_error_handlers
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


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the FastAPI application for the BFF service."""
    settings = settings or Settings()

    app = create_basic_app(settings=settings, router=router, lifespan=lifespan)
    register_service_error_handlers(app)

    return app


app = create_app()
