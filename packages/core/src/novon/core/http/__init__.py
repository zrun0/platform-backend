"""Shared HTTP infrastructure for service-to-service communication."""

from novon.core.http.base_client import BaseServiceClient
from novon.core.http.context import RequestContext
from novon.core.http.feign import delete, get, patch, post, put

__all__ = [
    "BaseServiceClient",
    "RequestContext",
    "delete",
    "get",
    "patch",
    "post",
    "put",
]
