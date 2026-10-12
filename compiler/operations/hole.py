"""Execute PartDesign Hole operations in FreeCAD."""

from __future__ import annotations

from typing import Any

HOLE_DEPTH_THROUGH_ALL = 1


def execute_hole(operation: dict[str, Any], context: Any) -> Any:
    profile = context.resolve(operation["profile"])
    hole = context.body.newObject("PartDesign::Hole", operation["id"])
    hole.Profile = (profile, [""])
    hole.Diameter = operation["diameter"] * context.unit_scale

    depth = operation["depth"]
    if depth == "through_all":
        hole.DepthType = HOLE_DEPTH_THROUGH_ALL
    else:
        hole.DepthType = 0
        hole.Depth = depth * context.unit_scale

    # Flat-bottom for blind holes (no drill-tip cone).
    if depth != "through_all":
        hole.DrillPoint = "Flat"

    if operation.get("reversed"):
        hole.Reversed = True

    return hole
