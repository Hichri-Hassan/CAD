"""Execute Pad and Pocket operations in FreeCAD."""

from __future__ import annotations

from typing import Any


def execute_pad(operation: dict[str, Any], context: Any) -> Any:
    profile = context.resolve(operation["profile"])
    pad = context.body.newObject("PartDesign::Pad", operation["id"])
    pad.Profile = (profile, [""])
    pad.Length = operation["length"] * context.unit_scale

    if operation.get("reversed"):
        pad.Reversed = True
    if operation.get("symmetric"):
        pad.Midplane = True

    return pad


def execute_pocket(operation: dict[str, Any], context: Any) -> Any:
    profile = context.resolve(operation["profile"])
    _validate_pocket_profile(profile, operation["id"], context)

    pocket = context.body.newObject("PartDesign::Pocket", operation["id"])
    pocket.Profile = (profile, [""])

    depth = operation["depth"]
    if depth == "through_all":
        pocket.Type = 1
    else:
        pocket.Type = 0
        pocket.Length = depth * context.unit_scale

    if operation.get("reversed"):
        pocket.Reversed = True

    return pocket


def _validate_pocket_profile(profile: Any, pocket_id: str, context: Any) -> None:
    """Ensure the pocket profile sketch contains geometry that can form a cut."""
    geometry_count = len(profile.Geometry)
    if geometry_count == 0:
        raise ValueError(f"Pocket {pocket_id}: profile sketch has no geometry.")

    if geometry_count == 1:
        geometry = profile.Geometry[0]
        if geometry.TypeId == "Part::GeomPoint":
            raise ValueError(
                f"Pocket {pocket_id}: profile sketch contains only a Point entity. "
                "A Pocket requires a closed profile (Circle, Rectangle, etc.). "
                "Point-based holes cannot be compiled without additional specification."
            )
