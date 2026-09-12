from sqlalchemy.exc import OperationalError

from app.db.session import get_db
from app.main import app


def test_health_ok(anonymous_client):
    response = anonymous_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_reports_unreachable_database_without_leaking_details(anonymous_client, monkeypatch):
    class BrokenSession:
        def execute(self, *args, **kwargs):
            raise OperationalError("SELECT 1", {}, Exception("connection refused to db-host"))

        def close(self):
            pass

    def broken_get_db():
        yield BrokenSession()

    monkeypatch.setitem(app.dependency_overrides, get_db, broken_get_db)

    response = anonymous_client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "unhealthy"}
    assert "db-host" not in response.text
