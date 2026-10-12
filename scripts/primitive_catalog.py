"""Shared primitive family definitions for generation and prompt datasets."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


def format_mm(value: float) -> str:
    if math.isclose(value, round(value)):
        return str(int(round(value)))
    text = f"{value:.1f}".rstrip("0").rstrip(".")
    return text


def linspace(start: float, end: float, count: int) -> list[float]:
    if count <= 1:
        return [start]
    step = (end - start) / (count - 1)
    return [round(start + step * index, 1) for index in range(count)]


def _rect_sketch_entities(length: float, width: float) -> list[dict[str, Any]]:
    return [
        {"id": "e_001", "type": "Line", "start": [0.0, 0.0], "end": [length, 0.0]},
        {"id": "e_002", "type": "Line", "start": [length, 0.0], "end": [length, width]},
        {"id": "e_003", "type": "Line", "start": [length, width], "end": [0.0, width]},
        {"id": "e_004", "type": "Line", "start": [0.0, width], "end": [0.0, 0.0]},
    ]


def _sketch_pad_operations(entities: list[dict[str, Any]], pad_length: float) -> list[dict[str, Any]]:
    return [
        {"id": "op_001", "type": "Sketch", "entities": entities, "constraints": [], "plane": "XY"},
        {"id": "op_002", "type": "Pad", "profile": "op_001", "length": pad_length},
    ]


@dataclass(frozen=True)
class PrimitiveFamily:
    shape_type: str
    folder: str
    filename_prefix: str
    supports_compiler_json: bool
    dimension_builder: Callable[[int], list[dict[str, float]]]
    filename_builder: Callable[[int, dict[str, float]], str]
    freecad_builder: Callable[[Any, dict[str, float]], None]
    prompt_templates_builder: Callable[[dict[str, float]], list[str]]
    operations_builder: Callable[[dict[str, float]], list[dict[str, Any]] | None]
    parser: re.Pattern[str]


def _cube_dimensions(count: int) -> list[dict[str, float]]:
    return [{"side": side} for side in linspace(10, 50, count)]


def _cylinder_dimensions(count: int) -> list[dict[str, float]]:
    radii = linspace(5, 20, count)
    heights = linspace(10, 100, count)
    return [{"radius": r, "height": h} for r, h in zip(radii, heights, strict=True)]


def _sphere_dimensions(count: int) -> list[dict[str, float]]:
    return [{"radius": radius} for radius in linspace(5, 50, count)]


def _rectangular_prism_dimensions(count: int) -> list[dict[str, float]]:
    seed_specs = [
        (40, 20, 10),
        (80, 30, 15),
        (120, 50, 25),
        (60, 35, 12),
        (90, 45, 18),
        (100, 40, 20),
        (75, 50, 22),
        (110, 55, 30),
        (95, 35, 14),
        (130, 60, 28),
        (55, 25, 8),
        (70, 42, 16),
        (85, 38, 19),
        (105, 48, 24),
        (115, 52, 26),
        (65, 28, 11),
        (125, 58, 27),
        (50, 22, 9),
        (140, 65, 32),
        (72, 33, 13),
    ]
    specs = seed_specs[:count]
    while len(specs) < count:
        specs.append(seed_specs[len(specs) % len(seed_specs)])
    dimensions: list[dict[str, float]] = []
    for length, width, height in specs:
        if math.isclose(length, width) and math.isclose(width, height):
            width += 5
        dimensions.append({"length": float(length), "width": float(width), "height": float(height)})
    return dimensions


def _thin_plate_dimensions(count: int) -> list[dict[str, float]]:
    seed_specs = [
        (100, 80, 3),
        (60, 40, 2),
        (150, 100, 5),
        (120, 90, 4),
        (80, 60, 2.5),
        (140, 110, 5),
        (90, 70, 3),
        (110, 85, 4),
        (70, 50, 2),
        (130, 95, 4.5),
        (160, 120, 6),
        (95, 75, 3),
        (105, 80, 3.5),
        (85, 65, 2.5),
        (125, 100, 5),
        (75, 55, 2),
        (145, 105, 4.5),
        (65, 45, 2),
        (155, 115, 5.5),
        (115, 88, 4),
    ]
    specs = seed_specs[:count]
    while len(specs) < count:
        specs.append(seed_specs[len(specs) % len(seed_specs)])
    return [
        {"length": float(length), "width": float(width), "thickness": float(thickness)}
        for length, width, thickness in specs
    ]


def _triangular_prism_dimensions(count: int) -> list[dict[str, float]]:
    bases = linspace(30, 100, count)
    tri_heights = linspace(20, 80, count)
    prism_heights = linspace(15, 60, count)
    return [
        {"base": base, "triangle_height": tri_h, "prism_height": prism_h}
        for base, tri_h, prism_h in zip(bases, tri_heights, prism_heights, strict=True)
    ]


def _build_box(freecad_app: Any, dims: dict[str, float], *, length_key: str, width_key: str, height_key: str, label: str) -> None:
    doc = freecad_app.ActiveDocument
    box = doc.addObject("Part::Box", label)
    box.Length = dims[length_key]
    box.Width = dims[width_key]
    box.Height = dims[height_key]


def _build_cube(freecad_app: Any, dims: dict[str, float]) -> None:
    _build_box(freecad_app, dims, length_key="side", width_key="side", height_key="side", label="Cube")


def _build_cylinder(freecad_app: Any, dims: dict[str, float]) -> None:
    doc = freecad_app.ActiveDocument
    cylinder = doc.addObject("Part::Cylinder", "Cylinder")
    cylinder.Radius = dims["radius"]
    cylinder.Height = dims["height"]


def _build_sphere(freecad_app: Any, dims: dict[str, float]) -> None:
    doc = freecad_app.ActiveDocument
    sphere = doc.addObject("Part::Sphere", "Sphere")
    sphere.Radius = dims["radius"]


def _build_rectangular_prism(freecad_app: Any, dims: dict[str, float]) -> None:
    _build_box(freecad_app, dims, length_key="length", width_key="width", height_key="height", label="RectangularPrism")


def _build_thin_plate(freecad_app: Any, dims: dict[str, float]) -> None:
    _build_box(
        freecad_app,
        {"length": dims["length"], "width": dims["width"], "height": dims["thickness"]},
        length_key="length",
        width_key="width",
        height_key="height",
        label="ThinPlate",
    )


def _build_triangular_prism(freecad_app: Any, dims: dict[str, float]) -> None:
    import Part

    base = dims["base"]
    tri_h = dims["triangle_height"]
    prism_h = dims["prism_height"]
    points = [
        freecad_app.Vector(0, 0, 0),
        freecad_app.Vector(base, 0, 0),
        freecad_app.Vector(base / 2.0, tri_h, 0),
        freecad_app.Vector(0, 0, 0),
    ]
    wire = Part.makePolygon(points)
    face = Part.Face(wire)
    solid = face.extrude(freecad_app.Vector(0, 0, prism_h))
    doc = freecad_app.ActiveDocument
    feature = doc.addObject("Part::Feature", "TriangularPrism")
    feature.Shape = solid


def _cube_prompts(dims: dict[str, float]) -> list[str]:
    side = format_mm(dims["side"])
    return [
        f"Create a cube with side length {side} mm.",
        f"Make a {side} by {side} by {side} millimeter cube.",
        f"Generate a solid cube measuring {side} × {side} × {side} mm.",
        f"Model a cubic solid with {side} mm edges.",
        f"Build a {side} mm cube.",
    ]


def _cylinder_prompts(dims: dict[str, float]) -> list[str]:
    radius = format_mm(dims["radius"])
    height = format_mm(dims["height"])
    return [
        f"Create a cylinder with radius {radius} mm and height {height} mm.",
        f"Make a cylinder {height} mm tall with a {radius} mm radius.",
        f"Generate a cylindrical solid: radius {radius} mm, height {height} mm.",
        f"Model a right circular cylinder {radius} mm in radius and {height} mm high.",
        f"Build a {height} by {radius} millimeter cylinder.",
    ]


def _sphere_prompts(dims: dict[str, float]) -> list[str]:
    radius = format_mm(dims["radius"])
    return [
        f"Create a sphere with radius {radius} mm.",
        f"Make a spherical solid {radius} millimeters in radius.",
        f"Generate a ball with a {radius} mm radius.",
        f"Model a sphere of radius {radius} mm.",
        f"Build a {radius} mm radius sphere.",
    ]


def _rectangular_prism_prompts(dims: dict[str, float]) -> list[str]:
    length = format_mm(dims["length"])
    width = format_mm(dims["width"])
    height = format_mm(dims["height"])
    return [
        f"Create a rectangular prism {length} mm long, {width} mm wide and {height} mm high.",
        f"Make a {length} by {width} by {height} millimeter block.",
        f"Generate a solid cuboid with dimensions {length} × {width} × {height} mm.",
        f"Model a rectangular block of size {length} × {width} × {height} mm.",
        f"Build a box-shaped solid measuring {length}, {width} and {height} millimeters.",
    ]


def _thin_plate_prompts(dims: dict[str, float]) -> list[str]:
    length = format_mm(dims["length"])
    width = format_mm(dims["width"])
    thickness = format_mm(dims["thickness"])
    return [
        f"Create a thin rectangular plate measuring {length} × {width} mm with a thickness of {thickness} mm.",
        f"Make a flat plate {length} by {width} by {thickness} millimeters.",
        f"Generate a thin base plate with dimensions {length} × {width} × {thickness} mm.",
        f"Model a rectangular plate that is {thickness} millimeters thick.",
        f"Build a flat rectangular plate measuring {length} × {width} × {thickness} mm.",
    ]


def _triangular_prism_prompts(dims: dict[str, float]) -> list[str]:
    base = format_mm(dims["base"])
    tri_h = format_mm(dims["triangle_height"])
    prism_h = format_mm(dims["prism_height"])
    return [
        f"Create a triangular prism {prism_h} mm high with a {base} mm base.",
        f"Make a triangular prism extruded to {prism_h} millimeters.",
        f"Generate a solid triangular prism with a {base} by {tri_h} mm triangle base.",
        f"Model a prism with a triangular profile of {base} × {tri_h} mm and height {prism_h} mm.",
        f"Build a triangular prism using a {base} mm base and {prism_h} mm extrusion height.",
    ]


def _cube_operations(dims: dict[str, float]) -> list[dict[str, Any]]:
    side = dims["side"]
    return _sketch_pad_operations(_rect_sketch_entities(side, side), side)


def _cylinder_operations(dims: dict[str, float]) -> list[dict[str, Any]]:
    return _sketch_pad_operations(
        [{"id": "e_001", "type": "Circle", "center": [0.0, 0.0], "radius": dims["radius"]}],
        dims["height"],
    )


def _rectangular_prism_operations(dims: dict[str, float]) -> list[dict[str, Any]]:
    return _sketch_pad_operations(
        _rect_sketch_entities(dims["length"], dims["width"]),
        dims["height"],
    )


def _thin_plate_operations(dims: dict[str, float]) -> list[dict[str, Any]]:
    return _sketch_pad_operations(
        _rect_sketch_entities(dims["length"], dims["width"]),
        dims["thickness"],
    )


def _triangular_prism_operations(dims: dict[str, float]) -> list[dict[str, Any]]:
    base = dims["base"]
    tri_h = dims["triangle_height"]
    entities = [
        {"id": "e_001", "type": "Line", "start": [0.0, 0.0], "end": [base, 0.0]},
        {"id": "e_002", "type": "Line", "start": [base, 0.0], "end": [base / 2.0, tri_h]},
        {"id": "e_003", "type": "Line", "start": [base / 2.0, tri_h], "end": [0.0, 0.0]},
    ]
    return _sketch_pad_operations(entities, dims["prism_height"])


PRIMITIVE_FAMILIES: dict[str, PrimitiveFamily] = {
    "cube": PrimitiveFamily(
        shape_type="cube",
        folder="cubes",
        filename_prefix="cube",
        supports_compiler_json=True,
        dimension_builder=_cube_dimensions,
        filename_builder=lambda index, dims: (
            f"cube_{index:02d}_side_{format_mm(dims['side'])}mm.FCStd"
        ),
        freecad_builder=_build_cube,
        prompt_templates_builder=_cube_prompts,
        operations_builder=_cube_operations,
        parser=re.compile(r"cube_(?P<index>\d+)_side_(?P<side>[\d.]+)mm", re.I),
    ),
    "cylinder": PrimitiveFamily(
        shape_type="cylinder",
        folder="cylinders",
        filename_prefix="cylinder",
        supports_compiler_json=True,
        dimension_builder=_cylinder_dimensions,
        filename_builder=lambda index, dims: (
            f"cylinder_{index:02d}_r{format_mm(dims['radius'])}_h{format_mm(dims['height'])}mm.FCStd"
        ),
        freecad_builder=_build_cylinder,
        prompt_templates_builder=_cylinder_prompts,
        operations_builder=_cylinder_operations,
        parser=re.compile(r"cylinder_(?P<index>\d+)_r(?P<radius>[\d.]+)_h(?P<height>[\d.]+)mm", re.I),
    ),
    "sphere": PrimitiveFamily(
        shape_type="sphere",
        folder="spheres",
        filename_prefix="sphere",
        supports_compiler_json=False,
        dimension_builder=_sphere_dimensions,
        filename_builder=lambda index, dims: (
            f"sphere_{index:02d}_r{format_mm(dims['radius'])}mm.FCStd"
        ),
        freecad_builder=_build_sphere,
        prompt_templates_builder=_sphere_prompts,
        operations_builder=lambda _dims: None,
        parser=re.compile(r"sphere_(?P<index>\d+)_r(?P<radius>[\d.]+)mm", re.I),
    ),
    "rectangular_prism": PrimitiveFamily(
        shape_type="rectangular_prism",
        folder="rectangular_prisms",
        filename_prefix="rectangular_prism",
        supports_compiler_json=True,
        dimension_builder=_rectangular_prism_dimensions,
        filename_builder=lambda index, dims: (
            f"rectangular_prism_{index:02d}_l{format_mm(dims['length'])}_w{format_mm(dims['width'])}_h{format_mm(dims['height'])}mm.FCStd"
        ),
        freecad_builder=_build_rectangular_prism,
        prompt_templates_builder=_rectangular_prism_prompts,
        operations_builder=_rectangular_prism_operations,
        parser=re.compile(
            r"rectangular_prism_(?P<index>\d+)_l(?P<length>[\d.]+)_w(?P<width>[\d.]+)_h(?P<height>[\d.]+)mm",
            re.I,
        ),
    ),
    "thin_plate": PrimitiveFamily(
        shape_type="thin_plate",
        folder="thin_plates",
        filename_prefix="thin_plate",
        supports_compiler_json=True,
        dimension_builder=_thin_plate_dimensions,
        filename_builder=lambda index, dims: (
            f"thin_plate_{index:02d}_l{format_mm(dims['length'])}_w{format_mm(dims['width'])}_t{format_mm(dims['thickness'])}mm.FCStd"
        ),
        freecad_builder=_build_thin_plate,
        prompt_templates_builder=_thin_plate_prompts,
        operations_builder=_thin_plate_operations,
        parser=re.compile(
            r"thin_plate_(?P<index>\d+)_l(?P<length>[\d.]+)_w(?P<width>[\d.]+)_t(?P<thickness>[\d.]+)mm",
            re.I,
        ),
    ),
    "triangular_prism": PrimitiveFamily(
        shape_type="triangular_prism",
        folder="triangular_prisms",
        filename_prefix="triangular_prism",
        supports_compiler_json=True,
        dimension_builder=_triangular_prism_dimensions,
        filename_builder=lambda index, dims: (
            "triangular_prism_{index:02d}_base{base}_tri{triangle_height}_prism{prism_height}mm.FCStd".format(
                index=index,
                base=format_mm(dims["base"]),
                triangle_height=format_mm(dims["triangle_height"]),
                prism_height=format_mm(dims["prism_height"]),
            )
        ),
        freecad_builder=_build_triangular_prism,
        prompt_templates_builder=_triangular_prism_prompts,
        operations_builder=_triangular_prism_operations,
        parser=re.compile(
            r"triangular_prism_(?P<index>\d+)_base(?P<base>[\d.]+)_tri(?P<triangle_height>[\d.]+)_prism(?P<prism_height>[\d.]+)mm",
            re.I,
        ),
    ),
}


DEFAULT_FAMILY_ORDER = [
    "cube",
    "cylinder",
    "sphere",
    "rectangular_prism",
    "thin_plate",
    "triangular_prism",
]


def parse_dimensions_from_match(family: PrimitiveFamily, match: re.Match[str]) -> dict[str, float]:
    if family.shape_type == "cube":
        return {"side_mm": float(match.group("side"))}
    if family.shape_type == "cylinder":
        return {"radius_mm": float(match.group("radius")), "height_mm": float(match.group("height"))}
    if family.shape_type == "sphere":
        return {"radius_mm": float(match.group("radius"))}
    if family.shape_type == "rectangular_prism":
        return {
            "length_mm": float(match.group("length")),
            "width_mm": float(match.group("width")),
            "height_mm": float(match.group("height")),
        }
    if family.shape_type == "thin_plate":
        return {
            "length_mm": float(match.group("length")),
            "width_mm": float(match.group("width")),
            "thickness_mm": float(match.group("thickness")),
        }
    if family.shape_type == "triangular_prism":
        return {
            "base_mm": float(match.group("base")),
            "triangle_height_mm": float(match.group("triangle_height")),
            "prism_height_mm": float(match.group("prism_height")),
        }
    raise ValueError(f"Unsupported family: {family.shape_type}")


def save_freecad_shape(output_path: Path, *, build_callback: Callable[[Any], None], document_label: str) -> None:
    import FreeCAD as App

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = App.newDocument(document_label)
    build_callback(App)
    doc.recompute()
    doc.saveAs(str(output_path.resolve()))
    print(f"Saved {output_path}")
    App.closeDocument(doc.Name)


def generate_family_shapes(output_dir: Path, family: PrimitiveFamily, count: int) -> list[Path]:
    saved: list[Path] = []
    for index, dims in enumerate(family.dimension_builder(count), start=1):
        filename = family.filename_builder(index, dims)
        output_path = output_dir / family.folder / filename
        save_freecad_shape(
            output_path,
            build_callback=lambda app, dims=dims, builder=family.freecad_builder: builder(app, dims),
            document_label=f"{family.shape_type}_{index:02d}",
        )
        saved.append(output_path)
    return saved


def parse_shape_file(
    path: Path,
    *,
    project_root: Path,
) -> dict[str, Any] | None:
    stem = path.stem
    rel_path = path.relative_to(project_root).as_posix()

    for family in PRIMITIVE_FAMILIES.values():
        match = family.parser.search(stem)
        if not match:
            continue
        dimensions = parse_dimensions_from_match(family, match)
        internal_dims = {key.removesuffix("_mm"): value for key, value in dimensions.items()}
        operations = family.operations_builder(internal_dims) if family.supports_compiler_json else None
        return {
            "shape_id": stem,
            "shape_type": family.shape_type,
            "index": int(match.group("index")),
            "dimensions": dimensions,
            "fcstd_path": rel_path,
            "filename": path.name,
            "prompts": family.prompt_templates_builder(internal_dims),
            "operations": operations,
        }
    return None
