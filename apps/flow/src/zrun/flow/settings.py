"""Flow service configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Runtime settings for the Flow service."""

    service_name: str = "zrun-flow"
