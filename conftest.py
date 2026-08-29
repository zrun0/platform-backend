"""Shared pytest fixtures for the whole workspace."""

from __future__ import annotations

import pytest
from zrun_test_utils import MockRouter


@pytest.fixture
def mock_router() -> MockRouter:
    """HTTP mock transport; inject into downstream service clients via transport=."""
    return MockRouter()
