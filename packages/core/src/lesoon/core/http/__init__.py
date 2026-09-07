"""Shared HTTP infrastructure for service-to-service communication."""

from lesoon.core.http.base_client import BaseServiceClient
from lesoon.core.http.context import RequestContext
from lesoon.core.http.feign import delete, get, patch, post, put

__all__ = [
    "BaseServiceClient",
    "RequestContext",
    "delete",
    "get",
    "patch",
    "post",
    "put",
]
