import importlib
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.main


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    catalog = tmp_path / "platforms.json"
    catalog.write_text(
        json.dumps(
            [
                {"id": "prod", "name": "生产集群", "openrc": str(tmp_path / "prod-openrc.sh")},
                {"id": "lab", "name": "实验集群", "openrc": str(tmp_path / "lab-openrc.sh")},
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENSTACK_PLATFORMS_FILE", str(catalog))
    monkeypatch.delenv("OPENSTACK_OPENRC", raising=False)
    module = importlib.reload(app.main)
    with TestClient(module.app) as test_client:
        yield test_client
    importlib.reload(app.main)


def test_health_reports_platform_count(client: TestClient) -> None:
    payload = client.get("/health").json()
    assert payload["status"] == "healthy"
    assert payload["platforms"] == 2


def test_platform_list_returns_configured_platforms(client: TestClient) -> None:
    payload = client.get("/api/platforms").json()
    assert [item["id"] for item in payload["platforms"]] == ["prod", "lab"]
    assert payload["status"] == "ok"


def test_platform_index_page_lists_platforms(client: TestClient) -> None:
    body = client.get("/").text
    assert "生产集群" in body
    assert "实验集群" in body


def test_missing_credentials_return_not_configured(client: TestClient) -> None:
    payload = client.get("/api/platforms/prod/inventory").json()
    assert payload["platform"]["id"] == "prod"
    assert payload["auth"]["status"] == "not_configured"
    assert [item["key"] for item in payload["categories"]] == [
        "compute",
        "network",
        "block_storage",
        "object_storage",
    ]


def test_platform_page_renders_for_known_platform(client: TestClient) -> None:
    response = client.get("/platforms/lab")
    assert response.status_code == 200
    assert "实验集群" in response.text


def test_unknown_platform_is_not_found(client: TestClient) -> None:
    assert client.get("/api/platforms/nope/inventory").status_code == 404
    assert client.get("/platforms/nope").status_code == 404


def test_unknown_category_is_not_found(client: TestClient) -> None:
    assert client.get("/api/platforms/prod/inventory/nope").status_code == 404
    assert client.get("/platforms/prod/nope").status_code == 404


def test_category_page_renders_empty_state(client: TestClient) -> None:
    response = client.get("/platforms/prod/compute")
    assert response.status_code == 200
    assert "暂无可显示资源" in response.text
