"""Compilation context tracking FreeCAD objects by operation id."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CompileContext:
    """Holds the FreeCAD document and operation object registry."""

    doc: Any
    body: Any
    unit_scale: float = 1.0
    objects: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def register(self, op_id: str, obj: Any) -> None:
        self.objects[op_id] = obj

    def resolve(self, op_id: str) -> Any:
        if op_id not in self.objects:
            raise KeyError(f"Unknown operation reference: {op_id}")
        return self.objects[op_id]


def unit_scale_factor(unit: str) -> float:
    """Return multiplier to convert JSON units into FreeCAD millimeters."""
    return {
        "mm": 1.0,
        "cm": 10.0,
        "m": 1000.0,
        "inch": 25.4,
    }[unit]
