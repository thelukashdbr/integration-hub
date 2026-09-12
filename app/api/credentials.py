from fastapi import APIRouter, Depends, Response, status

from app.api.deps import DbSession, require_api_key
from app.api.integrations import IntegrationRef
from app.schemas.credential import CredentialIn, CredentialRead
from app.services import credential_service

router = APIRouter(
    prefix="/integrations/{integration_ref}/credential",
    tags=["credentials"],
    dependencies=[Depends(require_api_key)],
)


@router.put("", response_model=CredentialRead, responses={201: {"model": CredentialRead}})
def set_credential(
    integration_ref: IntegrationRef, data: CredentialIn, db: DbSession, response: Response
) -> CredentialRead:
    """Create or replace the integration's credential. The secret is encrypted at rest
    and never returned."""
    credential, created = credential_service.set_credential(db, integration_ref, data)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return credential


@router.get("", response_model=CredentialRead)
def get_credential(integration_ref: IntegrationRef, db: DbSession) -> CredentialRead:
    return credential_service.get_credential(db, integration_ref)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_credential(integration_ref: IntegrationRef, db: DbSession) -> None:
    credential_service.delete_credential(db, integration_ref)
