"""Inspect a compiled feature .FCStd inside FreeCAD.

Usage (via FreeCADCmd / run_in_freecad):
    feature_geometry_check.py <fcstd> <expected.json> <report.json>
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 3:
        print("Usage: feature_geometry_check.py <fcstd> <expected.json> <report.json>", file=sys.stderr)
        return 2

    fcstd_path = Path(args[0])
    expected = json.loads(Path(args[1]).read_text(encoding="utf-8"))
    report_path = Path(args[2])

    try:
        report = inspect_model(fcstd_path, expected)
    except Exception as exc:  # noqa: BLE001
        report = {"passed": False, "error": str(exc), "traceback": traceback.format_exc(), "checks": []}

    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": report.get("passed"), "error": report.get("error")}))
    return 0 if report.get("passed") else 1


def inspect_model(fcstd_path: Path, expected: dict) -> dict:
    import FreeCAD as App

    doc = App.openDocument(str(fcstd_path))
    try:
        body = _find_body(doc)
        if body is None or not getattr(body, "Shape", None):
            return {"passed": False, "error": "No PartDesign Body with a Shape.", "checks": []}

        shape = body.Shape
        bbox = shape.BoundBox
        hole = _find_hole(doc)

        expected_bbox = expected["bbox"]
        height = float(expected["height"])
        bbox_tol = float(expected["bbox_tolerance_mm"])
        vol_tol = float(expected["volume_relative_tolerance"])
        radius_tol = float(expected["radius_tolerance_mm"])
        expected_diameter = float(expected["diameter"])
        expected_radius = expected_diameter / 2.0
        is_blind = bool(expected.get("is_blind", False))
        hole_depth = float(expected.get("hole_depth", 0.0))

        hole_centers = expected.get("hole_centers_xy")
        if not hole_centers:
            hole_centers = [expected["center_xy"]]

        checks: list[dict] = []
        checks.append(_check("valid_solid", bool(shape.isValid() and shape.Solids), {"solids": len(shape.Solids)}))
        checks.append(_check("no_document_errors", not _document_errors(doc), {"errors": _document_errors(doc)}))

        checks.extend([
            _check("bbox_xmin", abs(bbox.XMin - expected_bbox["xmin"]) <= bbox_tol, {"value": bbox.XMin}),
            _check("bbox_ymin", abs(bbox.YMin - expected_bbox["ymin"]) <= bbox_tol, {"value": bbox.YMin}),
            _check("bbox_zmin", abs(bbox.ZMin - expected_bbox["zmin"]) <= bbox_tol, {"value": bbox.ZMin}),
            _check("bbox_xmax", abs(bbox.XMax - expected_bbox["xmax"]) <= bbox_tol, {"value": bbox.XMax}),
            _check("bbox_ymax", abs(bbox.YMax - expected_bbox["ymax"]) <= bbox_tol, {"value": bbox.YMax}),
            _check("bbox_zmax", abs(bbox.ZMax - expected_bbox["zmax"]) <= bbox_tol, {"value": bbox.ZMax}),
        ])

        checks.append(_check(
            "volume",
            abs(shape.Volume - expected["volume"]) <= max(1.0, abs(expected["volume"]) * vol_tol),
            {"value": shape.Volume, "expected": expected["volume"]},
        ))

        checks.append(_check("hole_object_present", hole is not None, {}))
        checks.append(_check(
            "hole_diameter_property",
            hole is not None and abs(float(hole.Diameter) - expected_diameter) <= radius_tol,
            {"value": None if hole is None else float(hole.Diameter)},
        ))

        if is_blind:
            checks.append(_check(
                "hole_depth_type_dimension",
                hole is not None and _is_dimension_depth(hole),
                {"value": None if hole is None else _depth_type_value(hole)},
            ))
            if hole is not None:
                actual_depth = float(getattr(hole, "Depth", 0))
                checks.append(_check(
                    "hole_depth_value",
                    abs(actual_depth - hole_depth) <= radius_tol,
                    {"actual": actual_depth, "expected": hole_depth},
                ))
        else:
            checks.append(_check(
                "hole_depth_type_through_all",
                hole is not None and _is_through_all(hole),
                {"value": None if hole is None else _depth_type_value(hole)},
            ))

        cyl_radii = _cylinder_radii(shape)
        checks.append(_check(
            "cylindrical_face_radius",
            any(abs(radius - expected_radius) <= radius_tol for radius in cyl_radii),
            {"radii": cyl_radii, "expected_radius": expected_radius},
        ))

        z_mid = height / 2.0
        for idx, (cx, cy) in enumerate(hole_centers, start=1):
            if is_blind:
                # For blind holes: mid-depth of hole should be empty.
                z_check = height - hole_depth / 2.0
                checks.append(_check(
                    f"hole_axis_empty_{idx}",
                    not _is_inside(shape, float(cx), float(cy), z_check),
                    {"center": [cx, cy, z_check]},
                ))
                # Material must exist below the hole (at z = height - hole_depth - 1).
                z_below = height - hole_depth - 1.0
                if z_below > 0:
                    checks.append(_check(
                        f"material_below_hole_{idx}",
                        _is_inside(shape, float(cx), float(cy), z_below),
                        {"center": [cx, cy, z_below]},
                    ))
                # Hole must NOT pass through: material at z=0.5 along hole axis.
                checks.append(_check(
                    f"blind_not_through_{idx}",
                    _is_inside(shape, float(cx), float(cy), 0.5),
                    {"center": [cx, cy, 0.5], "reason": "material should exist at bottom"},
                ))
            else:
                checks.append(_check(
                    f"hole_axis_empty_{idx}",
                    not _is_inside(shape, float(cx), float(cy), z_mid),
                    {"center": [cx, cy, z_mid]},
                ))
                checks.append(_check(
                    f"through_below_empty_{idx}",
                    not _is_inside(shape, float(cx), float(cy), -1.0),
                    {"center": [cx, cy, -1.0]},
                ))
                checks.append(_check(
                    f"through_above_empty_{idx}",
                    not _is_inside(shape, float(cx), float(cy), height + 1.0),
                    {"center": [cx, cy, height + 1.0]},
                ))

        # Global sanity: a material point should remain inside the solid.
        # For rectangular bases, (2,2,z_mid) works.
        # For cylinders centered at origin, use a small offset from center.
        # For triangles, use (base/4, small_y, z_mid).
        # We just check that the solid has nonzero volume (already done above).

        return {
            "passed": all(item["passed"] for item in checks),
            "checks": checks,
            "bbox": {"xmin": bbox.XMin, "ymin": bbox.YMin, "zmin": bbox.ZMin,
                     "xmax": bbox.XMax, "ymax": bbox.YMax, "zmax": bbox.ZMax},
            "volume": shape.Volume,
            "cylinder_radii": cyl_radii,
        }
    finally:
        App.closeDocument(doc.Name)


def _find_body(doc):
    for obj in doc.Objects:
        if obj.TypeId == "PartDesign::Body":
            return obj
    return None


def _find_hole(doc):
    for obj in doc.Objects:
        if obj.TypeId == "PartDesign::Hole":
            return obj
    return None


def _depth_type_value(hole) -> str:
    return str(getattr(hole, "DepthType", ""))


def _is_through_all(hole) -> bool:
    value = getattr(hole, "DepthType", None)
    return value in (1, "1", "ThroughAll") or str(value) == "ThroughAll"


def _is_dimension_depth(hole) -> bool:
    value = getattr(hole, "DepthType", None)
    return value in (0, "0", "Dimension") or str(value) == "Dimension"


def _document_errors(doc) -> list[str]:
    return [obj.Name for obj in doc.Objects if hasattr(obj, "State") and "Error" in obj.State]


def _cylinder_radii(shape) -> list[float]:
    radii: list[float] = []
    for face in shape.Faces:
        surface = face.Surface
        type_id = getattr(surface, "TypeId", "")
        if "Cylinder" in str(type_id) or surface.__class__.__name__ == "Cylinder":
            if hasattr(surface, "Radius"):
                radii.append(float(surface.Radius))
    return radii


def _is_inside(shape, x: float, y: float, z: float) -> bool:
    import FreeCAD as App
    return bool(shape.isInside(App.Vector(x, y, z), 1e-4, False))


def _check(name: str, passed: bool, details: dict) -> dict:
    return {"name": name, "passed": bool(passed), "details": details}


if __name__ == "__main__":
    raise SystemExit(main())
