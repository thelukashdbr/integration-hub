import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.db.models import AuthType, IntegrationStatus


def normalize_base_url(value: str) -> str:
    url = HttpUrl(value)
    if url.query or url.fragment:
        raise ValueError("base_url must not contain a query string or fragment")
    return str(url).rstrip("/")


def validate_headers(headers: dict[str, str]) -> dict[str, str]:
    for name in headers:
        if name.lower() == "authorization":
            raise ValueError("Authorization is set from the integration's credential")
    return headers


class IntegrationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    base_url: str = Field(max_length=2048, examples=["https://api.example.com/v1"])
    auth_type: AuthType
    default_headers: dict[str, str] = Field(default_factory=dict)
    timeout_seconds: float | None = Field(default=None, gt=0, le=120)

    _normalize_base_url = field_validator("base_url")(normalize_base_url)
    _validate_headers = field_validator("default_headers")(validate_headers)


class IntegrationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    base_url: str | None = Field(default=None, max_length=2048)
    auth_type: AuthType | None = None
    default_headers: dict[str, str] | None = None
    timeout_seconds: float | None = Field(default=None, gt=0, le=120)
    status: IntegrationStatus | None = None

    @field_validator("base_url")
    @classmethod
    def _normalize_base_url(cls, value: str | None) -> str | None:
        return normalize_base_url(value) if value is not None else None

    @field_validator("default_headers")
    @classmethod
    def _validate_headers(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        return validate_headers(value) if value is not None else None


class IntegrationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    base_url: str
    auth_type: AuthType
    default_headers: dict[str, str]
    timeout_seconds: float | None
    status: IntegrationStatus
    created_at: datetime
    updated_at: datetime
