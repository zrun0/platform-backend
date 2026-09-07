"""Unit tests for BaseServiceClient connection-pool configuration."""

from __future__ import annotations

import pytest

from zrun.core.http.base_client import BaseServiceClient
from zrun.core.settings import ConnectionPoolSettings


def test_pool_and_kwargs_are_mutually_exclusive() -> None:
    """Passing both pool= and max_connections= must fail loudly, not silently override."""
    with pytest.raises(ValueError, match="not both"):
        BaseServiceClient(
            base_url="http://downstream.test",
            service_name="x",
            pool=ConnectionPoolSettings(),
            max_connections=5,
        )

    with pytest.raises(ValueError, match="not both"):
        BaseServiceClient(
            base_url="http://downstream.test",
            service_name="x",
            pool=ConnectionPoolSettings(),
            max_keepalive_connections=5,
        )


def test_constructs_with_default_pool_settings() -> None:
    """No pool args -> construction succeeds with ConnectionPoolSettings defaults."""
    client = BaseServiceClient(base_url="http://downstream.test", service_name="x")
    assert client.service_name == "x"


def test_constructs_with_explicit_pool() -> None:
    """pool= is accepted as the bundled way to configure connections."""
    client = BaseServiceClient(
        base_url="http://downstream.test",
        service_name="x",
        pool=ConnectionPoolSettings(max_connections=33, max_keepalive_connections=9),
    )
    assert client.service_name == "x"
