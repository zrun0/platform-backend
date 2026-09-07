"""UC service application factory."""

from fastapi import FastAPI

from zrun.core.app_factory import create_basic_app
from zrun.uc.api.routes import router
from zrun.uc.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the FastAPI application for the UC service."""
    settings = settings or Settings()
    # Internal service: continue traces forwarded by the BFF so spans join.
    return create_basic_app(settings=settings, router=router, trust_inbound_trace=True)


app = create_app()
