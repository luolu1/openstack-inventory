from pathlib import Path
from typing import Any

import openstack
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from keystoneauth1.exceptions import AuthorizationFailure, EndpointNotFound, MissingRequiredOptions

from app.auth import load_openrc
from app.config import Settings, load_settings
from app.inventory import collect_inventory
from app.labels import local_time, resource_label, status_label
from app.models import Category, Inventory

BASE_DIR = Path(__file__).parent
settings: Settings = load_settings()
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.filters["status_label"] = status_label
templates.env.filters["resource_label"] = resource_label
templates.env.filters["local_time"] = local_time
app = FastAPI(title="OpenStack Inventory", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
_cached: tuple[float, Inventory] | None = None


def snapshot() -> Inventory:
    global _cached
    import time

    now = time.monotonic()
    if _cached and now - _cached[0] < settings.cache_seconds:
        return _cached[1]
    auth = load_openrc(settings.openrc_path)
    if auth.environment is None:
        inventory = Inventory(auth.status, auth.message, not_configured_categories())
    else:
        try:
            connection = openstack.connect(
                auth=auth_options(auth.environment),
                interface=auth.environment.get("OS_INTERFACE", "public"),
                region_name=settings.region_name or auth.environment.get("OS_REGION_NAME"),
                cacert=auth.environment.get("OS_CACERT"),
                load_yaml_config=False,
                load_envvars=False,
            )
            inventory = Inventory("ok", auth.message, collect_inventory(connection, settings.object_limit))
        except (AuthorizationFailure, EndpointNotFound, MissingRequiredOptions, OSError, RuntimeError, ValueError):
            inventory = Inventory("unavailable", "OpenStack 认证或服务发现失败，已安全降级。", unavailable_categories())
    _cached = (now, inventory)
    return inventory


def not_configured_categories() -> list[Category]:
    return [Category(key, title, "not_configured", "需要配置 OpenStack 凭据后才能读取该服务。", "auth_missing") for key, title in category_names()]


def unavailable_categories() -> list[Category]:
    return [Category(key, title, "unavailable", "该服务当前无法查询。", "connection_failed") for key, title in category_names()]


def category_names() -> list[tuple[str, str]]:
    return [("compute", "计算"), ("network", "网络"), ("block_storage", "块存储"), ("object_storage", "对象存储")]


def auth_options(environment: dict[str, str]) -> dict[str, str]:
    mapping = {
        "OS_AUTH_URL": "auth_url",
        "OS_USERNAME": "username",
        "OS_PASSWORD": "password",
        "OS_PROJECT_NAME": "project_name",
        "OS_USER_DOMAIN_NAME": "user_domain_name",
        "OS_PROJECT_DOMAIN_NAME": "project_domain_name",
        "OS_USER_DOMAIN_ID": "user_domain_id",
        "OS_PROJECT_DOMAIN_ID": "project_domain_id",
    }
    return {target: environment[source] for source, target in mapping.items() if source in environment}


@app.get("/health")
def health() -> dict[str, str]:
    inventory = snapshot()
    return {"status": "healthy", "inventory": inventory.auth_status, "collected_at": inventory.collected_at}


@app.get("/api/inventory")
def api_inventory() -> dict[str, Any]:
    return snapshot().as_dict()


@app.get("/api/inventory/{category}")
def api_category(category: str) -> dict[str, Any]:
    for item in snapshot().categories:
        if item.key == category:
            return item.as_dict()
    raise HTTPException(status_code=404, detail="资源分类不存在。")


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request) -> HTMLResponse:
    inventory = snapshot()
    return templates.TemplateResponse(request=request, name="index.html", context={"inventory": inventory.as_dict()})


@app.get("/inventory/{category}", response_class=HTMLResponse)
def category_page(request: Request, category: str) -> HTMLResponse:
    inventory = snapshot()
    selected = next((item.as_dict() for item in inventory.categories if item.key == category), None)
    if selected is None:
        selected = {"key": category, "title": "未知分类", "status": "not_found", "message": "资源分类不存在。", "resources": [], "counts": {"resources": 0}}
    return templates.TemplateResponse(request=request, name="category.html", context={"category": selected})
