"""BFF service configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Runtime settings for the BFF service."""

    service_name: str = "zrun-bff"

    # Downstream service base URLs.
    flow_api_base_url: str = "http://127.0.0.1:8001"
    uc_api_base_url: str = "http://127.0.0.1:8002"

    # Per-service timeouts (seconds).
    flow_timeout: float = 30.0
    uc_timeout: float = 10.0

    # Connection pool settings.
    max_connections: int = 100
    max_keepalive_connections: int = 20
