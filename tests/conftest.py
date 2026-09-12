import os

# The app reads its settings at import time, so the test environment has to be in
# place before anything under `app` is imported. Tests always run against a
# separate database; the encryption key below is a fixed, test-only Fernet key.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://integration_hub:integration_hub@localhost:5432/integration_hub_test",
)
os.environ.setdefault("CREDENTIAL_ENCRYPTION_KEY", "wAjY14SJdiFmUXkM3bhUAVm3yp2F9lyN_f326V3NNZ4=")
os.environ.setdefault("HUB_API_KEY", "test-api-key")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.session import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _schema():
    # Tables come straight from the models; migrations are checked in CI with
    # `alembic check`, not by running them here.
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def _clean_tables():
    yield
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, headers={"X-API-Key": get_settings().hub_api_key})


@pytest.fixture
def anonymous_client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def db():
    """Direct database access for asserting on what was actually stored."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def integration(client) -> dict:
    return client.post(
        "/integrations",
        json={
            "name": "Payments API",
            "base_url": "https://payments.example.com",
            "auth_type": "API_KEY",
        },
    ).json()
