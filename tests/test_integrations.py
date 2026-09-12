import uuid

import pytest

VALID = {
    "name": "Payments API",
    "description": "Internal payments service",
    "base_url": "https://payments.example.com/v1",
    "auth_type": "API_KEY",
}


def test_create_integration(client):
    response = client.post("/integrations", json=VALID)

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Payments API"
    assert body["base_url"] == "https://payments.example.com/v1"
    assert body["auth_type"] == "API_KEY"
    assert body["status"] == "ACTIVE"
    assert body["default_headers"] == {}
    assert body["timeout_seconds"] is None
    assert uuid.UUID(body["id"])


def test_create_integration_normalizes_base_url(client):
    response = client.post(
        "/integrations", json={**VALID, "base_url": "HTTPS://Payments.Example.com/v1/"}
    )

    assert response.status_code == 201
    assert response.json()["base_url"] == "https://payments.example.com/v1"


@pytest.mark.parametrize(
    "base_url",
    ["not-a-url", "ftp://files.example.com", "https://payments.example.com/v1?env=prod"],
)
def test_create_integration_rejects_invalid_base_url(client, base_url):
    response = client.post("/integrations", json={**VALID, "base_url": base_url})

    assert response.status_code == 422


def test_create_integration_rejects_authorization_in_default_headers(client):
    response = client.post(
        "/integrations",
        json={**VALID, "default_headers": {"authorization": "Bearer leaked"}},
    )

    assert response.status_code == 422
    assert "credential" in response.text


def test_create_integration_with_duplicate_name_returns_409(client):
    client.post("/integrations", json=VALID)

    response = client.post("/integrations", json=VALID)

    assert response.status_code == 409


def test_get_integration(client):
    created = client.post("/integrations", json=VALID).json()

    response = client.get(f"/integrations/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_missing_integration_returns_404(client):
    response = client.get(f"/integrations/{uuid.uuid4()}")

    assert response.status_code == 404


def test_list_integrations_paginated(client):
    for i in range(3):
        client.post("/integrations", json={**VALID, "name": f"Integration {i}"})

    response = client.get("/integrations", params={"limit": 2})

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    assert body["total"] == 3
    assert body["limit"] == 2
    assert body["offset"] == 0


def test_list_integrations_filters_by_status(client):
    active = client.post("/integrations", json={**VALID, "name": "Active"}).json()
    paused = client.post("/integrations", json={**VALID, "name": "Paused"}).json()
    client.patch(f"/integrations/{paused['id']}", json={"status": "PAUSED"})

    response = client.get("/integrations", params={"status": "ACTIVE"})

    assert [i["id"] for i in response.json()["items"]] == [active["id"]]


def test_update_integration(client):
    created = client.post("/integrations", json=VALID).json()

    response = client.patch(
        f"/integrations/{created['id']}",
        json={
            "status": "PAUSED",
            "timeout_seconds": 5,
            "default_headers": {"Accept": "application/json"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "PAUSED"
    assert body["timeout_seconds"] == 5
    assert body["default_headers"] == {"Accept": "application/json"}
    assert body["name"] == "Payments API"  # untouched


def test_update_integration_to_existing_name_returns_409(client):
    client.post("/integrations", json={**VALID, "name": "First"})
    second = client.post("/integrations", json={**VALID, "name": "Second"}).json()

    response = client.patch(f"/integrations/{second['id']}", json={"name": "First"})

    assert response.status_code == 409


def test_delete_integration(client):
    created = client.post("/integrations", json=VALID).json()

    response = client.delete(f"/integrations/{created['id']}")

    assert response.status_code == 204
    assert client.get(f"/integrations/{created['id']}").status_code == 404


def test_delete_missing_integration_returns_404(client):
    response = client.delete(f"/integrations/{uuid.uuid4()}")

    assert response.status_code == 404
