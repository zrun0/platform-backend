"""BFF service configuration."""

from pydantic_settings import BaseSettings

from lesoon.core.settings import ConnectionPoolSettings


class Settings(BaseSettings):
    """Runtime settings for the BFF service."""

    service_name: str = "lesoon-bff"

    # Downstream service base URLs. Ports match the justfile dev recipes
    # (flow=8002, uc=8001); override with FLOW_API_BASE_URL / UC_API_BASE_URL.
    flow_api_base_url: str = "http://127.0.0.1:8002"
    uc_api_base_url: str = "http://127.0.0.1:8001"

    # Per-service timeouts (seconds).
    flow_timeout: float = 30.0
    uc_timeout: float = 10.0

    # Shared connection pool settings for all downstream clients.
    connection_pool: ConnectionPoolSettings = ConnectionPoolSettings()
