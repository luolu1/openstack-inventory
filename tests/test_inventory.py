from app.inventory import collect_inventory


class Resource:
    def __init__(self, identifier: str, name: str) -> None:
        self.identifier = identifier
        self.name = name

    def to_dict(self) -> dict[str, str]:
        return {"id": self.identifier, "name": self.name}


class Proxy:
    def __getattr__(self, name: str):
        if name == "objects":
            return lambda container: [Resource(f"object-{container}", "object")]
        return lambda **kwargs: [Resource(name, name)]


class Connection:
    compute = Proxy()
    network = Proxy()
    block_storage = Proxy()
    object_store = Proxy()

    def has_service(self, service: str) -> bool:
        return service in {"compute", "network", "block-storage", "object-store"}


def test_collect_inventory_covers_all_service_domains() -> None:
    categories = collect_inventory(Connection(), 20)
    assert [category.key for category in categories] == [
        "compute",
        "network",
        "block_storage",
        "object_storage",
    ]
    assert all(category.status == "ok" for category in categories)


def test_object_storage_includes_objects() -> None:
    categories = collect_inventory(Connection(), 20)
    object_storage = categories[-1]
    assert {resource["type"] for resource in object_storage.resources} == {"container", "object"}
