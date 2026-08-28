"""Flow service application factory."""

from fastapi import FastAPI

from zrun.core.app_factory import create_basic_app
from zrun.flow.api.routes import router
from zrun.flow.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the FastAPI application for the Flow service."""
    settings = settings or Settings()
    return create_basic_app(settings=settings, router=router)


app = create_app()
