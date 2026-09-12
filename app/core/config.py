from functools import lru_cache

from cryptography.fernet import Fernet
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+psycopg://integration_hub:integration_hub@localhost:5432/integration_hub"
    )

    # Fernet key used to encrypt credential secrets at rest.
    credential_encryption_key: str
    # Static key clients must send as X-API-Key to use this API.
    hub_api_key: str

    # Default timeout for outbound calls to external APIs. Can be overridden per request.
    http_timeout_seconds: float = 10.0

    log_level: str = "INFO"

    @field_validator("credential_encryption_key")
    @classmethod
    def _must_be_valid_fernet_key(cls, value: str) -> str:
        # Fail at startup instead of on the first credential write.
        Fernet(value.encode())
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
