"""Flow service application factory."""

from fastapi import FastAPI

from zrun.core.middleware import RequestIDMiddleware
from zrun.flow.api.routes import router
from zrun.flow.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the FastAPI application for the Flow service."""
    settings = settings or Settings()
    app = FastAPI(title=settings.service_name)
    app.add_middleware(RequestIDMiddleware)
    app.include_router(router)
    return app


app = create_app()
