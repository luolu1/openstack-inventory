from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.collector import InventoryCollector
from app.config import Settings, load_settings
from app.labels import local_time, resource_label, status_label
from app.platforms import Platform, PlatformCatalog, load_catalog

BASE_DIR = Path(__file__).parent
settings: Settings = load_settings()
collector = InventoryCollector(settings)
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.filters["status_label"] = status_label
templates.env.filters["resource_label"] = resource_label
templates.env.filters["local_time"] = local_time
app = FastAPI(title="OpenStack 资源清单", version="0.2.0")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


def catalog() -> PlatformCatalog:
    if settings.platforms_path is None and settings.legacy_openrc_path is not None:
        platform = Platform(
            id="default",
            name="默认平台",
            openrc_path=settings.legacy_openrc_path,
            region_name=settings.region_name,
            description="来自 OPENSTACK_OPENRC 的单平台配置。",
        )
        return PlatformCatalog((platform,), "ok", "使用单平台环境变量配置。")
    return load_catalog(settings.platforms_path)


def require_platform(platform_id: str) -> Platform:
    platform = catalog().find(platform_id)
    if platform is None:
        raise HTTPException(status_code=404, detail="平台不存在。")
    return platform


def platform_rows(current: PlatformCatalog) -> list[dict[str, str]]:
    return [
        {"id": item.id, "name": item.name, "description": item.description}
        for item in current.platforms
    ]


@app.get("/health")
def health() -> dict[str, str | int]:
    current = catalog()
    return {
        "status": "healthy",
        "platforms": len(current.platforms),
        "catalog": current.status,
        "message": current.message,
    }


@app.get("/api/platforms")
def api_platforms() -> dict[str, Any]:
    current = catalog()
    return {
        "status": current.status,
        "message": current.message,
        "platforms": platform_rows(current),
    }


@app.get("/api/platforms/{platform_id}/inventory")
def api_inventory(platform_id: str) -> dict[str, Any]:
    return collector.snapshot(require_platform(platform_id)).as_dict()


@app.get("/api/platforms/{platform_id}/inventory/{category}")
def api_category(platform_id: str, category: str) -> dict[str, Any]:
    inventory = collector.snapshot(require_platform(platform_id))
    for item in inventory.categories:
        if item.key == category:
            return {"platform": {"id": inventory.platform_id, "name": inventory.platform_name}} | item.as_dict()
    raise HTTPException(status_code=404, detail="资源分类不存在。")


@app.get("/", response_class=HTMLResponse)
def platform_index(request: Request) -> HTMLResponse:
    current = catalog()
    context = {
        "catalog_status": current.status,
        "catalog_message": current.message,
        "platforms": platform_rows(current),
    }
    return templates.TemplateResponse(request=request, name="platforms.html", context=context)


@app.get("/platforms/{platform_id}", response_class=HTMLResponse)
def platform_page(request: Request, platform_id: str) -> HTMLResponse:
    inventory = collector.snapshot(require_platform(platform_id)).as_dict()
    return templates.TemplateResponse(request=request, name="platform.html", context={"inventory": inventory})


@app.get("/platforms/{platform_id}/{category}", response_class=HTMLResponse)
def category_page(request: Request, platform_id: str, category: str) -> HTMLResponse:
    inventory = collector.snapshot(require_platform(platform_id))
    selected = next((item.as_dict() for item in inventory.categories if item.key == category), None)
    if selected is None:
        raise HTTPException(status_code=404, detail="资源分类不存在。")
    context = {
        "category": selected,
        "platform": {"id": inventory.platform_id, "name": inventory.platform_name},
    }
    return templates.TemplateResponse(request=request, name="category.html", context=context)
