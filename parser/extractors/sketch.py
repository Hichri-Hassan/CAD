"""Extract sketch geometry and constraints from FreeCAD XML."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from parser.utils.xml_helpers import (
    get_property,
    get_placement,
    is_identity_placement,
    round_point,
    round_value,
)

# FreeCAD Sketcher constraint type enumeration (subset used in V0).
CONSTRAINT_TYPE_NAMES = {
    1: "Coincident",
    2: "Horizontal",
    3: "Vertical",
    4: "Parallel",
    5: "Perpendicular",
    6: "Tangent",
    7: "Equal",
    8: "Symmetric",
    9: "Block",
    10: "Distance",
    11: "DistanceX",
    12: "DistanceY",
    13: "Radius",
    14: "Diameter",
}

ORIGIN_PLANE_MAP = {
    "XY_Plane": "XY",
    "XZ_Plane": "XZ",
    "YZ_Plane": "YZ",
}


def extract_sketch(
    obj: ET.Element,
    op_id: str,
    id_map: dict[str, str],
) -> dict[str, Any]:
    """Convert a Sketcher::SketchObject to CAD JSON Sketch operation.

    Sketch geometry is exported exactly as stored in FreeCAD. The parser never
    rewrites entities (e.g. it will not replace a Point with a Circle derived
    from a Hole diameter parameter).
    """
    attachment = get_property(obj, "AttachmentSupport")
    plane, support = _extract_plane_or_support(attachment, id_map)

    attachment_offset = get_placement(get_property(obj, "AttachmentOffset"))
    if attachment_offset and not is_identity_placement(attachment_offset):
        operation_attachment_offset = attachment_offset
    else:
        operation_attachment_offset = None

    geometry_prop = get_property(obj, "Geometry")
    entities = _extract_entities(geometry_prop)

    constraints_prop = get_property(obj, "Constraints")
    constraints = _extract_constraints(constraints_prop)

    operation: dict[str, Any] = {
        "id": op_id,
        "type": "Sketch",
        "entities": entities,
    }
    if constraints:
        operation["constraints"] = constraints
    else:
        operation["constraints"] = []

    if support is not None:
        operation["support"] = support
    elif plane is not None:
        operation["plane"] = plane
    else:
        # Spec requires plane; fall back when attachment cannot be resolved.
        operation["plane"] = "XY"

    if operation_attachment_offset is not None:
        operation["attachment_offset"] = operation_attachment_offset

    return operation


def _extract_plane_or_support(
    attachment_prop: ET.Element | None,
    id_map: dict[str, str],
) -> tuple[str | None, dict[str, Any] | None]:
    if attachment_prop is None:
        return None, None

    link_sub_list = attachment_prop.find("LinkSubList")
    if link_sub_list is None:
        return None, None

    links = link_sub_list.findall("Link")
    if not links:
        return None, None

    link = links[0]
    obj_name = link.get("obj", "")
    sub_name = link.get("sub", "")

    if obj_name == "Origin" and sub_name in ORIGIN_PLANE_MAP:
        return ORIGIN_PLANE_MAP[sub_name], None

    if sub_name.startswith("Face") and obj_name in id_map:
        return None, {
            "type": "face",
            "reference": id_map[obj_name],
            "selector": sub_name,
        }

    return None, None


def _extract_entities(geometry_prop: ET.Element | None) -> list[dict[str, Any]]:
    """Extract sketch entities in FreeCAD GeometryList order.

    Entities are never reordered or collapsed (e.g. four lines are not merged
    into a Rectangle) so that downstream Pad face topology matches the source
    model during round-trip compilation.
    """
    if geometry_prop is None:
        return []

    entities: list[dict[str, Any]] = []
    geometry_list = geometry_prop.find("GeometryList")
    if geometry_list is None:
        return []

    for idx, geom in enumerate(geometry_list.findall("Geometry"), start=1):
        geom_type = geom.get("type", "")
        entity_id = f"e_{idx:03d}"

        if geom_type == "Part::GeomLineSegment":
            segment = geom.find("LineSegment")
            if segment is None:
                continue
            start = round_point([
                float(segment.get("StartX", 0)),
                float(segment.get("StartY", 0)),
            ])
            end = round_point([
                float(segment.get("EndX", 0)),
                float(segment.get("EndY", 0)),
            ])
            entities.append({
                "id": entity_id,
                "type": "Line",
                "start": start,
                "end": end,
            })

        elif geom_type == "Part::GeomCircle":
            circle = geom.find("Circle")
            if circle is None:
                continue
            entities.append({
                "id": entity_id,
                "type": "Circle",
                "center": round_point([
                    float(circle.get("CenterX", 0)),
                    float(circle.get("CenterY", 0)),
                ]),
                "radius": round_value(float(circle.get("Radius", 0))),
            })

        elif geom_type == "Part::GeomArcOfCircle":
            arc = geom.find("ArcOfCircle")
            if arc is None:
                continue
            entities.append({
                "id": entity_id,
                "type": "Arc",
                "center": round_point([
                    float(arc.get("CenterX", 0)),
                    float(arc.get("CenterY", 0)),
                ]),
                "radius": round_value(float(arc.get("Radius", 0))),
                "start_angle": round_value(float(arc.get("StartAngle", 0)), 3),
                "end_angle": round_value(float(arc.get("EndAngle", 0)), 3),
            })

        elif geom_type == "Part::GeomPoint":
            point = geom.find("GeomPoint")
            if point is None:
                continue
            entities.append({
                "id": entity_id,
                "type": "Point",
                "position": round_point([
                    float(point.get("X", 0)),
                    float(point.get("Y", 0)),
                ]),
            })

    return entities


def _extract_constraints(constraints_prop: ET.Element | None) -> list[dict[str, Any]]:
    if constraints_prop is None:
        return []

    constraint_list = constraints_prop.find("ConstraintList")
    if constraint_list is None:
        return []

    results: list[dict[str, Any]] = []
    for constrain in constraint_list.findall("Constrain"):
        type_code = int(constrain.get("Type", "-1"))
        type_name = CONSTRAINT_TYPE_NAMES.get(type_code)
        if type_name is None:
            continue

        element_ids = [
            int(x)
            for x in constrain.get("ElementIds", "").split()
            if x.lstrip("-").isdigit() and int(x) >= 0
        ]
        entity_ids = [f"e_{eid + 1:03d}" for eid in element_ids]

        entry: dict[str, Any] = {"type": type_name}
        value = float(constrain.get("Value", "0"))
        if type_name in {"Distance", "DistanceX", "DistanceY", "Radius", "Diameter"} and value > 0:
            entry["value"] = round_value(value)

        if len(entity_ids) == 1:
            entry["entity"] = entity_ids[0]
        elif len(entity_ids) >= 2:
            entry["entity_1"] = entity_ids[0]
            entry["entity_2"] = entity_ids[1]
        else:
            continue

        results.append(entry)

    return results
