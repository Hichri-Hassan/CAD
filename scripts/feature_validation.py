"""Validate authored feature CAD JSON against compiled FreeCAD geometry and the parser."""

from __future__ import annotations

import json
import math
import sys
import tempfile
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from compiler.freecad_launcher import find_freecadcmd, run_in_freecad
from compiler.loader import load_cad_json
from feature_catalog import (
    circle_radius_from_diameter,
    expected_bbox,
    expected_volume,
    hole_centers,
    hole_count,
    blind_hole_expected_bbox,
    blind_hole_expected_volume,
    blind_hole_pad_height,
    _TOP_FACE,
)
from parser.document_parser import parse_fcstd


BBOX_TOLERANCE_MM = 0.05
VOLUME_RELATIVE_TOLERANCE = 0.02
RADIUS_TOLERANCE_MM = 0.05
COORD_TOLERANCE_MM = 0.05


def _check(name: str, passed: bool, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "details": details or {}}


def _close(a: Any, b: Any, tol: float = COORD_TOLERANCE_MM) -> bool:
    try:
        return abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return False


def _circles_from_entities(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    circles: list[dict[str, Any]] = []
    for ent in entities:
        if ent.get("type") != "Circle":
            continue
        center = ent.get("center") or []
        if not isinstance(center, list) or len(center) != 2:
            continue
        circles.append({"center": [float(center[0]), float(center[1])], "radius": float(ent["radius"])})
    return circles


def _detect_family(dims: dict[str, Any]) -> str:
    if "base_type" in dims:
        return "blind_hole"
    return "through_hole"


def assert_authored_consistency(dims: dict[str, Any], cad_json: dict[str, Any]) -> list[dict[str, Any]]:
    family = _detect_family(dims)
    checks: list[dict[str, Any]] = []
    operations = cad_json["operations"]
    types = [op["type"] for op in operations]
    checks.append(_check("operation_sequence", types == ["Sketch", "Pad", "Sketch", "Hole"], {"types": types}))

    pad = operations[1]
    hole = operations[3]
    hole_sketch = operations[2]

    expected_radius = circle_radius_from_diameter(float(dims["diameter"]))
    circles = _circles_from_entities(hole_sketch.get("entities", []))

    if family == "through_hole":
        checks.append(_check("pad_height", _close(pad["length"], dims["height"]), {"length": pad["length"]}))
        checks.append(_check("hole_depth_through_all", hole.get("depth") == "through_all", {"depth": hole.get("depth")}))
        expected_face = "Face6"
        exp_centers = sorted(hole_centers(dims))
        exp_count = hole_count(dims)
    else:
        pad_h = blind_hole_pad_height(dims)
        checks.append(_check("pad_height", _close(pad["length"], pad_h), {"length": pad["length"], "expected": pad_h}))
        checks.append(_check("hole_depth_numeric", isinstance(hole.get("depth"), (int, float)), {"depth": hole.get("depth")}))
        checks.append(_check("hole_depth_value", _close(hole.get("depth"), dims["hole_depth"]), {"depth": hole.get("depth"), "expected": dims["hole_depth"]}))
        checks.append(_check("hole_depth_less_than_pad",
                             float(hole.get("depth", 0)) < pad_h,
                             {"depth": hole.get("depth"), "pad_height": pad_h}))
        expected_face = _TOP_FACE[dims["base_type"]]
        exp_centers = [(float(dims["hole_cx"]), float(dims["hole_cy"]))]
        exp_count = 1

    checks.append(_check("hole_diameter", _close(hole["diameter"], dims["diameter"]), {"diameter": hole.get("diameter")}))
    checks.append(
        _check(
            "hole_sketch_support_face",
            hole_sketch.get("support") == {"type": "face", "reference": "op_002", "selector": expected_face},
            {"support": hole_sketch.get("support"), "expected_face": expected_face},
        )
    )
    checks.append(_check("hole_circle_count", len(circles) == exp_count, {"expected": exp_count, "found": len(circles)}))

    for ex_cx, ex_cy in exp_centers:
        match = any(
            _close(c["center"][0], ex_cx) and _close(c["center"][1], ex_cy) and _close(c["radius"], expected_radius)
            for c in circles
        )
        checks.append(
            _check("circle_match", match,
                   {"expected_center": [ex_cx, ex_cy], "expected_radius": expected_radius,
                    "found_centers": [c["center"] for c in circles]})
        )

    return checks


def compare_parser_to_canonical(canonical: dict[str, Any], parsed: dict[str, Any]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    can_ops = canonical["operations"]
    par_ops = parsed.get("operations", [])

    checks.append(_check("parser_operation_count", len(can_ops) == len(par_ops),
                         {"canonical": len(can_ops), "parsed": len(par_ops)}))

    for can_op, par_op in zip(can_ops, par_ops, strict=True):
        op_id = can_op["id"]
        checks.append(_check(f"parser_{op_id}_type", can_op["type"] == par_op.get("type"),
                             {"canonical": can_op["type"], "parsed": par_op.get("type")}))

        if can_op["type"] == "Pad":
            checks.append(_check(f"parser_{op_id}_length", _close(can_op["length"], par_op.get("length")),
                                 {"canonical": can_op["length"], "parsed": par_op.get("length")}))
        elif can_op["type"] == "Hole":
            checks.append(_check(f"parser_{op_id}_diameter", _close(can_op["diameter"], par_op.get("diameter")),
                                 {"canonical": can_op["diameter"], "parsed": par_op.get("diameter")}))
            can_depth = can_op["depth"]
            par_depth = par_op.get("depth")
            if can_depth == "through_all":
                checks.append(_check(f"parser_{op_id}_depth", par_depth == "through_all",
                                     {"canonical": can_depth, "parsed": par_depth}))
            else:
                checks.append(_check(f"parser_{op_id}_depth", _close(can_depth, par_depth),
                                     {"canonical": can_depth, "parsed": par_depth}))
        elif can_op["type"] == "Sketch" and can_op["id"] == "op_003":
            can_circles = _circles_from_entities(can_op.get("entities", []))
            par_circles = _circles_from_entities(par_op.get("entities") or [])
            checks.append(_check("parser_op_003_circle_count", len(can_circles) == len(par_circles),
                                 {"canonical": len(can_circles), "parsed": len(par_circles)}))
            for cc in can_circles:
                cx, cy = cc["center"]
                r = cc["radius"]
                m = any(_close(pc["center"][0], cx) and _close(pc["center"][1], cy) and _close(pc["radius"], r)
                        for pc in par_circles)
                checks.append(_check("parser_circle_match", m,
                                     {"expected_center": [cx, cy], "expected_radius": r,
                                      "found": [pc["center"] for pc in par_circles]}))

    return checks


def run_geometry_checks(*, fcstd_path: Path, dims: dict[str, Any], project_root: Path) -> dict[str, Any]:
    family = _detect_family(dims)

    if family == "through_hole":
        exp_bbox = expected_bbox(dims)
        exp_vol = expected_volume(dims)
        centers_xy = [[float(x), float(y)] for x, y in hole_centers(dims)]
        center_xy = centers_xy[0]
        height = float(dims["height"])
        is_blind = False
        hole_depth_val = 0.0
    else:
        exp_bbox = blind_hole_expected_bbox(dims)
        exp_vol = blind_hole_expected_volume(dims)
        centers_xy = [[float(dims["hole_cx"]), float(dims["hole_cy"])]]
        center_xy = centers_xy[0]
        height = blind_hole_pad_height(dims)
        is_blind = True
        hole_depth_val = float(dims["hole_depth"])

    expected = {
        "bbox": exp_bbox,
        "volume": exp_vol,
        "diameter": float(dims["diameter"]),
        "hole_centers_xy": centers_xy,
        "center_xy": center_xy,
        "height": height,
        "bbox_tolerance_mm": BBOX_TOLERANCE_MM,
        "volume_relative_tolerance": VOLUME_RELATIVE_TOLERANCE,
        "radius_tolerance_mm": RADIUS_TOLERANCE_MM,
        "is_blind": is_blind,
        "hole_depth": hole_depth_val,
    }

    with tempfile.TemporaryDirectory() as tmp:
        expected_path = Path(tmp) / "expected.json"
        report_path = Path(tmp) / "geometry_report.json"
        expected_path.write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")
        script_path = SCRIPT_DIR / "feature_geometry_check.py"
        result = run_in_freecad(
            script_path,
            [str(fcstd_path.resolve()), str(expected_path.resolve()), str(report_path.resolve())],
            project_root=project_root,
        )
        payload: dict[str, Any] = {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}
        if report_path.exists():
            payload.update(json.loads(report_path.read_text(encoding="utf-8")))
        elif result.returncode != 0:
            payload["passed"] = False
            payload["error"] = result.stderr or result.stdout or "Geometry check failed"
        return payload


def validate_feature_model(
    *,
    cad_json: dict[str, Any],
    json_path: Path,
    fcstd_path: Path | None,
    dims: dict[str, Any],
    project_root: Path,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    loader_ok = True
    loader_error: str | None = None
    try:
        load_cad_json(json_path)
    except ValueError as exc:
        loader_ok = False
        loader_error = str(exc)
    checks.append(_check("json_schema", loader_ok, {"error": loader_error}))
    checks.extend(assert_authored_consistency(dims, cad_json))

    parser_result: dict[str, Any] | None = None
    geometry_result: dict[str, Any] | None = None

    if fcstd_path is not None and fcstd_path.exists():
        parsed = parse_fcstd(fcstd_path)
        parser_result = {"status": parsed.status.value, "warnings": parsed.warnings,
                         "unsupported_features": parsed.unsupported_features}
        checks.append(_check("parser_status_valid", parsed.status.value == "valid", parser_result))
        checks.extend(compare_parser_to_canonical(cad_json, parsed.cad_json))

        if find_freecadcmd() is None:
            checks.append(_check("freecad_available", False, {"error": "FreeCADCmd not found"}))
        else:
            geometry_result = run_geometry_checks(fcstd_path=fcstd_path, dims=dims, project_root=project_root)
            checks.append(
                _check("compiler_geometry", bool(geometry_result.get("passed")),
                       {"error": geometry_result.get("error"), "details": geometry_result.get("checks")})
            )
    else:
        checks.append(_check("compiled_fcstd_exists", False, {"path": str(fcstd_path)}))

    passed = all(item["passed"] for item in checks)
    return {"passed": passed, "checks": checks, "parser": parser_result, "geometry": geometry_result}
