"""Unit tests for service error mapping and error hierarchy."""

from __future__ import annotations

import pytest

from lesoon.core.errors import (
    AppError,
    ServiceBadRequestError,
    ServiceCallError,
    ServiceNotFoundError,
    ServiceTimeoutError,
    ServiceUnavailableError,
)
from lesoon.core.service_error_handlers import map_service_error_to_status

# ---------------------------------------------------------------------------
# Error hierarchy — inheritance relationships
# ---------------------------------------------------------------------------


def test_all_service_errors_are_app_errors() -> None:
    """Every Service*Error must be a subclass of AppError (via ServiceCallError)."""
    assert issubclass(ServiceCallError, AppError)
    assert issubclass(ServiceTimeoutError, AppError)
    assert issubclass(ServiceUnavailableError, AppError)
    assert issubclass(ServiceBadRequestError, AppError)
    assert issubclass(ServiceNotFoundError, AppError)


def test_all_service_errors_are_call_errors() -> None:
    """Every concrete service error must be a subclass of ServiceCallError."""
    assert issubclass(ServiceTimeoutError, ServiceCallError)
    assert issubclass(ServiceUnavailableError, ServiceCallError)
    assert issubclass(ServiceBadRequestError, ServiceCallError)
    assert issubclass(ServiceNotFoundError, ServiceCallError)


def test_not_found_is_not_bad_request() -> None:
    """ServiceNotFoundError must NOT be a subclass of ServiceBadRequestError.

    404 and 400 are distinct error categories. A 404 is not a kind of
    "bad request" — the request was well-formed, the resource just
    doesn't exist.
    """
    assert not issubclass(ServiceNotFoundError, ServiceBadRequestError)
    not_found = ServiceNotFoundError(service_name="uc")
    assert not isinstance(not_found, ServiceBadRequestError)


# ---------------------------------------------------------------------------
# Status code mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (ServiceTimeoutError(service_name="flow"), 504),
        (ServiceUnavailableError(service_name="flow"), 502),
        (ServiceNotFoundError(service_name="uc"), 404),
        (ServiceBadRequestError(service_name="uc"), 400),
        (ServiceBadRequestError(service_name="uc", status_code=422), 422),
        (ServiceCallError(service_name="uc"), 502),  # base class fallback
    ],
)
def test_map_service_error_to_status(error: ServiceCallError, expected_status: int) -> None:
    """Each error subclass maps to the correct HTTP status code."""
    assert map_service_error_to_status(error) == expected_status


def test_service_not_found_default_fields() -> None:
    """ServiceNotFoundError should carry status_code=404 and service_name."""
    err = ServiceNotFoundError(service_name="uc")
    assert err.status_code == 404
    assert err.service_name == "uc"
    assert err.response_body is None


def test_service_bad_request_default_fields() -> None:
    """ServiceBadRequestError defaults to status_code=400."""
    err = ServiceBadRequestError(service_name="uc")
    assert err.status_code == 400
    assert err.service_name == "uc"
