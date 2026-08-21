from fastapi.testclient import TestClient

from app.main import app


def test_health_stays_healthy_without_openstack_credentials() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_inventory_reports_missing_credentials_without_500() -> None:
    client = TestClient(app)
    response = client.get("/api/inventory")
    assert response.status_code == 200
    assert response.json()["auth"]["status"] == "not_configured"


def test_unknown_category_is_not_found() -> None:
    client = TestClient(app)
    response = client.get("/api/inventory/nope")
    assert response.status_code == 404
