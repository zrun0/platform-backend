"""Shared test utilities for HTTP response mocking.

This module provides helper functions to create httpx.Response objects
for testing purposes. These are particularly useful when mocking HTTP
clients in unit and integration tests.
"""

from typing import Any

import httpx


def ok_response(data: dict[str, Any] | list[Any], *, status: int = 200) -> httpx.Response:
    """Create a successful HTTP response for testing.

    Args:
        data: Response body as JSON-serializable dict or list
        status: HTTP status code (default: 200)

    Returns:
        An httpx.Response object with the provided data and status

    Example:
        >>> response = ok_response({"user": "alice"})
        >>> response.status_code == 200
        True
        >>> response.json() == {"user": "alice"}
        True
    """
    return httpx.Response(status, json=data)


def error_response(detail: str, *, status: int = 404) -> httpx.Response:
    """Create an error HTTP response for testing.

    Args:
        detail: Error message describing what went wrong
        status: HTTP error status code (default: 404)

    Returns:
        An httpx.Response object with error detail and status

    Example:
        >>> response = error_response("User not found", status=404)
        >>> response.status_code == 404
        True
        >>> response.json() == {"detail": "User not found"}
        True
    """
    return httpx.Response(status, json={"detail": detail})
