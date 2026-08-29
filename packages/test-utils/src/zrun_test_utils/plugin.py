"""Pytest plugin exposing shared fixtures via the pytest11 entry point.

Loaded automatically by pytest wherever zrun-test-utils is installed.
Opt out per-run with `-p no:zrun-test-utils`.
"""

from __future__ import annotations

import pytest

from zrun_test_utils.mock_router import MockRouter


@pytest.fixture
def mock_router() -> MockRouter:
    """HTTP mock transport; inject into downstream service clients via transport=."""
    return MockRouter()
