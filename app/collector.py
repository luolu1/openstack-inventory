import time

import openstack
from keystoneauth1.exceptions import (
    AuthorizationFailure,
    EndpointNotFound,
    MissingRequiredOptions,
)

from app.auth import load_openrc
from app.config import Settings
from app.inventory import collect_inventory
from app.models import Category, Inventory
from app.platforms import Platform

CATEGORY_NAMES = (
    ("compute", "计算"),
    ("network", "网络"),
    ("block_storage", "块存储"),
    ("object_storage", "对象存储"),
)

AUTH_ERRORS = (
    AuthorizationFailure,
    EndpointNotFound,
    MissingRequiredOptions,
    OSError,
    RuntimeError,
    ValueError,
)

AUTH_OPTION_NAMES = {
    "OS_AUTH_URL": "auth_url",
    "OS_USERNAME": "username",
    "OS_PASSWORD": "password",
    "OS_PROJECT_NAME": "project_name",
    "OS_USER_DOMAIN_NAME": "user_domain_name",
    "OS_PROJECT_DOMAIN_NAME": "project_domain_name",
    "OS_USER_DOMAIN_ID": "user_domain_id",
    "OS_PROJECT_DOMAIN_ID": "project_domain_id",
}


def placeholder_categories(status: str, message: str, error_code: str) -> list[Category]:
    return [Category(key, title, status, message, error_code) for key, title in CATEGORY_NAMES]


def auth_options(environment: dict[str, str]) -> dict[str, str]:
    return {
        target: environment[source]
        for source, target in AUTH_OPTION_NAMES.items()
        if source in environment
    }


class InventoryCollector:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._cache: dict[str, tuple[float, Inventory]] = {}

    def snapshot(self, platform: Platform) -> Inventory:
        cached = self._cache.get(platform.id)
        now = time.monotonic()
        if cached and now - cached[0] < self._settings.cache_seconds:
            return cached[1]
        inventory = self._collect(platform)
        self._cache[platform.id] = (now, inventory)
        return inventory

    def _collect(self, platform: Platform) -> Inventory:
        auth = load_openrc(platform.openrc_path)
        if auth.environment is None:
            return Inventory(
                platform.id,
                platform.name,
                auth.status,
                auth.message,
                placeholder_categories("not_configured", auth.message, "auth_missing"),
            )
        try:
            connection = openstack.connect(
                auth=auth_options(auth.environment),
                interface=auth.environment.get("OS_INTERFACE", "public"),
                region_name=platform.region_name
                or self._settings.region_name
                or auth.environment.get("OS_REGION_NAME"),
                cacert=auth.environment.get("OS_CACERT"),
                load_yaml_config=False,
                load_envvars=False,
            )
            categories = collect_inventory(connection, self._settings.object_limit)
        except AUTH_ERRORS:
            message = "OpenStack 认证或服务发现失败，已安全降级。"
            return Inventory(
                platform.id,
                platform.name,
                "unavailable",
                message,
                placeholder_categories("unavailable", message, "connection_failed"),
            )
        return Inventory(platform.id, platform.name, "ok", auth.message, categories)
