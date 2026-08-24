"""UC service configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Runtime settings for the UC service."""

    service_name: str = "zrun-uc"
