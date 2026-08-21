from collections.abc import Callable, Iterable
from itertools import islice
from typing import Any

from fastapi.encoders import jsonable_encoder
from openstack.exceptions import SDKException

from app.models import Category, Resource


def resource_row(resource: Any, kind: str) -> Resource:
    raw_data = resource.to_dict() if hasattr(resource, "to_dict") else dict(resource)
    data = jsonable_encoder(raw_data)
    identifier = str(data.get("id", data.get("name", "unknown")))
    name = str(data.get("name", identifier))
    return {"id": identifier, "name": name, "type": kind, "details": data}


def collect_group(category: Category, kind: str, items: Iterable[Any]) -> None:
    category.resources.extend(resource_row(item, kind) for item in items)


def service_category(
    connection: Any,
    key: str,
    title: str,
    service: str,
    groups: list[tuple[str, Callable[[], Iterable[Any]]]],
) -> Category:
    category = Category(key, title)
    try:
        if not connection.has_service(service):
            category.status = "unavailable"
            category.message = f"{title} is not present in the Keystone catalog."
            category.error_code = "service_missing"
            return category
    except (OSError, RuntimeError, SDKException):
        category.status = "unavailable"
        category.message = f"{title} availability could not be checked."
        category.error_code = "service_check_failed"
        return category
    failed = 0
    for kind, loader in groups:
        try:
            collect_group(category, kind, loader())
        except (OSError, RuntimeError, SDKException, ValueError):
            failed += 1
    category.status = "partial" if failed and category.resources else "unavailable" if failed else "ok"
    category.message = "Some resource types could not be listed." if failed else ""
    category.error_code = "resource_query_failed" if failed else None
    return category


def collect_inventory(connection: Any, object_limit: int) -> list[Category]:
    categories = [
        service_category(connection, "compute", "Compute", "compute", [
            ("server", lambda: connection.compute.servers(details=True, all_projects=True)),
            ("flavor", connection.compute.flavors),
            ("image", connection.compute.images),
            ("keypair", connection.compute.keypairs),
            ("availability_zone", connection.compute.availability_zones),
            ("hypervisor", connection.compute.hypervisors),
            ("server_group", connection.compute.server_groups),
        ]),
        service_category(connection, "network", "Network", "network", [
            ("network", connection.network.networks),
            ("subnet", connection.network.subnets),
            ("port", connection.network.ports),
            ("router", connection.network.routers),
            ("security_group", connection.network.security_groups),
            ("floating_ip", connection.network.ips),
            ("trunk", connection.network.trunks),
            ("agent", connection.network.agents),
        ]),
        service_category(connection, "block_storage", "Block Storage", "block-storage", [
            ("volume", lambda: connection.block_storage.volumes(details=True, all_projects=True)),
            ("snapshot", lambda: connection.block_storage.snapshots(details=True, all_projects=True)),
            ("backup", connection.block_storage.backups),
            ("volume_type", connection.block_storage.volume_types),
            ("availability_zone", connection.block_storage.availability_zones),
        ]),
    ]
    categories.append(collect_object_storage(connection, object_limit))
    return categories


def collect_object_storage(connection: Any, object_limit: int) -> Category:
    category = service_category(
        connection,
        "object_storage",
        "Object Storage",
        "object-store",
        [("container", lambda: connection.object_store.containers(limit=object_limit))],
    )
    if category.status == "unavailable":
        return category
    containers = [item for item in category.resources if item["type"] == "container"]
    failed = False
    for container in containers:
        try:
            objects = islice(connection.object_store.objects(container["name"]), object_limit)
            collect_group(category, "object", objects)
        except (OSError, RuntimeError, SDKException, ValueError):
            failed = True
    if failed:
        category.status = "partial"
        category.message = "Some object listings could not be read."
        category.error_code = "object_query_failed"
    return category
