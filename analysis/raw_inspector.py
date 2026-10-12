"""Inspect raw FCStd documents for features not fully handled by the parser."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from parser.fcstd_reader import FCStdDocument, read_fcstd
from parser.utils.xml_helpers import get_property

from analysis.constants import (
    CONSTRAINT_TYPE_MAP,
    GEOMETRY_TYPE_MAP,
    OPERATION_TYPE_MAP,
    PARSER_SUPPORTED_TYPES,
)
from analysis.models import SketchStats


def operation_label(type_id: str) -> str:
    """Map a FreeCAD TypeId to a human-readable operation label."""
    if type_id in OPERATION_TYPE_MAP:
        return OPERATION_TYPE_MAP[type_id]
    if type_id.startswith("PartDesign::"):
        return type_id.split("::", 1)[1].replace("_", " ")
    if type_id.startswith("Sketcher::"):
        return type_id.split("::", 1)[1].replace("_", " ")
    return type_id


def is_construction_geometry(geom: ET.Element) -> bool:
    construction = geom.find("Construction")
    return construction is not None and construction.get("value") == "1"


def geometry_label(geom: ET.Element) -> str:
    """Classify a sketch geometry element."""
    geom_type = geom.get("type", "")
    return GEOMETRY_TYPE_MAP.get(geom_type, geom_type.replace("Part::Geom", "") or "Unknown")


def constraint_label(constrain: ET.Element) -> str:
    type_code = int(constrain.get("Type", "-1"))
    return CONSTRAINT_TYPE_MAP.get(type_code, f"Unknown({type_code})")


def inspect_sketch_object(obj: ET.Element, sketch_name: str) -> SketchStats:
    """Extract sketch geometry and constraint statistics from raw XML."""
    stats = SketchStats(sketch_name=sketch_name)

    geometry_prop = get_property(obj, "Geometry")
    geometry_list = geometry_prop.find("GeometryList") if geometry_prop is not None else None
    if geometry_list is not None:
        for geom in geometry_list.findall("Geometry"):
            label = geometry_label(geom)
            stats.geometry_counts[label] = stats.geometry_counts.get(label, 0) + 1
            stats.entity_count += 1
            if is_construction_geometry(geom):
                stats.construction_count += 1

    constraints_prop = get_property(obj, "Constraints")
    constraint_list = constraints_prop.find("ConstraintList") if constraints_prop is not None else None
    if constraint_list is not None:
        for constrain in constraint_list.findall("Constrain"):
            label = constraint_label(constrain)
            stats.constraint_counts[label] = stats.constraint_counts.get(label, 0) + 1
            stats.constraint_count += 1

    return stats


def inspect_body_features(document: FCStdDocument) -> dict[str, Any]:
    """Inspect all features in the PartDesign body feature tree."""
    operation_counts: dict[str, int] = {}
    unsupported_operation_counts: dict[str, int] = {}
    feature_sequence: list[str] = []
    sketches: list[SketchStats] = []

    for feature_name in document.body_feature_order:
        type_id = document.object_types.get(feature_name, "Unknown")
        label = operation_label(type_id)
        operation_counts[label] = operation_counts.get(label, 0) + 1
        feature_sequence.append(label)

        if type_id not in PARSER_SUPPORTED_TYPES:
            unsupported_operation_counts[label] = unsupported_operation_counts.get(label, 0) + 1

        if type_id == "Sketcher::SketchObject":
            obj = document.object_data.get(feature_name)
            if obj is not None:
                sketches.append(inspect_sketch_object(obj, feature_name))

    partdesign_count = sum(
        count
        for label, count in operation_counts.items()
        if label != "Sketch"
    )

    return {
        "feature_tree_depth": len(document.body_feature_order),
        "partdesign_operation_count": partdesign_count,
        "sketch_count": operation_counts.get("Sketch", 0),
        "operation_counts": operation_counts,
        "unsupported_operation_counts": unsupported_operation_counts,
        "feature_sequence": feature_sequence,
        "sketches": sketches,
    }


def load_document(path: str) -> FCStdDocument:
    """Load an FCStd document using the shared parser reader."""
    return read_fcstd(path)
