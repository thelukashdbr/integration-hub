import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.db.models import Integration, IntegrationStatus
from app.schemas.integration import IntegrationCreate, IntegrationUpdate

# Postgres names for the unique constraints on integrations, used to tell the caller
# which field collided instead of a generic "conflict".
_UNIQUE_CONSTRAINTS = {
    "integrations_name_key": "name",
    "integrations_slug_key": "slug",
}


def create_integration(db: Session, data: IntegrationCreate) -> Integration:
    integration = Integration(**data.model_dump())
    db.add(integration)
    _commit_or_conflict(db)
    db.refresh(integration)
    return integration


def list_integrations(
    db: Session,
    name: str | None = None,
    status: IntegrationStatus | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Integration], int]:
    filters = []
    if name:
        filters.append(Integration.name.ilike(f"%{name}%"))
    if status:
        filters.append(Integration.status == status)

    total = db.execute(select(func.count()).select_from(Integration).where(*filters)).scalar_one()
    items = db.execute(
        select(Integration)
        .where(*filters)
        .order_by(Integration.created_at.desc(), Integration.id)
        .limit(limit)
        .offset(offset)
    ).scalars()
    return list(items), total


def get_integration(db: Session, ref: uuid.UUID | str) -> Integration:
    """`ref` is either the integration id or its slug."""
    try:
        integration = db.get(Integration, uuid.UUID(str(ref)))
    except ValueError:
        integration = db.execute(
            select(Integration).where(Integration.slug == ref)
        ).scalar_one_or_none()

    if integration is None:
        raise NotFoundError("Integration", ref)
    return integration


def update_integration(db: Session, ref: uuid.UUID | str, data: IntegrationUpdate) -> Integration:
    integration = get_integration(db, ref)
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
    _commit_or_conflict(db)
    db.refresh(integration)
    return integration


def delete_integration(db: Session, ref: uuid.UUID | str) -> None:
    db.delete(get_integration(db, ref))
    db.commit()


def _commit_or_conflict(db: Session) -> None:
    # The unique constraints are the source of truth; checking first would leave a
    # window between the check and the insert.
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        field = _UNIQUE_CONSTRAINTS.get(exc.orig.diag.constraint_name, "value")
        raise ConflictError(f"An integration with this {field} already exists") from None
