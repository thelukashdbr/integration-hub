import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from app.db.models import AuthType

# Secrets are typed as SecretStr so an accidental repr/log of the model prints
# '**********' instead of the value.


class ApiKeyCredential(BaseModel):
    auth_type: Literal[AuthType.API_KEY]
    header_name: str = Field(default="X-API-Key", pattern=r"^[A-Za-z0-9-]+$", max_length=100)
    api_key: SecretStr = Field(min_length=1)


class BearerTokenCredential(BaseModel):
    auth_type: Literal[AuthType.BEARER_TOKEN]
    token: SecretStr = Field(min_length=1)


CredentialIn = Annotated[ApiKeyCredential | BearerTokenCredential, Field(discriminator="auth_type")]


class CredentialRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    integration_id: uuid.UUID
    auth_type: AuthType
    config: dict[str, str]
    created_at: datetime
    updated_at: datetime
