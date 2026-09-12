def test_missing_api_key_is_rejected(anonymous_client):
    response = anonymous_client.get("/integrations")

    assert response.status_code == 401
    assert response.json() == {"detail": "Missing or invalid API key"}


def test_wrong_api_key_is_rejected(anonymous_client):
    response = anonymous_client.get("/integrations", headers={"X-API-Key": "nope"})

    assert response.status_code == 401


def test_health_does_not_require_api_key(anonymous_client):
    assert anonymous_client.get("/health").status_code == 200
