import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    platforms_path: Path | None
    legacy_openrc_path: Path | None
    region_name: str | None
    host: str
    port: int
    cache_seconds: int
    object_limit: int


def load_settings() -> Settings:
    platforms = os.environ.get("OPENSTACK_PLATFORMS_FILE", "").strip()
    legacy = os.environ.get("OPENSTACK_OPENRC", "").strip()
    return Settings(
        platforms_path=Path(platforms) if platforms else None,
        legacy_openrc_path=Path(legacy) if legacy else None,
        region_name=os.environ.get("OPENSTACK_REGION_NAME") or None,
        host=os.environ.get("APP_HOST", "127.0.0.1"),
        port=int(os.environ.get("APP_PORT", "8000")),
        cache_seconds=max(0, int(os.environ.get("INVENTORY_CACHE_SECONDS", "30"))),
        object_limit=max(1, int(os.environ.get("OBJECT_LIST_LIMIT", "500"))),
    )
