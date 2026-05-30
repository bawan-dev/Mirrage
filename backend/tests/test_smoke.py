"""Backend smoke tests: the service starts and the basic routes respond."""

from fastapi.testclient import TestClient


def test_root_is_online(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"service": "mirrage-api", "status": "online"}


def test_health_is_online(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"service": "mirrage-api", "status": "online"}
