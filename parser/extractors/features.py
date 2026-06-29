"""Extract Pad, Pocket, Fillet, and Chamfer operations."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from parser.utils.xml_helpers import (
    get_bool,
    get_float,
    get_int,
    get_link,
    get_link_sub_parts,
    get_property,
    round_value,
)

# FreeCAD PartDesign Hole DepthType enumeration (mirrors Pocket Type values).
HOLE_DEPTH_THROUGH_ALL = 1


def extract_pad(obj: ET.Element, op_id: str, id_map: dict[str, str]) -> dict[str, Any]:
    profile_name = get_link(get_property(obj, "Profile"))
    length = get_float(get_property(obj, "Length"))
    reversed_dir = get_bool(get_property(obj, "Reversed"), False)
    symmetric = get_bool(get_property(obj, "Midplane"), False)

    operation: dict[str, Any] = {
        "id": op_id,
        "type": "Pad",
        "profile": id_map.get(profile_name or "", profile_name or ""),
        "length": round_value(length) if length is not None else 0.0,
    }
    if reversed_dir:
        operation["reversed"] = True
    if symmetric:
        operation["symmetric"] = True
    return operation


def extract_pocket(obj: ET.Element, op_id: str, id_map: dict[str, str]) -> dict[str, Any]:
    profile_name = get_link(get_property(obj, "Profile"))
    depth_type = get_int(get_property(obj, "Type"))
    depth = get_float(get_property(obj, "Length"))
    reversed_dir = get_bool(get_property(obj, "Reversed"), False)

    operation: dict[str, Any] = {
        "id": op_id,
        "type": "Pocket",
        "profile": id_map.get(profile_name or "", profile_name or ""),
    }

    # FreeCAD Pocket Type: 0=Dimension, 1=ThroughAll, 2=UpToFirst, 3=UpToLast
    if depth_type == 1:
        operation["depth"] = "through_all"
    elif depth is not None:
        operation["depth"] = round_value(depth)

    if reversed_dir:
        operation["reversed"] = True
    return operation


def extract_hole(obj: ET.Element, op_id: str, id_map: dict[str, str]) -> dict[str, Any]:
    """Extract a PartDesign::Hole feature as a native Hole operation."""
    profile_name = get_link(get_property(obj, "Profile"))
    diameter = get_float(get_property(obj, "Diameter"))
    depth_type = get_int(get_property(obj, "DepthType"))
    depth = get_float(get_property(obj, "Depth"))
    reversed_dir = get_bool(get_property(obj, "Reversed"), False)

    operation: dict[str, Any] = {
        "id": op_id,
        "type": "Hole",
        "profile": id_map.get(profile_name or "", profile_name or ""),
        "diameter": round_value(diameter) if diameter is not None else 0.0,
    }

    # FreeCAD Hole DepthType: 0=Dimension, 1=ThroughAll, 2=UpToFirst, 3=UpToLast
    if depth_type == HOLE_DEPTH_THROUGH_ALL:
        operation["depth"] = "through_all"
    elif depth is not None:
        operation["depth"] = round_value(depth)

    if reversed_dir:
        operation["reversed"] = True
    return operation


def extract_fillet(obj: ET.Element, op_id: str, id_map: dict[str, str]) -> dict[str, Any]:
    radius = get_float(get_property(obj, "Radius"))
    base_name, subs = get_link_sub_parts(get_property(obj, "Base"))
    use_all = get_bool(get_property(obj, "UseAllEdges"), False)

    return {
        "id": op_id,
        "type": "Fillet",
        "radius": round_value(radius) if radius is not None else 0.0,
        "edges": _build_edge_refs(base_name, subs, id_map, use_all),
    }


def extract_chamfer(obj: ET.Element, op_id: str, id_map: dict[str, str]) -> dict[str, Any]:
    distance = get_float(get_property(obj, "Size"))
    base_name, subs = get_link_sub_parts(get_property(obj, "Base"))
    use_all = get_bool(get_property(obj, "UseAllEdges"), False)

    return {
        "id": op_id,
        "type": "Chamfer",
        "distance": round_value(distance) if distance is not None else 0.0,
        "edges": _build_edge_refs(base_name, subs, id_map, use_all),
    }


def _build_edge_refs(
    base_name: str | None,
    subs: list[str],
    id_map: dict[str, str],
    use_all: bool,
) -> list[dict[str, Any]]:
    if use_all:
        return [{"type": "all"}]

    if not base_name or not subs:
        return []

    reference = id_map.get(base_name, base_name)
    return [
        {
            "reference": reference,
            "selector": sub,
        }
        for sub in subs
        if sub
    ]
