import json
from pathlib import Path

from app.platforms import load_catalog


def write_catalog(tmp_path: Path, payload: object) -> Path:
    path = tmp_path / "platforms.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_catalog_loads_multiple_platforms(tmp_path: Path) -> None:
    path = write_catalog(
        tmp_path,
        {
            "platforms": [
                {"id": "prod", "name": "生产集群", "openrc": "/etc/kolla/prod-openrc.sh"},
                {"id": "test", "name": "测试集群", "openrc": "/etc/kolla/test-openrc.sh"},
            ]
        },
    )
    catalog = load_catalog(path)
    assert catalog.status == "ok"
    assert [item.id for item in catalog.platforms] == ["prod", "test"]
    assert catalog.find("test") is not None
    assert catalog.find("missing") is None


def test_relative_openrc_resolves_against_catalog(tmp_path: Path) -> None:
    path = write_catalog(tmp_path, [{"id": "lab", "openrc": "creds/lab-openrc.sh"}])
    platform = load_catalog(path).platforms[0]
    assert platform.openrc_path == (tmp_path / "creds/lab-openrc.sh").resolve()
    assert platform.name == "lab"


def test_missing_catalog_file_is_not_configured(tmp_path: Path) -> None:
    catalog = load_catalog(tmp_path / "absent.json")
    assert catalog.status == "not_configured"
    assert catalog.platforms == ()


def test_invalid_json_is_not_configured(tmp_path: Path) -> None:
    path = tmp_path / "platforms.json"
    path.write_text("{not json", encoding="utf-8")
    catalog = load_catalog(path)
    assert catalog.status == "not_configured"


def test_duplicate_platform_id_is_rejected(tmp_path: Path) -> None:
    path = write_catalog(
        tmp_path,
        [{"id": "same", "openrc": "/a.sh"}, {"id": "same", "openrc": "/b.sh"}],
    )
    catalog = load_catalog(path)
    assert catalog.status == "not_configured"
    assert "same" in catalog.message


def test_entry_without_openrc_is_rejected(tmp_path: Path) -> None:
    path = write_catalog(tmp_path, [{"id": "broken"}])
    assert load_catalog(path).status == "not_configured"


def test_empty_platform_list_is_empty_status(tmp_path: Path) -> None:
    path = write_catalog(tmp_path, {"platforms": []})
    assert load_catalog(path).status == "empty"
