"""Shared fixtures for BFF endpoint tests."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from zrun_test_utils import MockRouter

from zrun.bff.main import AppClients, create_app
from zrun.bff.settings import Settings
from zrun.flow_api import FlowServiceClient
from zrun.uc_api import UcServiceClient


@pytest.fixture
def make_bff_client(mock_router: MockRouter) -> Callable[[Settings], TestClient]:
    """Factory for BFF test clients with both downstreams on the mock transport.

    TestClient doesn't trigger lifespan events, so downstream clients are
    wired here instead of in the app lifespan. The unused placeholder client
    exists because routes may touch either service.
    """

    def _make(settings: Settings) -> TestClient:
        app = create_app(settings)
        app.state.clients = AppClients(
            flow=FlowServiceClient(
                base_url=settings.flow_api_base_url,
                timeout=settings.flow_timeout,
                max_connections=settings.max_connections,
                max_keepalive_connections=settings.max_keepalive_connections,
                transport=mock_router,
            ),
            uc=UcServiceClient(
                base_url=settings.uc_api_base_url,
                timeout=settings.uc_timeout,
                max_connections=settings.max_connections,
                max_keepalive_connections=settings.max_keepalive_connections,
                transport=mock_router,
            ),
        )
        return TestClient(app)

    return _make
