from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from app.api.deps import DbSession, require_api_key
from app.db.models import IntegrationStatus
from app.schemas.common import Page
from app.schemas.integration import IntegrationCreate, IntegrationRead, IntegrationUpdate
from app.services import integration_service

router = APIRouter(
    prefix="/integrations", tags=["integrations"], dependencies=[Depends(require_api_key)]
)

IntegrationRef = Annotated[str, Path(description="Integration id (UUID) or slug")]


@router.post("", response_model=IntegrationRead, status_code=status.HTTP_201_CREATED)
def create_integration(data: IntegrationCreate, db: DbSession) -> IntegrationRead:
    return integration_service.create_integration(db, data)


@router.get("", response_model=Page[IntegrationRead])
def list_integrations(
    db: DbSession,
    name: Annotated[str | None, Query(description="Case-insensitive partial match")] = None,
    status: IntegrationStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[IntegrationRead]:
    items, total = integration_service.list_integrations(
        db, name=name, status=status, limit=limit, offset=offset
    )
    return Page(items=items, limit=limit, offset=offset, total=total)


@router.get("/{integration_ref}", response_model=IntegrationRead)
def get_integration(integration_ref: IntegrationRef, db: DbSession) -> IntegrationRead:
    return integration_service.get_integration(db, integration_ref)


@router.patch("/{integration_ref}", response_model=IntegrationRead)
def update_integration(
    integration_ref: IntegrationRef, data: IntegrationUpdate, db: DbSession
) -> IntegrationRead:
    return integration_service.update_integration(db, integration_ref, data)


@router.delete("/{integration_ref}", status_code=status.HTTP_204_NO_CONTENT)
def delete_integration(integration_ref: IntegrationRef, db: DbSession) -> None:
    integration_service.delete_integration(db, integration_ref)
