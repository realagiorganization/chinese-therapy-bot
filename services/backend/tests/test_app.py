from fastapi.testclient import TestClient

from app.core.app import create_app


def test_healthcheck_returns_ok() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/api/healthz")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
