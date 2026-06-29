"""Execute Sketch operations in FreeCAD."""

from __future__ import annotations

from typing import Any

import Part


PLANE_NAMES = {
    "XY": "XY_Plane",
    "XZ": "XZ_Plane",
    "YZ": "YZ_Plane",
}


def execute_sketch(operation: dict[str, Any], context: Any) -> Any:
    """Create a sketch and add all entities from the JSON operation."""
    sketch = context.body.newObject("Sketcher::SketchObject", operation["id"])
    _attach_sketch(sketch, operation, context)
    _apply_attachment_offset(sketch, operation, context.unit_scale)
    context.doc.recompute()

    for entity in operation.get("entities", []):
        _add_entity(sketch, entity, context.unit_scale)

    return sketch


def _apply_attachment_offset(sketch: Any, operation: dict[str, Any], scale: float) -> None:
    offset = operation.get("attachment_offset")
    if not offset:
        return

    import FreeCAD as App

    position = offset["position"]
    rotation = offset["rotation"]
    sketch.AttachmentOffset = App.Placement(
        App.Vector(position[0] * scale, position[1] * scale, position[2] * scale),
        App.Rotation(rotation[0], rotation[1], rotation[2], rotation[3]),
    )


def _attach_sketch(sketch: Any, operation: dict[str, Any], context: Any) -> None:
    if "plane" in operation:
        plane_name = PLANE_NAMES[operation["plane"]]
        sketch.MapMode = "FlatFace"
        sketch.AttachmentSupport = [(context.body.Origin, plane_name)]
        return

    support = operation["support"]
    if support.get("type") != "face":
        raise ValueError(f"Unsupported sketch support type: {support.get('type')}")

    reference = context.resolve(support["reference"])
    selector = support["selector"]
    sketch.MapMode = "FlatFace"
    sketch.AttachmentSupport = [(reference, selector)]


def _add_entity(sketch: Any, entity: dict[str, Any], scale: float) -> None:
    entity_type = entity["type"]

    if entity_type == "Line":
        start = entity["start"]
        end = entity["end"]
        segment = Part.LineSegment(
            _vec2(start, scale),
            _vec2(end, scale),
        )
        sketch.addGeometry(segment, False)

    elif entity_type == "Circle":
        center = entity["center"]
        radius = entity["radius"] * scale
        circle = Part.Circle(_vec2(center, scale), _normal(), radius)
        sketch.addGeometry(circle, False)

    elif entity_type == "Arc":
        center = entity["center"]
        radius = entity["radius"] * scale
        start_angle = entity["start_angle"]
        end_angle = entity["end_angle"]
        circle = Part.Circle(_vec2(center, scale), _normal(), radius)
        arc = Part.ArcOfCircle(circle, _deg(start_angle), _deg(end_angle))
        sketch.addGeometry(arc, False)

    elif entity_type == "Rectangle":
        # Supported for manually authored JSON. Uses left-edge-first winding
        # consistent with FreeCAD sketch construction order.
        origin = entity["origin"]
        width = entity["width"] * scale
        height = entity["height"] * scale
        x0 = origin[0] * scale
        y0 = origin[1] * scale
        segments = [
            (_vec2([x0, y0 + height], 1.0), _vec2([x0, y0], 1.0)),
            (_vec2([x0, y0], 1.0), _vec2([x0 + width, y0], 1.0)),
            (_vec2([x0 + width, y0], 1.0), _vec2([x0 + width, y0 + height], 1.0)),
            (_vec2([x0 + width, y0 + height], 1.0), _vec2([x0, y0 + height], 1.0)),
        ]
        for start, end in segments:
            sketch.addGeometry(Part.LineSegment(start, end), False)

    elif entity_type == "Point":
        position = entity["position"]
        point = Part.Point(_vec2(position, scale))
        sketch.addGeometry(point, False)

    else:
        raise ValueError(f"Unsupported sketch entity type: {entity_type}")


def _vec2(point: list[float], scale: float) -> Any:
    import FreeCAD as App

    return App.Vector(point[0] * scale, point[1] * scale, 0)


def _normal() -> Any:
    import FreeCAD as App

    return App.Vector(0, 0, 1)


def _deg(value: float) -> float:
    import math

    return math.radians(value)
