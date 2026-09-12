import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import DbSession, require_api_key
from app.db.models import IntegrationStatus
from app.schemas.common import Page
from app.schemas.integration import IntegrationCreate, IntegrationRead, IntegrationUpdate
from app.services import integration_service

router = APIRouter(
    prefix="/integrations", tags=["integrations"], dependencies=[Depends(require_api_key)]
)


@router.post("", response_model=IntegrationRead, status_code=status.HTTP_201_CREATED)
def create_integration(data: IntegrationCreate, db: DbSession) -> IntegrationRead:
    return integration_service.create_integration(db, data)


@router.get("", response_model=Page[IntegrationRead])
def list_integrations(
    db: DbSession,
    status: IntegrationStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[IntegrationRead]:
    items, total = integration_service.list_integrations(
        db, status=status, limit=limit, offset=offset
    )
    return Page(items=items, limit=limit, offset=offset, total=total)


@router.get("/{integration_id}", response_model=IntegrationRead)
def get_integration(integration_id: uuid.UUID, db: DbSession) -> IntegrationRead:
    return integration_service.get_integration(db, integration_id)


@router.patch("/{integration_id}", response_model=IntegrationRead)
def update_integration(
    integration_id: uuid.UUID, data: IntegrationUpdate, db: DbSession
) -> IntegrationRead:
    return integration_service.update_integration(db, integration_id, data)


@router.delete("/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_integration(integration_id: uuid.UUID, db: DbSession) -> None:
    integration_service.delete_integration(db, integration_id)
