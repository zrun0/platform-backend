"""UC service application factory."""

from fastapi import FastAPI

from zrun.core.middleware import RequestIDMiddleware
from zrun.uc.api.routes import router
from zrun.uc.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the FastAPI application for the UC service."""
    settings = settings or Settings()
    app = FastAPI(title=settings.service_name)
    app.add_middleware(RequestIDMiddleware)
    app.include_router(router)
    return app


app = create_app()
