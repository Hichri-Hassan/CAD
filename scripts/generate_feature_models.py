#!/usr/bin/env python3
"""Generate controlled CAD-feature models as authored JSON + compiled .FCStd.

Modes:
- reference: generate a single canonical example
- family: generate (or skip) a controlled diversified dataset and produce:
    - output/features/feature_training_data.jsonl
    - output/features/prompt_dataset.md
    - output/features/through_holes/through_hole_dataset_report.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from compiler.freecad_launcher import find_freecadcmd, run_in_freecad
from compiler.loader import load_cad_json
from feature_catalog import FEATURE_FAMILIES, FeatureFamily
from feature_validation import validate_feature_model


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate CAD feature models.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "output" / "features",
        help="Root directory for feature families (default: output/features).",
    )
    parser.add_argument(
        "--family",
        choices=list(FEATURE_FAMILIES.keys()),
        default="through_hole",
    )
    parser.add_argument(
        "--mode",
        choices=["reference", "family"],
        default="reference",
        help="reference: one canonical model. family: generate multiple controlled variants.",
    )
    parser.add_argument("--count", type=int, default=75, help="Used only with --mode family.")
    return parser


def compile_cad_json(json_path: Path, fcstd_path: Path) -> tuple[bool, str]:
    freecadcmd = find_freecadcmd()
    if freecadcmd is None:
        return False, "FreeCADCmd not found. Install FreeCAD or set FREECAD_CMD."
    result = run_in_freecad(
        PROJECT_ROOT / "compiler" / "freecad_main.py",
        [str(json_path.resolve()), "-o", str(fcstd_path.resolve())],
        project_root=PROJECT_ROOT,
    )
    log = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
    if result.returncode != 0 or not fcstd_path.exists():
        return False, log or "Compilation failed"
    return True, log


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _build_dims_metadata(dims: dict[str, Any], family_id: str) -> dict[str, Any]:
    """Build a serializable dimensions dict for metadata, adapting to each family."""
    if family_id == "through_hole":
        from feature_catalog import hole_centers as _hc
        return {
            "length_mm": float(dims["length"]),
            "width_mm": float(dims["width"]),
            "height_mm": float(dims["height"]),
            "diameter_mm": float(dims["diameter"]),
            "hole_centers_xy": [[float(x), float(y)] for x, y in _hc(dims)],
            "hole_count": len(_hc(dims)),
        }
    if family_id == "blind_hole":
        bt = dims["base_type"]
        meta: dict[str, Any] = {
            "base_type": bt,
            "diameter_mm": float(dims["diameter"]),
            "hole_depth_mm": float(dims["hole_depth"]),
            "hole_cx": float(dims["hole_cx"]),
            "hole_cy": float(dims["hole_cy"]),
        }
        if bt in ("rect", "plate"):
            meta.update({"length_mm": float(dims["length"]), "width_mm": float(dims["width"]),
                         "height_mm": float(dims["height"])})
        elif bt == "triangle":
            meta.update({"base_mm": float(dims["base"]),
                         "triangle_height_mm": float(dims["triangle_height"]),
                         "prism_height_mm": float(dims["prism_height"])})
        elif bt == "cylinder":
            meta.update({"cyl_radius_mm": float(dims["cyl_radius"]),
                         "cyl_height_mm": float(dims["cyl_height"])})
        return meta
    # Fallback: dump all numeric keys.
    return {f"{k}_mm" if isinstance(v, (int, float)) else k: v for k, v in dims.items()}


def generate_one(
    family: FeatureFamily,
    *,
    index: int,
    dims: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    stem = family.filename_builder(index, dims)
    family_dir = output_dir / family.folder
    json_path = family_dir / f"{stem}.json"
    fcstd_path = family_dir / f"{stem}.FCStd"
    meta_path = family_dir / f"{stem}.meta.json"
    validation_path = family_dir / f"{stem}.validation.json"

    cad_json = family.cad_json_builder(dims, stem)
    prompts = family.prompt_builder(dims)
    operations = family.operations_builder(dims)

    write_json(json_path, cad_json)
    load_cad_json(json_path)

    compile_ok, compile_log = compile_cad_json(json_path, fcstd_path)
    validation = validate_feature_model(
        cad_json=cad_json,
        json_path=json_path,
        fcstd_path=fcstd_path if compile_ok else None,
        dims=dims,
        project_root=PROJECT_ROOT,
    )
    if not compile_ok:
        validation["passed"] = False
        validation["checks"].append(
            {"name": "compiler_success", "passed": False, "details": {"error": compile_log}}
        )

    # Build dimensions dict for metadata (family-agnostic).
    dims_meta = _build_dims_metadata(dims, family.family_id)

    metadata = {
        "shape_id": stem,
        "shape_type": family.family_id,
        "index": index,
        "dimensions": dims_meta,
        "fcstd_path": fcstd_path.relative_to(PROJECT_ROOT).as_posix(),
        "json_path": json_path.relative_to(PROJECT_ROOT).as_posix(),
        "prompts": prompts,
        "passed_validation": bool(validation["passed"]),
    }

    write_json(meta_path, metadata)
    write_json(validation_path, validation)

    training_rows = []
    if validation["passed"]:
        rel_fcstd = fcstd_path.relative_to(PROJECT_ROOT).as_posix()
        for prompt_index, prompt in enumerate(prompts):
            training_rows.append(
                {
                    "input": prompt,
                    "output": {"operations": operations},
                    "shape_id": stem,
                    "shape_type": family.family_id,
                    "prompt_index": prompt_index,
                    "fcstd_path": rel_fcstd,
                    "dataset_source": "features_v1",
                }
            )

    return {
        "stem": stem,
        "json_path": json_path,
        "fcstd_path": fcstd_path,
        "meta_path": meta_path,
        "validation_path": validation_path,
        "validation": validation,
        "prompts": prompts,
        "training_rows": training_rows,
    }


def iter_meta_files(through_dir: Path) -> Iterable[Path]:
    yield from sorted(through_dir.glob("*.meta.json"))


def load_record_from_meta(meta_path: Path, through_dir: Path) -> dict[str, Any] | None:
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    shape_id = meta["shape_id"]
    validation_path = through_dir / f"{shape_id}.validation.json"
    if not validation_path.exists():
        return None
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    if not bool(validation.get("passed")):
        return None

    json_path = PROJECT_ROOT / meta["json_path"]
    cad_json = json.loads(json_path.read_text(encoding="utf-8"))

    operations = cad_json["operations"]
    prompts = meta["prompts"]
    fcstd_path = meta["fcstd_path"]

    # Backward compatibility:
    # Older meta.json files may not include hole_centers_xy / hole_count.
    dims = meta.setdefault("dimensions", {})
    if "hole_count" not in dims or "hole_centers_xy" not in dims:
        hole_op = next((op for op in operations if op.get("type") == "Hole"), None)
        hole_sketch = None
        if hole_op:
            hole_sketch = next((op for op in operations if op.get("id") == hole_op.get("profile")), None)

        circles = []
        if hole_sketch:
            circles = [ent for ent in hole_sketch.get("entities", []) if ent.get("type") == "Circle"]

        centers_xy: list[list[float]] = []
        for c in circles:
            center = c.get("center") or []
            if isinstance(center, list) and len(center) == 2:
                centers_xy.append([float(center[0]), float(center[1])])

        dims["hole_centers_xy"] = centers_xy
        dims["hole_count"] = len(centers_xy)

    training_rows = []
    for prompt_index, prompt in enumerate(prompts):
        training_rows.append(
            {
                "input": prompt,
                "output": {"operations": operations},
                "shape_id": shape_id,
                "shape_type": meta["shape_type"],
                "prompt_index": prompt_index,
                "fcstd_path": fcstd_path,
                "dataset_source": "features_v1",
            }
        )

    return {
        "stem": shape_id,
        "json_path": Path(meta["json_path"]),
        "fcstd_path": Path(meta["fcstd_path"]),
        "validation": validation,
        "prompts": prompts,
        "training_rows": training_rows,
        "meta": meta,
        "cad_json": cad_json,
    }


def write_family_outputs(records: list[dict[str, Any]], output_dir: Path, family_id: str) -> None:
    jsonl_path = output_dir / "feature_training_data.jsonl"
    md_path = output_dir / "prompt_dataset.md"

    with jsonl_path.open("w", encoding="utf-8") as handle:
        for record in records:
            for row in record["training_rows"]:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    lines: list[str] = [f"# Feature dataset: {family_id}", ""]
    lines.append(f"Passed models: **{len(records)}**")
    lines.append("")

    for record in records:
        meta = record["meta"]
        dims = meta["dimensions"]
        dims_str = ", ".join(f"{k}={v}" for k, v in dims.items() if isinstance(v, (int, float)))
        lines.extend([
            f"## {record['stem']}",
            "",
            f"- **Validation:** PASS",
            f"- **Dims:** {dims_str}",
            "- **Prompts:**",
        ])
        for i, prompt in enumerate(record["prompts"], start=1):
            lines.append(f"  {i}. {prompt}")
        lines.append("")

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def classify_geometry(record: dict[str, Any]) -> str:
    meta = record["meta"]
    dims = meta["dimensions"]
    shape_type = meta.get("shape_type", "")

    if shape_type == "blind_hole":
        return dims.get("base_type", "rect")

    # through_hole classification
    hole_count_val = int(dims.get("hole_count", 1))
    height = float(dims.get("height_mm", 99))
    centers = dims.get("hole_centers_xy") or []

    if hole_count_val == 4:
        return "four_holes"
    if hole_count_val == 2:
        return "two_holes"
    if height <= 6.0:
        return "thin_plate"
    if not centers:
        return "off_center_single"

    cx, cy = centers[0]
    L = float(dims.get("length_mm", 0))
    W = float(dims.get("width_mm", 0))
    if abs(cx - L / 2.0) <= 1e-6 and abs(cy - W / 2.0) <= 1e-6:
        return "centered_single"
    return "off_center_single"


def build_dataset_report(records: list[dict[str, Any]], output_dir: Path, family_id: str = "") -> dict[str, Any]:
    # Auto-detect categories from actual data.
    all_cats: set[str] = set()
    for r in records:
        all_cats.add(classify_geometry(r))
    categories = sorted(all_cats)
    counts: dict[str, int] = {c: 0 for c in categories}

    for r in records:
        cat = classify_geometry(r)
        if cat in counts:
            counts[cat] += 1

    # Examples + canonical JSON/prompt snippets
    def pick_example(cat: str) -> dict[str, Any] | None:
        for r in records:
            if classify_geometry(r) == cat:
                return r
        return None

    example_map = {cat: pick_example(cat) for cat in categories}

    # Prompt/target pairs: each geometry has 5 prompts
    prompt_target_pairs = sum(len(r["prompts"]) for r in records)

    total_unique_geometries = len(records)

    # Validation pass/fail counts — scan the family folder passed via family_id.
    # Try to find the right folder; fall back to scanning all subdirs.
    failed = 0
    passed = 0
    for sub in output_dir.iterdir():
        if not sub.is_dir():
            continue
        for mp in sub.glob("*.meta.json"):
            pf = json.loads(mp.read_text(encoding="utf-8")).get("passed_validation", False)
            if pf:
                passed += 1
            else:
                failed += 1

    report = {
        "categories": counts,
        "total_unique_geometries": total_unique_geometries,
        "total_prompt_target_pairs": prompt_target_pairs,
        "validation_pass": passed,
        "validation_fail": failed,
        "examples": {},
    }

    for cat, ex in example_map.items():
        if not ex:
            continue
        report["examples"][cat] = {
            "shape_id": ex["stem"],
            "prompts": ex["prompts"],
            "cad_json": ex["cad_json"],
        }

    return report


def write_markdown_report(report: dict[str, Any], output_dir: Path, *, family_id: str = "feature") -> None:
    md_path = output_dir / f"{family_id}_dataset_report.md"
    lines: list[str] = [f"# {family_id} dataset report", ""]
    lines.append(f"Dataset folder: `{output_dir.as_posix()}`")
    lines.append("")

    lines.append("## Category counts")
    for cat, c in report["categories"].items():
        lines.append(f"- **{cat}**: {c}")
    lines.append("")

    lines.append("## Totals")
    lines.append(f"- Unique geometries: **{report['total_unique_geometries']}**")
    lines.append(f"- Prompt/target pairs: **{report['total_prompt_target_pairs']}**")
    lines.append(f"- Validation pass: **{report['validation_pass']}**")
    lines.append(f"- Validation fail: **{report['validation_fail']}**")
    lines.append("")

    for cat in report.get("categories", {}):
        ex = report.get("examples", {}).get(cat)
        if not ex:
            continue
        lines.append(f"## Example: {cat}")
        lines.append(f"- shape_id: `{ex['shape_id']}`")
        lines.append("")
        lines.append("### Prompts (all variants)")
        for i, p in enumerate(ex["prompts"], start=1):
            lines.append(f"{i}. {p}")
        lines.append("")
        lines.append("### Canonical CAD JSON (operations)")
        ops = ex["cad_json"].get("operations")
        lines.append("```json")
        lines.append(json.dumps(ops, indent=2))
        lines.append("```")
        lines.append("")

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    family = FEATURE_FAMILIES[args.family]
    output_dir = args.output_dir.resolve()

    if args.mode == "reference":
        generate_one(
            family,
            index=1,
            dims=dict(family.reference_dims),
            output_dir=output_dir,
        )
        print("Reference model generated.")
        return 0

    # family mode
    through_dir = output_dir / family.folder
    through_dir.mkdir(parents=True, exist_ok=True)

    dims_list = family.dimension_builder(args.count)

    # Generate (or skip) each expected index.
    for index, dims in enumerate(dims_list, start=1):
        stem = family.filename_builder(index, dims)
        json_path = through_dir / f"{stem}.json"
        fcstd_path = through_dir / f"{stem}.FCStd"
        meta_path = through_dir / f"{stem}.meta.json"
        validation_path = through_dir / f"{stem}.validation.json"

        # Skip if already generated and passed.
        if meta_path.exists() and validation_path.exists() and json_path.exists() and fcstd_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            validation = json.loads(validation_path.read_text(encoding="utf-8"))
            if bool(meta.get("passed_validation")) and bool(validation.get("passed")):
                continue

        generate_one(family, index=index, dims=dims, output_dir=output_dir)

    # Collect all passing records from disk (includes existing ones).
    records: list[dict[str, Any]] = []
    for meta_path in iter_meta_files(through_dir):
        rec = load_record_from_meta(meta_path, through_dir)
        if rec is not None:
            records.append(rec)

    records = sorted(records, key=lambda r: r["meta"]["index"])

    # The merged training dataset lives in output/features/, not inside the
    # per-family subfolder.
    write_family_outputs(records, output_dir, family.family_id)

    report = build_dataset_report(records, output_dir, family_id=family.family_id)
    write_markdown_report(report, output_dir / family.folder, family_id=family.family_id)

    report_path = output_dir / family.folder / f"{family.family_id}_dataset_report.md"
    print(f"Family   : {family.family_id}")
    print(f"Count    : {args.count} (attempted indices)")
    print(f"Passed   : {len(records)} geometries")
    print(f"Report   : {report_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

