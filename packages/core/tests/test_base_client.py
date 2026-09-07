"""Tests for BaseServiceClient response parsing contracts."""

from __future__ import annotations

import httpx2
import pytest
from pydantic import BaseModel
from zrun_test_utils import MockRouter
from zrun_test_utils.helpers import ok_response

from zrun.core.errors import ServiceResponseError
from zrun.core.http.base_client import BaseServiceClient

BASE_URL = "https://downstream.test"


class Toy(BaseModel):
    id: str


@pytest.fixture
def client(mock_router: MockRouter) -> BaseServiceClient:
    return BaseServiceClient(
        base_url=BASE_URL,
        service_name="toy",
        max_retries=1,
        transport=mock_router,
    )


async def test_parses_body_into_model(client: BaseServiceClient, mock_router: MockRouter) -> None:
    """A JSON body is validated into the declared model."""
    mock_router.get(f"{BASE_URL}/toys/1").return_value = ok_response({"id": "1"})

    result = await client.request("GET", "/toys/1", response_model=Toy)

    assert isinstance(result, Toy)
    assert result.id == "1"


async def test_optional_model_empty_body_maps_to_none(
    client: BaseServiceClient, mock_router: MockRouter
) -> None:
    """`Model | None` maps an empty (204) body to None."""
    mock_router.get(f"{BASE_URL}/toys/1").return_value = httpx2.Response(204)

    result = await client.request("GET", "/toys/1", response_model=Toy | None)

    assert result is None


async def test_optional_model_json_null_body_maps_to_none(
    client: BaseServiceClient, mock_router: MockRouter
) -> None:
    """`Model | None` maps a literal JSON null body (b"null") to None."""
    # A literal null body, distinct from an empty one: json=None in the
    # Response constructor is the no-body sentinel, so use raw content.
    mock_router.get(f"{BASE_URL}/toys/1").return_value = httpx2.Response(200, content=b"null")

    result = await client.request("GET", "/toys/1", response_model=Toy | None)

    assert result is None


async def test_optional_model_parses_present_body(
    client: BaseServiceClient, mock_router: MockRouter
) -> None:
    """`Model | None` still parses a present body into the model."""
    mock_router.get(f"{BASE_URL}/toys/1").return_value = ok_response({"id": "1"})

    result = await client.request("GET", "/toys/1", response_model=Toy | None)

    assert isinstance(result, Toy)


async def test_unreadable_body_raises_service_response_error(
    client: BaseServiceClient, mock_router: MockRouter
) -> None:
    """A 2xx body that is not JSON maps to ServiceResponseError with 502."""
    mock_router.get(f"{BASE_URL}/toys/1").return_value = httpx2.Response(200, text="not-json")

    with pytest.raises(ServiceResponseError) as exc_info:
        await client.request("GET", "/toys/1", response_model=Toy)

    assert exc_info.value.service_name == "toy"
    assert exc_info.value.status_code == 502
    assert exc_info.value.response_body == "not-json"


async def test_contract_violating_body_raises_service_response_error(
    client: BaseServiceClient, mock_router: MockRouter
) -> None:
    """Valid JSON that fails model validation is also a contract violation."""
    mock_router.get(f"{BASE_URL}/toys/1").return_value = ok_response({"wrong": "shape"})

    with pytest.raises(ServiceResponseError) as exc_info:
        await client.request("GET", "/toys/1", response_model=Toy)

    assert exc_info.value.status_code == 502


async def test_response_error_not_retried(mock_router: MockRouter) -> None:
    """Contract violations are deterministic and must not be retried."""
    no_retry = BaseServiceClient(
        base_url=BASE_URL,
        service_name="toy",
        max_retries=3,
        transport=mock_router,
    )
    route = mock_router.get(f"{BASE_URL}/toys/1")
    route.return_value = httpx2.Response(200, text="not-json")

    with pytest.raises(ServiceResponseError):
        await no_retry.request("GET", "/toys/1", response_model=Toy)

    assert len(route.calls) == 1
