"""Flow service application factory."""

from fastapi import FastAPI

from lesoon.core.app_factory import create_basic_app
from lesoon.flow.api.routes import router
from lesoon.flow.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the FastAPI application for the Flow service."""
    settings = settings or Settings()
    # Internal service: continue traces forwarded by the BFF so spans join.
    return create_basic_app(settings=settings, router=router, trust_inbound_trace=True)


app = create_app()
