import json
import logging
import uuid

from pydantic import SecretStr
from sqlalchemy.orm import Session

from app.core import security
from app.core.exceptions import ConflictError, NotFoundError
from app.db.models import AuthType, Credential
from app.schemas.credential import CredentialIn
from app.services.integration_service import get_integration

logger = logging.getLogger(__name__)


def set_credential(
    db: Session, integration_id: uuid.UUID, data: CredentialIn
) -> tuple[Credential, bool]:
    """Create or replace the integration's credential. Returns (credential, created)."""
    integration = get_integration(db, integration_id)

    if integration.auth_type == AuthType.NONE:
        raise ConflictError("Integration does not use authentication (auth_type is NONE)")
    if data.auth_type != integration.auth_type:
        raise ConflictError(
            f"Credential type {data.auth_type.value} does not match "
            f"integration auth_type {integration.auth_type.value}"
        )

    config, secret = _split_secret(data)
    encrypted_secret = security.encrypt(json.dumps(secret))

    credential = integration.credential
    created = credential is None
    if created:
        credential = Credential(integration=integration)
        db.add(credential)
    credential.config = config
    credential.encrypted_secret = encrypted_secret

    db.commit()
    db.refresh(credential)

    logger.info(
        "credential %s",
        "created" if created else "replaced",
        extra={"integration_id": str(integration_id), "auth_type": integration.auth_type.value},
    )
    return credential, created


def get_credential(db: Session, integration_id: uuid.UUID) -> Credential:
    credential = get_integration(db, integration_id).credential
    if credential is None:
        raise NotFoundError("Credential for integration", integration_id)
    return credential


def delete_credential(db: Session, integration_id: uuid.UUID) -> None:
    db.delete(get_credential(db, integration_id))
    db.commit()
    logger.info("credential deleted", extra={"integration_id": str(integration_id)})


def decrypt_secret(credential: Credential) -> dict[str, str]:
    return json.loads(security.decrypt(credential.encrypted_secret))


def _split_secret(data: CredentialIn) -> tuple[dict[str, str], dict[str, str]]:
    # The schema decides what is secret: SecretStr fields get encrypted, the rest is
    # plain config that can be returned from the API.
    config: dict[str, str] = {}
    secret: dict[str, str] = {}
    for name, value in data:
        if name == "auth_type":
            continue
        if isinstance(value, SecretStr):
            secret[name] = value.get_secret_value()
        else:
            config[name] = value
    return config, secret
