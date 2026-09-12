import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AuthType(enum.StrEnum):
    NONE = "NONE"
    API_KEY = "API_KEY"
    BEARER_TOKEN = "BEARER_TOKEN"
    OAUTH2_CLIENT_CREDENTIALS = "OAUTH2_CLIENT_CREDENTIALS"


class IntegrationStatus(enum.StrEnum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"


# Enums are stored as plain VARCHAR rather than native Postgres ENUM types: adding a
# value is then a no-op migration instead of an ALTER TYPE, and the values are already
# validated by Pydantic at the API boundary.
def enum_column(enum_cls: type[enum.Enum]) -> Enum:
    return Enum(enum_cls, native_enum=False, length=40)


class Integration(Base):
    __tablename__ = "integrations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[str | None] = mapped_column(Text)

    base_url: Mapped[str] = mapped_column(String(2048))
    auth_type: Mapped[AuthType] = mapped_column(enum_column(AuthType))
    # Non-secret headers sent on every request to this integration (e.g. Accept,
    # a tenant id). Authorization is never stored here — it comes from the credential.
    default_headers: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict)
    # Overrides the global HTTP_TIMEOUT_SECONDS when set.
    timeout_seconds: Mapped[float | None]

    # Operator-controlled. PAUSED blocks request execution.
    status: Mapped[IntegrationStatus] = mapped_column(
        enum_column(IntegrationStatus), default=IntegrationStatus.ACTIVE
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
