"""Inspect raw FCStd Document.xml without relying on parser feature extraction."""

from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from parser.utils.xml_helpers import get_property, get_string

from analysis.forensics.models import BodyRecord, DocumentForensics, ObjectRecord

PARTDESIGN_FEATURE_PREFIX = "PartDesign::"
SKETCHER_TYPE = "Sketcher::SketchObject"
BODY_TYPE = "PartDesign::Body"


def _read_document_xml(path: Path) -> ET.Element:
    with zipfile.ZipFile(path, "r") as archive:
        if "Document.xml" not in archive.namelist():
            raise ValueError("Missing Document.xml")
        with archive.open("Document.xml") as handle:
            return ET.parse(handle).getroot()


def _object_label(obj_data: ET.Element | None) -> str:
    if obj_data is None:
        return ""
    label = get_string(get_property(obj_data, "Label"))
    return label or ""


def _build_parent_map(object_data: dict[str, ET.Element]) -> dict[str, str]:
    """Map child object name -> parent object name via Group/Objects LinkList."""
    parent_map: dict[str, str] = {}
    group_property_names = {"Group", "Objects", "GroupLinks"}

    for parent_name, obj in object_data.items():
        for prop in obj.findall("./Properties/Property"):
            if prop.get("name") not in group_property_names:
                continue
            link_list = prop.find("LinkList")
            if link_list is None:
                continue
            for link in link_list.findall("Link"):
                child = link.get("value", "")
                if child:
                    parent_map[child] = parent_name

    return parent_map


def _extract_body_group(obj_data: ET.Element) -> list[str]:
    group_prop = get_property(obj_data, "Group")
    if group_prop is None:
        return []
    link_list = group_prop.find("LinkList")
    if link_list is None:
        return []
    return [link.get("value", "") for link in link_list.findall("Link") if link.get("value")]


def _extract_body_tip(obj_data: ET.Element) -> str:
    tip = get_string(get_property(obj_data, "Tip"))
    return tip or ""


def _count_partdesign_features(feature_names: list[str], object_types: dict[str, str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for name in feature_names:
        type_id = object_types.get(name, "")
        if type_id.startswith(PARTDESIGN_FEATURE_PREFIX) and type_id != BODY_TYPE:
            short = type_id.split("::", 1)[1]
            counts[short] = counts.get(short, 0) + 1
    return counts


def _top_level_types(
    object_records: list[ObjectRecord],
    parent_map: dict[str, str],
) -> list[str]:
    top_level: list[str] = []
    seen: set[str] = set()
    for record in object_records:
        if record.parent:
            continue
        if record.type_id.startswith(("App::Origin", "App::Line", "App::Plane", "App::Point")):
            continue
        if record.type_id not in seen:
            seen.add(record.type_id)
            top_level.append(record.type_id)
    return top_level


def inspect_document(
    path: Path | str,
    *,
    dataset_id: str = "",
    repository: str = "",
    original_relative_path: str = "",
) -> DocumentForensics:
    """Perform a raw structural inspection of one FCStd file."""
    path = Path(path)
    result = DocumentForensics(
        filename=path.name,
        dataset_id=dataset_id,
        repository=repository,
        original_relative_path=original_relative_path,
        file_size_bytes=path.stat().st_size if path.exists() else 0,
    )

    try:
        root = _read_document_xml(path)
    except Exception as exc:  # noqa: BLE001
        result.read_error = str(exc)
        return result

    object_types: dict[str, str] = {}
    for obj in root.findall("./Objects/Object"):
        name = obj.get("name", "")
        type_id = obj.get("type", "")
        if name and type_id:
            object_types[name] = type_id
            result.type_counts[type_id] = result.type_counts.get(type_id, 0) + 1

    object_data: dict[str, ET.Element] = {}
    for obj in root.findall("./ObjectData/Object"):
        name = obj.get("name", "")
        if name:
            object_data[name] = obj

    parent_map = _build_parent_map(object_data)

    for name, type_id in sorted(object_types.items()):
        result.objects.append(
            ObjectRecord(
                name=name,
                label=_object_label(object_data.get(name)),
                type_id=type_id,
                parent=parent_map.get(name, ""),
            )
        )

    result.object_count = len(result.objects)
    result.top_level_object_types = _top_level_types(result.objects, parent_map)

    body_names = [name for name, type_id in object_types.items() if type_id == BODY_TYPE]
    result.body_count = len(body_names)
    result.has_partdesign_body = result.body_count > 0
    result.has_body_named_body = "Body" in body_names

    for body_name in sorted(body_names):
        body_data = object_data.get(body_name)
        if body_data is None:
            continue
        feature_names = _extract_body_group(body_data)
        feature_types = _count_partdesign_features(feature_names, object_types)
        sketch_count = sum(
            1 for feature in feature_names if object_types.get(feature) == SKETCHER_TYPE
        )
        result.bodies.append(
            BodyRecord(
                name=body_name,
                label=_object_label(body_data),
                feature_count=len(feature_names),
                feature_types=feature_types,
                feature_names=feature_names,
                tip=_extract_body_tip(body_data),
                depth=len(feature_names),
                sketch_count=sketch_count,
            )
        )

    result.sketch_count = result.type_counts.get(SKETCHER_TYPE, 0)
    result.partdesign_feature_count = sum(
        count
        for type_id, count in result.type_counts.items()
        if type_id.startswith(PARTDESIGN_FEATURE_PREFIX) and type_id != BODY_TYPE
    )

    result.flags = compute_content_flags(result.type_counts, result.objects, parent_map)
    return result


def compute_content_flags(
    type_counts: dict[str, int],
    objects: list[ObjectRecord],
    parent_map: dict[str, str],
) -> dict[str, bool]:
    """Boolean indicators for document content classes."""
    def has_prefix(prefix: str) -> bool:
        return any(type_id.startswith(prefix) for type_id in type_counts)

    part_features = sum(
        count
        for type_id, count in type_counts.items()
        if type_id.startswith("Part::") and "Part2D" not in type_id
    )
    mesh_count = sum(count for type_id, count in type_counts.items() if type_id.startswith("Mesh::"))
    sketch_count = type_counts.get(SKETCHER_TYPE, 0)
    body_count = type_counts.get(BODY_TYPE, 0)

    app_part_count = type_counts.get("App::Part", 0)
    link_group = has_prefix("App::Link") or type_counts.get("App::LinkGroup", 0) > 0

    meaningful = [
        obj
        for obj in objects
        if not obj.type_id.startswith(("App::Origin", "App::Line", "App::Plane", "App::Point"))
    ]

    return {
        "has_partdesign_body": body_count > 0,
        "has_app_part": app_part_count > 0,
        "has_part_feature": part_features > 0,
        "has_part_extrusion": type_counts.get("Part::Extrusion", 0) > 0,
        "has_sketcher": sketch_count > 0,
        "has_mesh": mesh_count > 0,
        "has_draft": has_prefix("Draft::"),
        "has_techdraw": has_prefix("TechDraw::"),
        "has_fem": has_prefix("Fem::"),
        "has_spreadsheet": has_prefix("Spreadsheet::"),
        "has_assembly_link": link_group,
        "has_imported_part": type_counts.get("Part::Feature", 0) > 0 and body_count == 0,
        "has_document_group": type_counts.get("App::DocumentObjectGroup", 0) > 0,
        "is_empty": len(meaningful) == 0,
    }
