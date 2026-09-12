import logging
import uuid

from sqlalchemy import select

from app.db.models import Credential
from app.services.credential_service import decrypt_secret

API_KEY_CREDENTIAL = {
    "auth_type": "API_KEY",
    "header_name": "X-Api-Key",
    "api_key": "sk_live_abc123",
}


def url(integration: dict) -> str:
    return f"/integrations/{integration['id']}/credential"


def test_set_credential_never_returns_the_secret(client, integration):
    response = client.put(url(integration), json=API_KEY_CREDENTIAL)

    assert response.status_code == 201
    body = response.json()
    assert body["integration_id"] == integration["id"]
    assert body["auth_type"] == "API_KEY"
    assert body["config"] == {"header_name": "X-Api-Key"}
    assert "sk_live_abc123" not in response.text
    assert "api_key" not in body


def test_set_credential_again_replaces_it(client, integration):
    first = client.put(url(integration), json=API_KEY_CREDENTIAL)
    second = client.put(url(integration), json={**API_KEY_CREDENTIAL, "header_name": "Api-Key"})

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert client.get(url(integration)).json()["config"] == {"header_name": "Api-Key"}


def test_secret_is_encrypted_at_rest(client, integration, db):
    client.put(url(integration), json=API_KEY_CREDENTIAL)

    stored = db.execute(select(Credential)).scalar_one()

    assert b"sk_live_abc123" not in stored.encrypted_secret
    assert decrypt_secret(stored) == {"api_key": "sk_live_abc123"}


def test_secret_is_never_logged(client, integration, caplog):
    with caplog.at_level(logging.DEBUG):
        client.put(url(integration), json=API_KEY_CREDENTIAL)

    assert any("credential created" in record.getMessage() for record in caplog.records)
    for record in caplog.records:
        assert "sk_live_abc123" not in record.getMessage()
        assert "sk_live_abc123" not in str(record.__dict__)


def test_set_credential_of_wrong_type_returns_409(client, integration):
    response = client.put(url(integration), json={"auth_type": "BEARER_TOKEN", "token": "t"})

    assert response.status_code == 409
    assert "API_KEY" in response.json()["detail"]


def test_set_credential_on_integration_without_auth_returns_409(client):
    integration = client.post(
        "/integrations",
        json={"name": "Public API", "base_url": "https://public.example.com", "auth_type": "NONE"},
    ).json()

    response = client.put(url(integration), json={"auth_type": "BEARER_TOKEN", "token": "t"})

    assert response.status_code == 409


def test_set_credential_validates_payload(client, integration):
    empty_key = client.put(url(integration), json={"auth_type": "API_KEY", "api_key": ""})
    bad_header = client.put(
        url(integration),
        json={"auth_type": "API_KEY", "header_name": "X Api Key", "api_key": "k"},
    )
    unknown_type = client.put(url(integration), json={"auth_type": "BASIC", "user": "u"})

    assert empty_key.status_code == 422
    assert bad_header.status_code == 422
    assert unknown_type.status_code == 422


def test_set_credential_for_missing_integration_returns_404(client):
    response = client.put(f"/integrations/{uuid.uuid4()}/credential", json=API_KEY_CREDENTIAL)

    assert response.status_code == 404


def test_get_credential_before_it_is_set_returns_404(client, integration):
    assert client.get(url(integration)).status_code == 404


def test_credential_routes_accept_slug(client, integration):
    response = client.put(
        f"/integrations/{integration['slug']}/credential", json=API_KEY_CREDENTIAL
    )

    assert response.status_code == 201
    assert response.json()["integration_id"] == integration["id"]
    assert client.get(f"/integrations/{integration['slug']}/credential").status_code == 200


def test_delete_credential(client, integration):
    client.put(url(integration), json=API_KEY_CREDENTIAL)

    response = client.delete(url(integration))

    assert response.status_code == 204
    assert client.get(url(integration)).status_code == 404


def test_deleting_integration_removes_its_credential(client, integration, db):
    client.put(url(integration), json=API_KEY_CREDENTIAL)

    client.delete(f"/integrations/{integration['id']}")

    assert db.execute(select(Credential)).scalars().all() == []


def test_changing_auth_type_with_credential_returns_409(client, integration):
    client.put(url(integration), json=API_KEY_CREDENTIAL)

    response = client.patch(
        f"/integrations/{integration['id']}", json={"auth_type": "BEARER_TOKEN"}
    )

    assert response.status_code == 409
    assert client.get(url(integration)).status_code == 200  # untouched


def test_changing_auth_type_without_credential_is_allowed(client, integration):
    response = client.patch(
        f"/integrations/{integration['id']}", json={"auth_type": "BEARER_TOKEN"}
    )

    assert response.status_code == 200
    assert response.json()["auth_type"] == "BEARER_TOKEN"
