import uuid

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import DbSession, require_api_key
from app.schemas.credential import CredentialIn, CredentialRead
from app.services import credential_service

router = APIRouter(
    prefix="/integrations/{integration_id}/credential",
    tags=["credentials"],
    dependencies=[Depends(require_api_key)],
)


@router.put("", response_model=CredentialRead, responses={201: {"model": CredentialRead}})
def set_credential(
    integration_id: uuid.UUID, data: CredentialIn, db: DbSession, response: Response
) -> CredentialRead:
    """Create or replace the integration's credential. The secret is encrypted at rest
    and never returned."""
    credential, created = credential_service.set_credential(db, integration_id, data)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return credential


@router.get("", response_model=CredentialRead)
def get_credential(integration_id: uuid.UUID, db: DbSession) -> CredentialRead:
    return credential_service.get_credential(db, integration_id)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_credential(integration_id: uuid.UUID, db: DbSession) -> None:
    credential_service.delete_credential(db, integration_id)
