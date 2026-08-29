"""Shared FastAPI application factory utilities."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Any, Protocol

from fastapi import APIRouter, FastAPI

from zrun.core.middleware import RequestIDMiddleware

type Lifespan = Callable[[FastAPI], AbstractAsyncContextManager[Any]]


class ServiceSettings(Protocol):
    """Protocol for settings objects expected by create_basic_app."""

    service_name: str


def create_basic_app(
    settings: ServiceSettings,
    router: APIRouter,
    *,
    lifespan: Lifespan | None = None,
) -> FastAPI:
    """Create a basic FastAPI application with standard setup.

    This factory provides a consistent pattern for creating FastAPI applications
    across all zrun services, handling common setup like middleware registration
    and router inclusion.

    Args:
        settings: Application settings with at least a service_name field
        router: Main API router to include in the application
        lifespan: Optional lifespan context manager for startup/shutdown hooks

    Returns:
        Configured FastAPI application ready for use

    Example:
        >>> from zrun.core.app_factory import create_basic_app
        >>> app = create_basic_app(settings=settings, router=router)
    """
    app = FastAPI(title=settings.service_name, lifespan=lifespan)
    app.state.settings = settings

    # Standard middleware - always included
    app.add_middleware(RequestIDMiddleware)

    app.include_router(router)
    return app
