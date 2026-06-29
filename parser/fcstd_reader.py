"""Read .FCStd archives and load Document.xml."""

from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FCStdDocument:
    """Parsed FreeCAD document metadata."""

    source_path: Path
    root: ET.Element
    object_types: dict[str, str] = field(default_factory=dict)
    object_data: dict[str, ET.Element] = field(default_factory=dict)
    body_feature_order: list[str] = field(default_factory=list)
    unit: str = "mm"
    label: str = ""


def read_fcstd(path: Path) -> FCStdDocument:
    """Open an .FCStd file and parse its Document.xml."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"FCStd file not found: {path}")

    with zipfile.ZipFile(path, "r") as archive:
        if "Document.xml" not in archive.namelist():
            raise ValueError(f"Invalid FCStd archive (missing Document.xml): {path}")
        with archive.open("Document.xml") as doc_file:
            root = ET.parse(doc_file).getroot()

    object_types: dict[str, str] = {}
    for obj in root.findall("./Objects/Object"):
        name = obj.get("name")
        obj_type = obj.get("type")
        if name and obj_type:
            object_types[name] = obj_type

    object_data: dict[str, ET.Element] = {}
    for obj in root.findall("./ObjectData/Object"):
        name = obj.get("name")
        if name:
            object_data[name] = obj

    body_order = _extract_body_feature_order(object_data)
    unit = _extract_unit(root)
    label = _extract_document_label(root)

    return FCStdDocument(
        source_path=path,
        root=root,
        object_types=object_types,
        object_data=object_data,
        body_feature_order=body_order,
        unit=unit,
        label=label,
    )


def _extract_document_label(root: ET.Element) -> str:
    for prop in root.findall("./Properties/Property"):
        if prop.get("name") == "Label":
            string = prop.find("String")
            if string is not None:
                return string.get("value", "")
    return ""


def _extract_unit(root: ET.Element) -> str:
    """Map FreeCAD UnitSystem enumeration to CAD JSON unit string."""
    for prop in root.findall("./Properties/Property"):
        if prop.get("name") != "UnitSystem":
            continue
        integer = prop.find("Integer")
        if integer is None:
            break
        index = int(integer.get("value", "0"))
        enum_list = prop.find("CustomEnumList")
        if enum_list is not None:
            enums = enum_list.findall("Enum")
            if 0 <= index < len(enums):
                label = enums[index].get("value", "").lower()
                if "inch" in label or "impérial" in label or "impérial" in label:
                    return "inch"
                if label.startswith("mks") or "(m," in label:
                    return "m"
                if "cm" in label and "mm" not in label:
                    return "cm"
        break
    return "mm"


def _extract_body_feature_order(object_data: dict[str, ET.Element]) -> list[str]:
    """Return PartDesign feature order from the first Body's Group property."""
    for name, obj in object_data.items():
        if name != "Body":
            continue
        for prop in obj.findall("./Properties/Property"):
            if prop.get("name") != "Group":
                continue
            link_list = prop.find("LinkList")
            if link_list is None:
                continue
            return [link.get("value", "") for link in link_list.findall("Link") if link.get("value")]
    return []
