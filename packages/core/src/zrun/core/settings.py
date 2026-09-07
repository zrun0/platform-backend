"""Shared settings types for zrun services."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConnectionPoolSettings:
    """HTTP connection pool settings shared across service clients.

    Bundles the two pool knobs that always travel together so they can
    be passed as one unit from settings objects to client constructors.
    """

    max_connections: int = 100
    max_keepalive_connections: int = 20
