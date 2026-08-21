from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, TypedDict


class Resource(TypedDict):
    id: str
    name: str
    type: str
    details: dict[str, Any]


@dataclass(slots=True)
class Category:
    key: str
    title: str
    status: str = "empty"
    message: str = ""
    error_code: str | None = None
    resources: list[Resource] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "title": self.title,
            "status": self.status,
            "message": self.message,
            "error_code": self.error_code,
            "counts": {"resources": len(self.resources)},
            "resources": self.resources,
        }


@dataclass(slots=True)
class Inventory:
    platform_id: str
    platform_name: str
    auth_status: str
    auth_message: str
    categories: list[Category]
    collected_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def as_dict(self) -> dict[str, Any]:
        category_data = [category.as_dict() for category in self.categories]
        return {
            "status": "ok" if self.auth_status == "ok" else "partial",
            "platform": {"id": self.platform_id, "name": self.platform_name},
            "collected_at": self.collected_at,
            "auth": {"status": self.auth_status, "message": self.auth_message},
            "categories": category_data,
            "summary": {
                "categories": len(category_data),
                "resources": sum(item["counts"]["resources"] for item in category_data),
            },
        }
