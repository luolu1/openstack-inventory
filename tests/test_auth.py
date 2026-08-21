from pathlib import Path

from app.auth import load_openrc


def test_missing_openrc_is_not_configured() -> None:
    result = load_openrc(Path("/does/not/exist"))
    assert result.status == "not_configured"
    assert result.environment is None


def test_unset_openrc_is_not_configured() -> None:
    result = load_openrc(None)
    assert result.status == "not_configured"
