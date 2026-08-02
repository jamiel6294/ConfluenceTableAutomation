"""Plain data structures shared between the transform layer and the API."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FieldKind(str, Enum):
    """How a column's values should be rendered on the frontend."""

    TEXT = "text"
    STATUS = "status"
    PROGRESS = "progress"
    DATE = "date"
    OWNER = "owner"
    NUMBER = "number"


@dataclass
class Column:
    """Describes one Tabulator column, driven by the source data's fields."""

    field: str
    title: str
    kind: FieldKind = FieldKind.TEXT
    filterable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "title": self.title,
            "kind": self.kind.value,
            "filterable": self.filterable,
        }


@dataclass
class DashboardPayload:
    """The full response body served to the frontend for one refresh cycle."""

    columns: list[Column]
    rows: list[dict[str, Any]]
    status_colors: dict[str, str] = field(default_factory=dict)
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "columns": [c.to_dict() for c in self.columns],
            "rows": self.rows,
            "status_colors": self.status_colors,
            "generated_at": self.generated_at,
        }
