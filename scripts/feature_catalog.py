"""Controlled CAD-feature families for synthetic training data.

This file defines how we author compiler-valid CAD JSON for synthetic
feature families, compile to FreeCAD PartDesign .FCStd, and produce
training examples (prompt/operations pairs).

Important:
- The FCStd parser is used for round-trip validation only.
- For through-holes, we author PartDesign::Sketch + PartDesign::Pad
  then PartDesign::Hole with depth="through_all".
"""

from __future__ import annotations

import math
import sys
from typing import Any, Callable
from dataclasses import dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from primitive_catalog import _rect_sketch_entities, format_mm


# Existing centered through-hole dataset (must remain backward-compatible).
REFERENCE_THROUGH_HOLE: dict[str, Any] = {
    "length": 60.0,
    "width": 40.0,
    "height": 20.0,
    "diameter": 10.0,
    "hole_centers": [(30.0, 20.0)],
    # For reporting only (not used by compiler/parser).
    "source_level": 1,
}

# How much clearance (mm) we require between hole edge and solid edges.
EDGE_CLEARANCE_MM = 3.0


def circle_radius_from_diameter(diameter: float) -> float:
    return diameter / 2.0


def hole_centers(dims: dict[str, Any]) -> list[tuple[float, float]]:
    centers = dims.get("hole_centers")
    if not centers:
        # Default: centered single-hole.
        return [(dims["length"] / 2.0, dims["width"] / 2.0)]
    return [(float(x), float(y)) for x, y in centers]


def hole_count(dims: dict[str, Any]) -> int:
    return len(hole_centers(dims))


def hole_center(dims: dict[str, Any]) -> tuple[float, float]:
    # Backward-compatible helper for single-hole use-cases.
    centers = hole_centers(dims)
    return centers[0]


def expected_volume(dims: dict[str, Any]) -> float:
    """Through-all volume: prism minus sum of cylindrical hole volumes."""
    n = hole_count(dims)
    prism = dims["length"] * dims["width"] * dims["height"]
    r = circle_radius_from_diameter(dims["diameter"])
    hole = n * math.pi * (r**2) * dims["height"]
    return prism - hole


def expected_bbox(dims: dict[str, Any]) -> dict[str, float]:
    return {
        "xmin": 0.0,
        "ymin": 0.0,
        "zmin": 0.0,
        "xmax": float(dims["length"]),
        "ymax": float(dims["width"]),
        "zmax": float(dims["height"]),
    }


def _is_centered_single(dims: dict[str, Any], *, tol: float = 1e-6) -> bool:
    if hole_count(dims) != 1:
        return False
    cx, cy = hole_centers(dims)[0]
    return abs(cx - dims["length"] / 2.0) <= tol and abs(cy - dims["width"] / 2.0) <= tol


def through_hole_filename(index: int, dims: dict[str, Any]) -> str:
    """
    Backward-compatible naming:
    - If the hole is a single centered hole, keep the original filename format:
      through_hole_{i}_l{L}_w{W}_h{H}_d{D}mm
    - Otherwise, include hole centers in the filename to avoid collisions.
    """
    base = (
        f"through_hole_{index:02d}_"
        f"l{format_mm(dims['length'])}_"
        f"w{format_mm(dims['width'])}_"
        f"h{format_mm(dims['height'])}_"
        f"d{format_mm(dims['diameter'])}mm"
    )

    if _is_centered_single(dims):
        return base

    centers = sorted(hole_centers(dims))
    n = len(centers)
    if n == 1:
        cx, cy = centers[0]
        return f"{base}_x{format_mm(cx)}_y{format_mm(cy)}"

    centers_str = "_".join(f"x{format_mm(cx)}_y{format_mm(cy)}" for cx, cy in centers)
    return f"{base}_n{n}_{centers_str}"


def through_hole_operations(dims: dict[str, Any]) -> list[dict[str, Any]]:
    length = float(dims["length"])
    width = float(dims["width"])
    height = float(dims["height"])
    diameter = float(dims["diameter"])

    r = circle_radius_from_diameter(diameter)
    centers = hole_centers(dims)

    circle_entities: list[dict[str, Any]] = []
    for idx, (cx, cy) in enumerate(centers, start=1):
        circle_entities.append(
            {
                "id": f"e_00{idx}",
                "type": "Circle",
                "center": [float(cx), float(cy)],
                "radius": r,
            }
        )

    # Sketch op_003 must be attached to the TOP face of the pad for Hole to cut correctly.
    # For rectangular PartDesign::Pad blocks, Face6 is the top face in this project.
    return [
        {
            "id": "op_001",
            "type": "Sketch",
            "entities": _rect_sketch_entities(length, width),
            "constraints": [],
            "plane": "XY",
        },
        {
            "id": "op_002",
            "type": "Pad",
            "profile": "op_001",
            "length": height,
        },
        {
            "id": "op_003",
            "type": "Sketch",
            "entities": circle_entities,
            "constraints": [],
            "support": {"type": "face", "reference": "op_002", "selector": "Face6"},
        },
        {
            "id": "op_004",
            "type": "Hole",
            "profile": "op_003",
            "diameter": diameter,
            "depth": "through_all",
        },
    ]


def through_hole_cad_json(dims: dict[str, Any], *, source_label: str) -> dict[str, Any]:
    return {
        "metadata": {
            "version": "1.0",
            "unit": "mm",
            "source_format": "authored",
            "feature_family": "through_hole",
            "source_label": source_label,
        },
        "operations": through_hole_operations(dims),
    }


def _fmt_xy(x: float, y: float) -> str:
    return f"({format_mm(x)}, {format_mm(y)})"


def _fmt_from_edges(cx: float, cy: float) -> str:
    return f"{format_mm(cx)} mm from the left edge and {format_mm(cy)} mm from the bottom edge"


def through_hole_prompts(dims: dict[str, Any]) -> list[str]:
    length = format_mm(float(dims["length"]))
    width = format_mm(float(dims["width"]))
    height = format_mm(float(dims["height"]))
    diameter = format_mm(float(dims["diameter"]))
    centers = sorted(hole_centers(dims))
    n = len(centers)

    # Level 1: centered single-hole (keep prompt style already validated).
    if n == 1 and _is_centered_single(dims):
        return [
            (
                f"Create a rectangular prism {length} mm long, {width} mm wide, and {height} mm high, "
                f"with a centered through-hole of {diameter} mm diameter going through the entire height of the prism."
            ),
            (
                f"Generate a {length} × {width} × {height} mm block with a centered "
                f"{diameter} mm diameter through-hole."
            ),
            (
                f"Make a {length} by {width} by {height} millimeter rectangular prism "
                f"with a {diameter} mm hole through the full height."
            ),
            (
                f"Build a rectangular block measuring {length} × {width} × {height} mm "
                f"with a centered circular through-hole of diameter {diameter} mm."
            ),
            (
                f"I need a {length} mm × {width} mm × {height} mm prism with a "
                f"{diameter} mm diameter hole through all."
            ),
        ]

    if n == 1:
        cx, cy = centers[0]
        return [
            (
                f"Create a {length} × {width} × {height} mm rectangular block with a "
                f"{diameter} mm diameter through-hole located {format_mm(cx)} mm from the left edge "
                f"and {format_mm(cy)} mm from the bottom edge."
            ),
            (
                f"Generate a {length} by {width} by {height} millimeter prism with a through-hole "
                f"of {diameter} mm passing fully through, with the hole center at {_fmt_xy(cx, cy)}."
            ),
            (
                f"Make a {length} mm long, {width} mm wide, and {height} mm high block "
                f"with a {diameter} mm diameter hole through all. Position it {_fmt_from_edges(cx, cy)}."
            ),
            (
                f"Build a rectangular solid measuring {length} × {width} × {height} mm "
                f"with a {diameter} mm through hole at hole center {_fmt_xy(cx, cy)}."
            ),
            (
                f"I need a {length} × {width} × {height} mm prism featuring a {diameter} mm hole through all. "
                f"The hole center is at {_fmt_xy(cx, cy)}."
            ),
        ]

    coords = [_fmt_xy(x, y) for x, y in centers]
    if n == 2:
        c1, c2 = coords
        return [
            (
                f"Create a {length} × {width} × {height} mm plate with two {diameter} mm diameter through-holes "
                f"at positions {c1} and {c2}."
            ),
            (
                f"Generate a {length} by {width} by {height} millimeter block with two through-holes "
                f"({c1}) and ({c2}), each passing through the full height."
            ),
            (
                f"Make a {length} mm long, {width} mm wide, and {height} mm high rectangular prism "
                f"with two {diameter} mm holes through all, hole centers at {c1} and {c2}."
            ),
            (
                f"Build a rectangular solid measuring {length} × {width} × {height} mm "
                f"with two {diameter} mm through-holes placed at {c1} and {c2}."
            ),
            (
                f"I need a {length} × {width} × {height} mm prism containing two {diameter} mm through holes. "
                f"Place their centers at {c1} and {c2}."
            ),
        ]

    if n == 4:
        c1, c2, c3, c4 = coords
        return [
            (
                f"Create a {length} × {width} × {height} mm plate with four {diameter} mm diameter through-holes "
                f"at positions {c1}, {c2}, {c3}, and {c4}."
            ),
            (
                f"Generate a {length} by {width} by {height} millimeter block with four through holes "
                f"({c1}), ({c2}), ({c3}), and ({c4}), each going through the full thickness."
            ),
            (
                f"Make a {length} mm long, {width} mm wide, and {height} mm high rectangular prism "
                f"with four {diameter} mm holes through all, hole centers at {c1}, {c2}, {c3}, {c4}."
            ),
            (
                f"Build a rectangular solid measuring {length} × {width} × {height} mm "
                f"with four {diameter} mm through-holes at {c1}, {c2}, {c3}, and {c4}."
            ),
            (
                f"I need a {length} × {width} × {height} mm prism featuring four {diameter} mm through holes. "
                f"Place their centers at {c1}, {c2}, {c3}, and {c4}."
            ),
        ]

    # Generic fallback
    coords_str = ", ".join(coords)
    return [
        (
            f"Create a {length} × {width} × {height} mm solid with {n} through-holes of diameter {diameter} mm. "
            f"Hole centers are at {coords_str}."
        ),
        (
            f"Generate a {length} by {width} by {height} millimeter block with {n} circular through holes "
            f"at {coords_str}, each going through the full height."
        ),
        (
            f"Make a {length} × {width} × {height} mm prism with {n} {diameter} mm holes through all. "
            f"Place centers at {coords_str}."
        ),
        (
            f"Build a rectangular solid measuring {length} × {width} × {height} mm "
            f"with {n} through-holes at {coords_str}."
        ),
        (
            f"I need a {length} mm × {width} mm × {height} mm part with {n} holes of diameter {diameter} mm. "
            f"Centers: {coords_str}."
        ),
    ]


def _assert_valid_through_hole_dims(d: dict[str, Any]) -> None:
    L, W, H, D = float(d["length"]), float(d["width"]), float(d["height"]), float(d["diameter"])
    if H <= 0:
        raise ValueError("Prism height must be positive.")
    if D <= 0:
        raise ValueError("Hole diameter must be positive.")
    r = circle_radius_from_diameter(D)

    centers = hole_centers(d)
    if len(centers) != hole_count(d):
        raise ValueError("Invalid hole_centers structure.")

    # Each hole must be fully inside the solid boundaries with clearance.
    for cx, cy in centers:
        if cx < r + EDGE_CLEARANCE_MM or cx > L - r - EDGE_CLEARANCE_MM:
            raise ValueError(f"Hole center x={cx} invalid for {L=} and {D=}")
        if cy < r + EDGE_CLEARANCE_MM or cy > W - r - EDGE_CLEARANCE_MM:
            raise ValueError(f"Hole center y={cy} invalid for {W=} and {D=}")

    # Non-overlap: distance between centers must be >= D (2r) plus a small epsilon.
    min_dist = D + 0.5
    for i in range(len(centers)):
        for j in range(i + 1, len(centers)):
            x1, y1 = centers[i]
            x2, y2 = centers[j]
            if math.hypot(x1 - x2, y1 - y2) < min_dist:
                raise ValueError("Overlapping hole circles.")


def through_hole_dimensions(count: int) -> list[dict[str, Any]]:
    """
    Build dims for a controlled diversified through-hole dataset.

    We keep indices 1..30 identical to the existing centered dataset.
    Additional indices introduce off-center, thin plates, and 2/4 holes.
    """

    # Level 1: reproduce existing centered examples (length/width/height/diameter only).
    centered_specs = [
        (60, 40, 20, 10),
        (80, 50, 15, 8),
        (100, 60, 25, 12),
        (50, 30, 10, 6),
        (70, 45, 18, 10),
        (90, 55, 22, 14),
        (120, 70, 30, 16),
        (65, 35, 12, 8),
        (75, 40, 16, 10),
        (85, 50, 20, 12),
        (95, 60, 24, 14),
        (110, 65, 28, 16),
        (55, 35, 14, 8),
        (45, 30, 12, 6),
        (130, 80, 20, 18),
        (40, 25, 8, 5),
        (150, 90, 25, 20),
        (72, 48, 18, 10),
        (88, 52, 16, 12),
        (64, 42, 22, 8),
        (108, 62, 26, 14),
        (96, 44, 12, 10),
        (58, 38, 15, 7),
        (82, 46, 19, 11),
        (140, 75, 30, 18),
        (68, 36, 14, 9),
        (52, 32, 11, 6),
        (76, 54, 21, 12),
        (114, 68, 24, 15),
        (48, 28, 9, 5),
    ]

    def centered_item(L: float, W: float, H: float, D: float, *, level: int) -> dict[str, Any]:
        cx, cy = L / 2.0, W / 2.0
        d = {
            "length": float(L),
            "width": float(W),
            "height": float(H),
            "diameter": float(D),
            "hole_centers": [(cx, cy)],
            "source_level": level,
        }
        _assert_valid_through_hole_dims(d)
        return d

    def single_item(L: float, W: float, H: float, D: float, cx: float, cy: float, *, level: int) -> dict[str, Any]:
        d = {
            "length": float(L),
            "width": float(W),
            "height": float(H),
            "diameter": float(D),
            "hole_centers": [(float(cx), float(cy))],
            "source_level": level,
        }
        _assert_valid_through_hole_dims(d)
        return d

    def multi_item(L: float, W: float, H: float, D: float, centers: list[tuple[float, float]], *, level: int) -> dict[str, Any]:
        d = {
            "length": float(L),
            "width": float(W),
            "height": float(H),
            "diameter": float(D),
            "hole_centers": [(float(x), float(y)) for x, y in centers],
            "source_level": level,
        }
        _assert_valid_through_hole_dims(d)
        return d

    items: list[dict[str, Any]] = []

    # Add centered items first (indices 1..30).
    for i, (L, W, H, D) in enumerate(centered_specs, start=1):
        if len(items) >= count:
            return items
        items.append(centered_item(L, W, H, D, level=1))

    # Off-center single holes (16)
    off_center_specs = [
        (80, 50, 20, 10, 18, 22),
        (90, 55, 22, 12, 25, 20),
        (120, 70, 30, 16, 35, 28),
        (65, 35, 15, 8, 14, 10),
        (140, 75, 25, 14, 40, 30),
        (72, 48, 18, 10, 20, 26),
        (50, 30, 12, 6, 12, 15),
        (110, 65, 28, 16, 28, 40),
        (105, 48, 20, 12, 30, 12),
        (88, 52, 16, 10, 22, 30),
        (76, 54, 21, 12, 25, 18),
        (64, 42, 22, 12, 18, 26),
        (130, 80, 20, 14, 45, 35),
        (92, 58, 17, 10, 30, 20),
        (108, 62, 26, 14, 36, 24),
        (114, 68, 24, 12, 28, 40),
    ]
    for L, W, H, D, cx, cy in off_center_specs:
        if len(items) >= count:
            return items
        items.append(single_item(L, W, H, D, cx, cy, level=2))

    # Thin plates (12): height <= 6
    thin_specs = [
        (100, 60, 4, 8, 50, 30),  # centered
        (120, 80, 5, 10, 60, 40),
        (90, 45, 3, 6, 45, 22.5),
        (140, 70, 4, 10, 70, 35),
        (80, 50, 6, 8, 40, 25),
        (110, 65, 5, 10, 55, 32.5),
        # off-center thin
        (100, 60, 4, 8, 20, 30),
        (120, 80, 5, 10, 80, 30),
        (90, 45, 3, 6, 25, 15),
        (140, 70, 4, 10, 25, 20),
        (80, 50, 6, 8, 15, 20),
        (110, 65, 5, 10, 35, 40),
    ]
    for L, W, H, D, cx, cy in thin_specs:
        if len(items) >= count:
            return items
        items.append(single_item(L, W, H, D, cx, cy, level=2))

    # Two holes (10): two circles, same diameter.
    two_hole_specs = [
        (100, 50, 10, 8, [(25, 25), (75, 25)]),  # X
        (90, 60, 20, 10, [(45, 20), (45, 40)]),  # Y
        (120, 70, 12, 10, [(30, 20), (90, 50)]),  # diagonal
        (80, 50, 8, 8, [(20, 20), (60, 30)]),  # asymmetric
        (110, 65, 18, 12, [(27.5, 32.5), (82.5, 32.5)]),  # X
        (140, 75, 10, 12, [(35, 37.5), (105, 37.5)]),
        (60, 40, 15, 6, [(15, 20), (45, 20)]),
        (95, 55, 20, 10, [(23.75, 27.5), (71.25, 27.5)]),
        (105, 60, 12, 10, [(52.5, 15), (52.5, 45)]),
        (130, 80, 8, 12, [(32.5, 40), (97.5, 40)]),
    ]
    for L, W, H, D, centers in two_hole_specs:
        if len(items) >= count:
            return items
        items.append(multi_item(L, W, H, D, centers, level=2))

    # Four holes (7): corners
    four_hole_specs = [
        (120, 80, 5, 6),
        (140, 90, 6, 8),
        (100, 60, 5, 8),
        (160, 100, 8, 10),
        (130, 85, 6, 8),
        (110, 70, 5, 8),
        (150, 95, 7, 10),
    ]
    for L, W, H, D in four_hole_specs:
        if len(items) >= count:
            return items
        r = circle_radius_from_diameter(D)
        m = r + EDGE_CLEARANCE_MM
        centers = [(m, m), (L - m, m), (m, W - m), (L - m, W - m)]
        items.append(multi_item(L, W, H, D, centers, level=2))

    return items[:count]


@dataclass(frozen=True)
class FeatureFamily:
    family_id: str
    folder: str
    filename_builder: Callable[[int, dict[str, Any]], str]
    operations_builder: Callable[[dict[str, Any]], list[dict[str, Any]]]
    cad_json_builder: Callable[[dict[str, Any], str], dict[str, Any]]
    prompt_builder: Callable[[dict[str, Any]], list[str]]
    dimension_builder: Callable[[int], list[dict[str, Any]]]
    reference_dims: dict[str, Any]


FEATURE_FAMILIES: dict[str, FeatureFamily] = {
    "through_hole": FeatureFamily(
        family_id="through_hole",
        folder="through_holes",
        filename_builder=through_hole_filename,
        operations_builder=through_hole_operations,
        cad_json_builder=lambda dims, label: through_hole_cad_json(dims, source_label=label),
        prompt_builder=through_hole_prompts,
        dimension_builder=through_hole_dimensions,
        reference_dims=REFERENCE_THROUGH_HOLE,
    ),
}


# ---------------------------------------------------------------------------
# BLIND HOLE family
# ---------------------------------------------------------------------------

# Top-face selectors per base geometry (determined empirically from FreeCAD).
_TOP_FACE: dict[str, str] = {
    "rect": "Face6",
    "plate": "Face6",
    "triangle": "Face5",
    "cylinder": "Face3",
}

REFERENCE_BLIND_HOLE: dict[str, Any] = {
    "base_type": "rect",
    "length": 60.0,
    "width": 40.0,
    "height": 20.0,
    "diameter": 10.0,
    "hole_depth": 8.0,
    "hole_cx": 30.0,
    "hole_cy": 20.0,
}


def _tri_sketch_entities(base: float, tri_h: float) -> list[dict[str, Any]]:
    return [
        {"id": "e_001", "type": "Line", "start": [0.0, 0.0], "end": [base, 0.0]},
        {"id": "e_002", "type": "Line", "start": [base, 0.0], "end": [base / 2.0, tri_h]},
        {"id": "e_003", "type": "Line", "start": [base / 2.0, tri_h], "end": [0.0, 0.0]},
    ]


def _cyl_sketch_entities(radius: float) -> list[dict[str, Any]]:
    return [{"id": "e_001", "type": "Circle", "center": [0.0, 0.0], "radius": radius}]


def blind_hole_base_sketch(dims: dict[str, Any]) -> list[dict[str, Any]]:
    bt = dims["base_type"]
    if bt in ("rect", "plate"):
        return _rect_sketch_entities(dims["length"], dims["width"])
    if bt == "triangle":
        return _tri_sketch_entities(dims["base"], dims["triangle_height"])
    if bt == "cylinder":
        return _cyl_sketch_entities(dims["cyl_radius"])
    raise ValueError(f"Unknown base_type: {bt}")


def blind_hole_pad_height(dims: dict[str, Any]) -> float:
    bt = dims["base_type"]
    if bt in ("rect", "plate"):
        return float(dims["height"])
    if bt == "triangle":
        return float(dims["prism_height"])
    if bt == "cylinder":
        return float(dims["cyl_height"])
    raise ValueError(f"Unknown base_type: {bt}")


def blind_hole_operations(dims: dict[str, Any]) -> list[dict[str, Any]]:
    pad_h = blind_hole_pad_height(dims)
    diameter = float(dims["diameter"])
    hole_depth = float(dims["hole_depth"])
    r = circle_radius_from_diameter(diameter)
    cx = float(dims["hole_cx"])
    cy = float(dims["hole_cy"])
    bt = dims["base_type"]

    return [
        {
            "id": "op_001",
            "type": "Sketch",
            "entities": blind_hole_base_sketch(dims),
            "constraints": [],
            "plane": "XY",
        },
        {
            "id": "op_002",
            "type": "Pad",
            "profile": "op_001",
            "length": pad_h,
        },
        {
            "id": "op_003",
            "type": "Sketch",
            "entities": [
                {
                    "id": "e_001",
                    "type": "Circle",
                    "center": [cx, cy],
                    "radius": r,
                }
            ],
            "constraints": [],
            "support": {"type": "face", "reference": "op_002", "selector": _TOP_FACE[bt]},
        },
        {
            "id": "op_004",
            "type": "Hole",
            "profile": "op_003",
            "diameter": diameter,
            "depth": hole_depth,
        },
    ]


def blind_hole_cad_json(dims: dict[str, Any], *, source_label: str) -> dict[str, Any]:
    return {
        "metadata": {
            "version": "1.0",
            "unit": "mm",
            "source_format": "authored",
            "feature_family": "blind_hole",
            "source_label": source_label,
        },
        "operations": blind_hole_operations(dims),
    }


def blind_hole_expected_volume(dims: dict[str, Any]) -> float:
    bt = dims["base_type"]
    if bt in ("rect", "plate"):
        base_vol = dims["length"] * dims["width"] * dims["height"]
    elif bt == "triangle":
        base_vol = 0.5 * dims["base"] * dims["triangle_height"] * dims["prism_height"]
    elif bt == "cylinder":
        base_vol = math.pi * dims["cyl_radius"] ** 2 * dims["cyl_height"]
    else:
        raise ValueError(f"Unknown base_type: {bt}")
    r = circle_radius_from_diameter(dims["diameter"])
    hole_vol = math.pi * r**2 * dims["hole_depth"]
    return base_vol - hole_vol


def blind_hole_expected_bbox(dims: dict[str, Any]) -> dict[str, float]:
    bt = dims["base_type"]
    if bt in ("rect", "plate"):
        return {"xmin": 0.0, "ymin": 0.0, "zmin": 0.0,
                "xmax": float(dims["length"]), "ymax": float(dims["width"]), "zmax": float(dims["height"])}
    if bt == "triangle":
        return {"xmin": 0.0, "ymin": 0.0, "zmin": 0.0,
                "xmax": float(dims["base"]), "ymax": float(dims["triangle_height"]),
                "zmax": float(dims["prism_height"])}
    if bt == "cylinder":
        R = float(dims["cyl_radius"])
        return {"xmin": -R, "ymin": -R, "zmin": 0.0,
                "xmax": R, "ymax": R, "zmax": float(dims["cyl_height"])}
    raise ValueError(f"Unknown base_type: {bt}")


def _is_centered_blind(dims: dict[str, Any], *, tol: float = 1e-6) -> bool:
    bt = dims["base_type"]
    cx, cy = float(dims["hole_cx"]), float(dims["hole_cy"])
    if bt in ("rect", "plate"):
        return abs(cx - dims["length"] / 2.0) <= tol and abs(cy - dims["width"] / 2.0) <= tol
    if bt == "triangle":
        # Centroid of triangle (0,0)-(base,0)-(base/2, tri_h)
        centroid_x = (0 + dims["base"] + dims["base"] / 2.0) / 3.0
        centroid_y = (0 + 0 + dims["triangle_height"]) / 3.0
        return abs(cx - centroid_x) <= tol and abs(cy - centroid_y) <= tol
    if bt == "cylinder":
        return abs(cx) <= tol and abs(cy) <= tol
    return False


def blind_hole_filename(index: int, dims: dict[str, Any]) -> str:
    bt = dims["base_type"]
    d_str = format_mm(dims["diameter"])
    depth_str = format_mm(dims["hole_depth"])

    if bt in ("rect", "plate"):
        base = (
            f"blind_hole_{index:02d}_{bt}_"
            f"l{format_mm(dims['length'])}_w{format_mm(dims['width'])}_h{format_mm(dims['height'])}"
        )
    elif bt == "triangle":
        base = (
            f"blind_hole_{index:02d}_tri_"
            f"b{format_mm(dims['base'])}_th{format_mm(dims['triangle_height'])}_"
            f"ph{format_mm(dims['prism_height'])}"
        )
    elif bt == "cylinder":
        base = (
            f"blind_hole_{index:02d}_cyl_"
            f"r{format_mm(dims['cyl_radius'])}_h{format_mm(dims['cyl_height'])}"
        )
    else:
        base = f"blind_hole_{index:02d}_{bt}"

    pos = ""
    if not _is_centered_blind(dims):
        pos = f"_x{format_mm(dims['hole_cx'])}_y{format_mm(dims['hole_cy'])}"

    return f"{base}_d{d_str}_dp{depth_str}mm{pos}"


def blind_hole_prompts(dims: dict[str, Any]) -> list[str]:
    bt = dims["base_type"]
    diameter = format_mm(dims["diameter"])
    depth = format_mm(dims["hole_depth"])
    cx, cy = float(dims["hole_cx"]), float(dims["hole_cy"])
    centered = _is_centered_blind(dims)

    def _pos_phrase() -> str:
        if centered:
            return "centered"
        return f"at position ({format_mm(cx)}, {format_mm(cy)})"

    def _pos_phrase_alt() -> str:
        if centered:
            return "in the center"
        return f"with the hole center at ({format_mm(cx)}, {format_mm(cy)})"

    if bt in ("rect", "plate"):
        L = format_mm(dims["length"])
        W = format_mm(dims["width"])
        H = format_mm(dims["height"])
        shape_word = "plate" if bt == "plate" else "block"
        return [
            (
                f"Create a {L} × {W} × {H} mm {shape_word} with a {_pos_phrase()} "
                f"{diameter} mm diameter blind hole {depth} mm deep."
            ),
            (
                f"Make a {L} by {W} by {H} millimeter rectangular prism with a "
                f"Ø{diameter} mm blind hole drilled {depth} mm into the top face, {_pos_phrase_alt()}."
            ),
            (
                f"Generate a {L} × {W} × {H} mm {shape_word} containing a {diameter} mm diameter "
                f"hole that stops after {depth} mm, {_pos_phrase_alt()}."
            ),
            (
                f"I need a {L} mm × {W} mm × {H} mm {shape_word} with a {_pos_phrase()} "
                f"{diameter} mm blind hole {depth} mm deep from the top face."
            ),
            (
                f"Build a rectangular solid measuring {L} × {W} × {H} mm with a "
                f"{diameter} mm blind hole drilled to a depth of {depth} mm, {_pos_phrase_alt()}."
            ),
        ]

    if bt == "triangle":
        B = format_mm(dims["base"])
        TH = format_mm(dims["triangle_height"])
        PH = format_mm(dims["prism_height"])
        return [
            (
                f"Create a triangular prism with a {B} mm base, {TH} mm triangle height, "
                f"and {PH} mm extrusion length, with a {_pos_phrase()} {diameter} mm diameter "
                f"blind hole {depth} mm deep."
            ),
            (
                f"Make a triangular prism (base {B} mm, triangle height {TH} mm, length {PH} mm) "
                f"with a Ø{diameter} mm blind hole drilled {depth} mm into the top face, {_pos_phrase_alt()}."
            ),
            (
                f"Generate a {B} × {TH} × {PH} mm triangular prism containing a {diameter} mm "
                f"blind hole that stops after {depth} mm, {_pos_phrase_alt()}."
            ),
            (
                f"I need a triangular prism with base {B} mm, triangle height {TH} mm, "
                f"and prism height {PH} mm, with a {_pos_phrase()} {diameter} mm blind hole {depth} mm deep."
            ),
            (
                f"Build a triangular prism ({B} mm base, {TH} mm height, {PH} mm long) "
                f"with a {diameter} mm blind hole drilled to {depth} mm, {_pos_phrase_alt()}."
            ),
        ]

    if bt == "cylinder":
        CR = format_mm(dims["cyl_radius"])
        CD = format_mm(dims["cyl_radius"] * 2)
        CH = format_mm(dims["cyl_height"])
        return [
            (
                f"Create a cylinder {CD} mm in diameter and {CH} mm high with a "
                f"{_pos_phrase()} {diameter} mm diameter blind hole {depth} mm deep."
            ),
            (
                f"Make a cylindrical solid (radius {CR} mm, height {CH} mm) with a "
                f"Ø{diameter} mm blind hole drilled {depth} mm from the top face, {_pos_phrase_alt()}."
            ),
            (
                f"Generate a cylinder with diameter {CD} mm and height {CH} mm "
                f"containing a {diameter} mm blind hole that stops after {depth} mm, {_pos_phrase_alt()}."
            ),
            (
                f"I need a cylinder {CD} mm in diameter, {CH} mm tall, "
                f"with a {_pos_phrase()} {diameter} mm blind hole {depth} mm deep from the top."
            ),
            (
                f"Build a {CD} mm diameter, {CH} mm high cylinder with a "
                f"{diameter} mm blind hole drilled to a depth of {depth} mm, {_pos_phrase_alt()}."
            ),
        ]

    raise ValueError(f"Unknown base_type: {bt}")


def _assert_valid_blind_hole_dims(d: dict[str, Any]) -> None:
    bt = d["base_type"]
    D = float(d["diameter"])
    hole_depth = float(d["hole_depth"])
    r = circle_radius_from_diameter(D)
    cx, cy = float(d["hole_cx"]), float(d["hole_cy"])

    if D <= 0 or hole_depth <= 0:
        raise ValueError("Diameter and hole_depth must be positive.")

    pad_h = blind_hole_pad_height(d)
    if hole_depth >= pad_h:
        raise ValueError(f"Blind hole depth {hole_depth} >= pad height {pad_h}")
    if hole_depth < 1.0:
        raise ValueError("Blind hole depth too shallow (< 1 mm).")

    clr = EDGE_CLEARANCE_MM

    if bt in ("rect", "plate"):
        L, W = float(d["length"]), float(d["width"])
        if cx < r + clr or cx > L - r - clr:
            raise ValueError(f"Hole cx={cx} out of bounds for L={L}, D={D}")
        if cy < r + clr or cy > W - r - clr:
            raise ValueError(f"Hole cy={cy} out of bounds for W={W}, D={D}")

    elif bt == "triangle":
        base = float(d["base"])
        tri_h = float(d["triangle_height"])
        # The triangle is (0,0)-(base,0)-(base/2,tri_h).
        # Check if the circle (cx,cy,r) is inside the triangle with clearance.
        # Use inset: shrink each edge inward by (r + clr).
        # Simple conservative check: point must be inside triangle AND
        # distance to each edge >= r + clr.
        margin = r + clr
        # Edge 1: y >= margin (bottom edge y=0)
        if cy < margin:
            raise ValueError(f"Hole too close to bottom edge: cy={cy}")
        # Edge 2: line from (base,0) to (base/2,tri_h)
        # Normal pointing inward (leftward): (tri_h, base/2) normalized
        # Signed distance from point to line ax+by+c=0
        # Edge 2 direction: (-base/2, tri_h). Inward normal: (-tri_h, -base/2) → need sign
        # Use half-plane: the centroid is inside. Test if point is on same side as centroid.
        # Simpler: use barycentric or just shrink the triangle.
        _check_point_in_triangle_inset(cx, cy, base, tri_h, margin)

    elif bt == "cylinder":
        cyl_R = float(d["cyl_radius"])
        dist = math.hypot(cx, cy)
        if dist + r + clr > cyl_R:
            raise ValueError(f"Hole extends outside cylinder: dist={dist}, r={r}, R={cyl_R}")


def _check_point_in_triangle_inset(cx: float, cy: float, base: float, tri_h: float, margin: float) -> None:
    # Triangle vertices: A=(0,0), B=(base,0), C=(base/2, tri_h)
    # Check signed distance to each edge >= margin.
    # Edge AB: y=0, inward normal (0,1). Distance = cy.
    if cy < margin:
        raise ValueError(f"Hole center too close to bottom edge (cy={cy})")

    # Edge BC: from B=(base,0) to C=(base/2,tri_h)
    # Direction: (-base/2, tri_h). Normal (outward right): (tri_h, base/2)
    # Line equation: tri_h*(x - base) + (base/2)*(y - 0) = 0
    #   tri_h*x + base/2*y - tri_h*base = 0
    # Signed dist (positive = inside for centroid test)
    n2_len = math.hypot(tri_h, base / 2.0)
    d2 = (tri_h * base / 2.0 + (base / 2.0) * tri_h / 3.0 - tri_h * base) / n2_len
    # Actually let's just use a simple approach: compute distances properly.
    d_edge2 = _point_line_dist(cx, cy, base, 0.0, base / 2.0, tri_h)
    if d_edge2 < margin:
        raise ValueError(f"Hole center too close to edge BC (dist={d_edge2:.2f})")

    # Edge CA: from C=(base/2,tri_h) to A=(0,0)
    d_edge3 = _point_line_dist(cx, cy, base / 2.0, tri_h, 0.0, 0.0)
    if d_edge3 < margin:
        raise ValueError(f"Hole center too close to edge CA (dist={d_edge3:.2f})")

    # Also verify the point is actually inside the triangle (not outside on the far side).
    if not _point_in_triangle(cx, cy, 0.0, 0.0, base, 0.0, base / 2.0, tri_h):
        raise ValueError(f"Hole center ({cx},{cy}) is outside the triangle")


def _point_line_dist(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length < 1e-12:
        return math.hypot(px - x1, py - y1)
    return abs(dy * px - dx * py + x2 * y1 - y2 * x1) / length


def _point_in_triangle(px: float, py: float,
                       ax: float, ay: float,
                       bx: float, by: float,
                       cx_: float, cy_: float) -> bool:
    def sign(x1: float, y1: float, x2: float, y2: float, x3: float, y3: float) -> float:
        return (x1 - x3) * (y2 - y3) - (x2 - x3) * (y1 - y3)

    d1 = sign(px, py, ax, ay, bx, by)
    d2 = sign(px, py, bx, by, cx_, cy_)
    d3 = sign(px, py, cx_, cy_, ax, ay)

    has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
    has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
    return not (has_neg and has_pos)


def blind_hole_dimensions(count: int) -> list[dict[str, Any]]:
    """Build dims for a controlled diversified blind-hole dataset."""

    items: list[dict[str, Any]] = []

    def _add(d: dict[str, Any]) -> None:
        if len(items) >= count:
            return
        _assert_valid_blind_hole_dims(d)
        items.append(d)

    # ---- A. Rectangular prisms (20) ----
    rect_specs: list[tuple] = [
        # (L, W, H, D, depth, cx, cy)  — centered
        (60, 40, 20, 10, 8, 30, 20),
        (80, 50, 25, 12, 15, 40, 25),
        (100, 60, 30, 14, 20, 50, 30),
        (50, 30, 15, 8, 6, 25, 15),
        (70, 45, 22, 10, 12, 35, 22.5),
        (90, 55, 28, 16, 18, 45, 27.5),
        (120, 70, 35, 18, 25, 60, 35),
        (65, 35, 18, 8, 10, 32.5, 17.5),
        (110, 65, 32, 14, 22, 55, 32.5),
        (55, 38, 16, 6, 7, 27.5, 19),
        # off-center
        (80, 50, 20, 10, 10, 20, 15),
        (100, 60, 25, 12, 14, 25, 40),
        (70, 45, 22, 8, 12, 15, 30),
        (120, 70, 30, 14, 20, 40, 20),
        (90, 55, 28, 10, 16, 60, 15),
        (65, 40, 18, 8, 8, 18, 12),
        (110, 65, 35, 16, 24, 30, 45),
        (85, 50, 24, 12, 15, 55, 35),
        (75, 42, 20, 10, 11, 22, 28),
        (95, 58, 26, 14, 17, 70, 18),
    ]
    for L, W, H, D, dp, cx, cy in rect_specs:
        _add({"base_type": "rect", "length": float(L), "width": float(W),
              "height": float(H), "diameter": float(D), "hole_depth": float(dp),
              "hole_cx": float(cx), "hole_cy": float(cy)})

    # ---- B. Plates (12) ----
    plate_specs: list[tuple] = [
        # (L, W, H, D, depth, cx, cy) — H <= 12mm
        (100, 70, 12, 8, 7, 50, 35),
        (120, 80, 10, 10, 6, 60, 40),
        (80, 50, 8, 6, 4, 40, 25),
        (140, 90, 12, 12, 8, 70, 45),
        (90, 60, 10, 8, 5, 45, 30),
        (110, 65, 8, 10, 4, 55, 32.5),
        # off-center plates
        (100, 70, 12, 8, 7, 20, 50),
        (120, 80, 10, 10, 5, 30, 20),
        (80, 50, 8, 6, 3, 60, 15),
        (140, 90, 12, 12, 9, 100, 30),
        (90, 60, 10, 8, 6, 25, 45),
        (110, 65, 8, 10, 4, 80, 20),
    ]
    for L, W, H, D, dp, cx, cy in plate_specs:
        _add({"base_type": "plate", "length": float(L), "width": float(W),
              "height": float(H), "diameter": float(D), "hole_depth": float(dp),
              "hole_cx": float(cx), "hole_cy": float(cy)})

    # ---- C. Triangular prisms (18) ----
    # Triangle: vertices (0,0)-(base,0)-(base/2,tri_h), extruded along Z by prism_height.
    # Centroid: (base/2, tri_h/3).
    tri_specs: list[tuple] = []
    # centered on centroid
    for base, tri_h, ph, D, dp in [
        (60, 40, 30, 8, 10),
        (80, 50, 40, 10, 15),
        (100, 60, 50, 12, 20),
        (70, 45, 35, 8, 12),
        (90, 55, 45, 10, 18),
        (50, 35, 25, 6, 8),
        (110, 70, 55, 14, 25),
        (65, 42, 32, 8, 14),
        (85, 52, 42, 10, 16),
    ]:
        cx_c = (0 + base + base / 2.0) / 3.0
        cy_c = (0 + 0 + tri_h) / 3.0
        tri_specs.append((base, tri_h, ph, D, dp, cx_c, cy_c))

    # off-center (shift from centroid but still inside triangle)
    for base, tri_h, ph, D, dp, cx_off, cy_off in [
        (80, 50, 40, 10, 12, 25, 10),
        (100, 60, 50, 12, 18, 60, 12),
        (70, 45, 35, 8, 10, 30, 8),
        (90, 55, 45, 10, 15, 50, 14),
        (110, 70, 55, 14, 22, 40, 18),
        (60, 40, 30, 6, 8, 25, 8),
        (120, 80, 60, 12, 20, 55, 20),
        (75, 48, 38, 8, 14, 40, 12),
        (95, 58, 48, 10, 18, 35, 15),
    ]:
        tri_specs.append((base, tri_h, ph, D, dp, cx_off, cy_off))

    for base, tri_h, ph, D, dp, cx, cy in tri_specs:
        _add({"base_type": "triangle", "base": float(base),
              "triangle_height": float(tri_h), "prism_height": float(ph),
              "diameter": float(D), "hole_depth": float(dp),
              "hole_cx": float(cx), "hole_cy": float(cy)})

    # ---- D. Cylinders (18) ----
    cyl_specs: list[tuple] = []
    # centered (cx=0, cy=0)
    for cyl_r, cyl_h, D, dp in [
        (20, 50, 10, 20),
        (25, 60, 12, 25),
        (15, 40, 8, 15),
        (30, 70, 14, 30),
        (18, 45, 10, 18),
        (22, 55, 12, 22),
        (35, 80, 16, 35),
        (12, 35, 6, 12),
        (28, 65, 14, 28),
    ]:
        cyl_specs.append((cyl_r, cyl_h, D, dp, 0.0, 0.0))

    # off-center (hole center offset from axis but still inside cylinder)
    for cyl_r, cyl_h, D, dp, cx_off, cy_off in [
        (25, 60, 10, 20, 8, 0),
        (30, 70, 12, 25, 0, 10),
        (20, 50, 8, 15, 6, 4),
        (35, 80, 14, 30, 10, 8),
        (22, 55, 10, 18, -5, 6),
        (28, 65, 12, 22, 8, -6),
        (18, 45, 6, 12, 4, 3),
        (32, 75, 14, 28, -8, 10),
        (24, 58, 10, 20, 7, -5),
    ]:
        cyl_specs.append((cyl_r, cyl_h, D, dp, cx_off, cy_off))

    for cyl_r, cyl_h, D, dp, cx, cy in cyl_specs:
        _add({"base_type": "cylinder", "cyl_radius": float(cyl_r),
              "cyl_height": float(cyl_h), "diameter": float(D),
              "hole_depth": float(dp), "hole_cx": float(cx), "hole_cy": float(cy)})

    return items[:count]


FEATURE_FAMILIES["blind_hole"] = FeatureFamily(
    family_id="blind_hole",
    folder="blind_holes",
    filename_builder=blind_hole_filename,
    operations_builder=blind_hole_operations,
    cad_json_builder=lambda dims, label: blind_hole_cad_json(dims, source_label=label),
    prompt_builder=blind_hole_prompts,
    dimension_builder=blind_hole_dimensions,
    reference_dims=REFERENCE_BLIND_HOLE,
)

