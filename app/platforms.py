import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Platform:
    id: str
    name: str
    openrc_path: Path
    region_name: str | None = None
    description: str = ""


@dataclass(frozen=True, slots=True)
class PlatformCatalog:
    platforms: tuple[Platform, ...]
    status: str
    message: str

    def find(self, platform_id: str) -> Platform | None:
        return next((item for item in self.platforms if item.id == platform_id), None)


def empty_catalog(status: str, message: str) -> PlatformCatalog:
    return PlatformCatalog((), status, message)


def load_catalog(path: Path | None) -> PlatformCatalog:
    if path is None:
        return empty_catalog("not_configured", "未设置 OPENSTACK_PLATFORMS_FILE，请指向平台清单 JSON 文件。")
    if not path.is_file():
        return empty_catalog("not_configured", f"平台清单文件不存在：{path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return empty_catalog("not_configured", "平台清单文件无法读取，请检查权限与编码。")
    except json.JSONDecodeError as error:
        return empty_catalog("not_configured", f"平台清单不是合法 JSON：第 {error.lineno} 行。")
    return parse_catalog(raw, path)


def parse_catalog(raw: object, path: Path) -> PlatformCatalog:
    entries = raw.get("platforms") if isinstance(raw, dict) else raw
    if not isinstance(entries, list):
        return empty_catalog("not_configured", "平台清单格式错误：应为数组，或包含 platforms 数组的对象。")
    platforms: list[Platform] = []
    seen: set[str] = set()
    for index, entry in enumerate(entries, start=1):
        platform = parse_entry(entry, index, path)
        if platform is None:
            return empty_catalog("not_configured", f"平台清单第 {index} 项缺少 id 或 openrc 字段。")
        if platform.id in seen:
            return empty_catalog("not_configured", f"平台清单存在重复的 id：{platform.id}")
        seen.add(platform.id)
        platforms.append(platform)
    if not platforms:
        return empty_catalog("empty", "平台清单为空，请至少配置一个平台。")
    return PlatformCatalog(tuple(platforms), "ok", f"已加载 {len(platforms)} 个平台。")


def parse_entry(entry: object, index: int, path: Path) -> Platform | None:
    if not isinstance(entry, dict):
        return None
    platform_id = str(entry.get("id") or "").strip()
    openrc = str(entry.get("openrc") or entry.get("openrc_path") or "").strip()
    if not platform_id or not openrc:
        return None
    region = entry.get("region_name") or entry.get("region")
    return Platform(
        id=platform_id,
        name=str(entry.get("name") or platform_id),
        openrc_path=resolve_openrc(openrc, path),
        region_name=str(region) if region else None,
        description=str(entry.get("description") or ""),
    )


def resolve_openrc(openrc: str, catalog_path: Path) -> Path:
    candidate = Path(openrc).expanduser()
    return candidate if candidate.is_absolute() else (catalog_path.parent / candidate).resolve()
