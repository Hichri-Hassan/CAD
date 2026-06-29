"""Helpers for reading FreeCAD Document.xml property values."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any


def get_property(object_elem: ET.Element, name: str) -> ET.Element | None:
    """Return the Property element with the given name under an Object node."""
    for prop in object_elem.findall("./Properties/Property"):
        if prop.get("name") == name:
            return prop
    return None


def get_float(prop: ET.Element | None, default: float | None = None) -> float | None:
    if prop is None:
        return default
    node = prop.find("Float")
    if node is not None and node.get("value") is not None:
        return float(node.get("value"))
    return default


def get_bool(prop: ET.Element | None, default: bool | None = None) -> bool | None:
    if prop is None:
        return default
    node = prop.find("Bool")
    if node is not None and node.get("value") is not None:
        return node.get("value") == "true"
    return default


def get_int(prop: ET.Element | None, default: int | None = None) -> int | None:
    if prop is None:
        return default
    node = prop.find("Integer")
    if node is not None and node.get("value") is not None:
        return int(node.get("value"))
    return default


def get_string(prop: ET.Element | None, default: str | None = None) -> str | None:
    if prop is None:
        return default
    node = prop.find("String")
    if node is not None and node.get("value") is not None:
        return node.get("value")
    return default


def get_link(prop: ET.Element | None) -> str | None:
    if prop is None:
        return None
    node = prop.find("Link")
    if node is not None:
        return node.get("value") or None
    link_sub = prop.find("LinkSub")
    if link_sub is not None:
        return link_sub.get("value") or None
    return None


def get_link_sub_parts(prop: ET.Element | None) -> tuple[str | None, list[str]]:
    """Return (object_name, [sub_names]) from a LinkSub or LinkSubList property."""
    if prop is None:
        return None, []

    link_sub = prop.find("LinkSub")
    if link_sub is not None:
        subs = [sub.get("value", "") for sub in link_sub.findall("Sub")]
        return link_sub.get("value") or None, subs

    link_sub_list = prop.find("LinkSubList")
    if link_sub_list is not None:
        links = link_sub_list.findall("Link")
        if not links:
            return None, []
        link = links[0]
        return link.get("obj"), [link.get("sub", "")]

    return None, []


def round_value(value: float, decimals: int = 3) -> float:
    return round(value, decimals)


def round_point(point: list[float], decimals: int = 3) -> list[float]:
    return [round_value(v, decimals) for v in point]


def get_placement(prop: ET.Element | None) -> dict[str, list[float]] | None:
    """Parse App::PropertyPlacement (PropertyPlacement child node)."""
    if prop is None:
        return None
    node = prop.find("PropertyPlacement")
    if node is None:
        return None
    return {
        "position": round_point([
            float(node.get("Px", 0)),
            float(node.get("Py", 0)),
            float(node.get("Pz", 0)),
        ]),
        "rotation": round_point([
            float(node.get("Q0", 0)),
            float(node.get("Q1", 0)),
            float(node.get("Q2", 0)),
            float(node.get("Q3", 1)),
        ], decimals=6),
    }


def is_identity_placement(placement: dict[str, list[float]]) -> bool:
    """Return True when placement is zero translation and identity rotation."""
    position = placement["position"]
    rotation = placement["rotation"]
    if any(abs(v) > 1e-9 for v in position):
        return False
    return (
        abs(rotation[0]) < 1e-9
        and abs(rotation[1]) < 1e-9
        and abs(rotation[2]) < 1e-9
        and abs(rotation[3] - 1.0) < 1e-9
    )
