"""Shared HTTP infrastructure for service-to-service communication."""

from zrun.core.http.base_client import BaseServiceClient
from zrun.core.http.context import RequestContext
from zrun.core.http.feign import delete, get, patch, post, put

__all__ = [
    "BaseServiceClient",
    "RequestContext",
    "delete",
    "get",
    "patch",
    "post",
    "put",
]
