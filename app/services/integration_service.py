import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.db.models import Integration, IntegrationStatus
from app.schemas.integration import IntegrationCreate, IntegrationUpdate


def create_integration(db: Session, data: IntegrationCreate) -> Integration:
    integration = Integration(**data.model_dump())
    db.add(integration)
    _commit_or_conflict(db, integration.name)
    db.refresh(integration)
    return integration


def list_integrations(
    db: Session,
    status: IntegrationStatus | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Integration], int]:
    filters = [Integration.status == status] if status else []

    total = db.execute(select(func.count()).select_from(Integration).where(*filters)).scalar_one()
    items = db.execute(
        select(Integration)
        .where(*filters)
        .order_by(Integration.created_at.desc(), Integration.id)
        .limit(limit)
        .offset(offset)
    ).scalars()
    return list(items), total


def get_integration(db: Session, integration_id: uuid.UUID) -> Integration:
    integration = db.get(Integration, integration_id)
    if integration is None:
        raise NotFoundError("Integration", integration_id)
    return integration


def update_integration(
    db: Session, integration_id: uuid.UUID, data: IntegrationUpdate
) -> Integration:
    integration = get_integration(db, integration_id)
    updates = data.model_dump(exclude_unset=True)

    # The stored credential only makes sense for the auth type it was created for.
    # Refusing is safer than silently discarding a secret.
    if (
        "auth_type" in updates
        and updates["auth_type"] != integration.auth_type
        and integration.credential is not None
    ):
        raise ConflictError("Delete the integration's credential before changing auth_type")

    for field, value in updates.items():
        setattr(integration, field, value)
    _commit_or_conflict(db, integration.name)
    db.refresh(integration)
    return integration


def delete_integration(db: Session, integration_id: uuid.UUID) -> None:
    db.delete(get_integration(db, integration_id))
    db.commit()


def _commit_or_conflict(db: Session, name: str) -> None:
    # The unique constraint is the source of truth for name uniqueness; checking
    # first would leave a window between the check and the insert.
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError(f"An integration named '{name}' already exists") from None
