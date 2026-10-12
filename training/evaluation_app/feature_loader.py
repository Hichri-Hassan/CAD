"""Load generated CAD feature models for the evaluation dashboard."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ThroughHoleRecord:
    shape_id: str
    index: int
    length_mm: float
    width_mm: float
    height_mm: float
    diameter_mm: float
    fcstd_path: Path
    json_path: Path
    meta_path: Path
    validation_path: Path | None
    passed_validation: bool
    prompts: list[str]
    operations: list[dict[str, Any]]
    validation_summary: dict[str, Any]


def load_through_hole_records(features_dir: Path, project_root: Path) -> list[ThroughHoleRecord]:
    """Scan through_holes folder for metadata + canonical JSON."""
    through_dir = features_dir / "through_holes"
    if not through_dir.exists():
        return []

    records: list[ThroughHoleRecord] = []
    for meta_path in sorted(through_dir.glob("*.meta.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        json_rel = meta.get("json_path", "")
        json_path = (project_root / json_rel).resolve() if json_rel else meta_path.with_suffix("").with_suffix(".json")
        if not json_path.exists():
            json_path = meta_path.with_name(meta_path.name.replace(".meta.json", ".json"))
        fcstd_rel = meta.get("fcstd_path", "")
        fcstd_path = (project_root / fcstd_rel).resolve() if fcstd_rel else json_path.with_suffix(".FCStd")

        validation_path = meta_path.with_name(meta_path.name.replace(".meta.json", ".validation.json"))
        validation_summary: dict[str, Any] = {}
        if validation_path.exists():
            validation_raw = json.loads(validation_path.read_text(encoding="utf-8"))
            validation_summary = {
                "passed": validation_raw.get("passed"),
                "volume": validation_raw.get("geometry", {}).get("volume"),
                "bbox": validation_raw.get("geometry", {}).get("bbox"),
            }

        cad_json = json.loads(json_path.read_text(encoding="utf-8"))
        dims = meta.get("dimensions", {})
        records.append(
            ThroughHoleRecord(
                shape_id=str(meta.get("shape_id", meta_path.stem.replace(".meta", ""))),
                index=int(meta.get("index", 0)),
                length_mm=float(dims.get("length_mm", 0)),
                width_mm=float(dims.get("width_mm", 0)),
                height_mm=float(dims.get("height_mm", 0)),
                diameter_mm=float(dims.get("diameter_mm", 0)),
                fcstd_path=fcstd_path,
                json_path=json_path,
                meta_path=meta_path,
                validation_path=validation_path if validation_path.exists() else None,
                passed_validation=bool(meta.get("passed_validation")),
                prompts=list(meta.get("prompts", [])),
                operations=list(cad_json.get("operations", [])),
                validation_summary=validation_summary,
            )
        )
    return records


def extract_hole_specs(operations: list[dict[str, Any]]) -> dict[str, Any]:
    pad = next((op for op in operations if op.get("type") == "Pad"), {})
    hole = next((op for op in operations if op.get("type") == "Hole"), {})
    hole_sketch = next((op for op in operations if op.get("id") == hole.get("profile")), {})
    circles = [
        entity
        for entity in hole_sketch.get("entities", [])
        if entity.get("type") == "Circle"
    ]
    centers = [c.get("center", [None, None]) for c in circles]
    radii = [c.get("radius") for c in circles]

    center = centers[0] if centers else [None, None]
    radius = radii[0] if radii else None
    return {
        "pad_height_mm": pad.get("length"),
        "hole_diameter_mm": hole.get("diameter"),
        "hole_depth": hole.get("depth"),
        "hole_count": len(circles),
        "circle_centers_mm": centers,
        "circle_radii_mm": radii,
        "circle_center_mm": center,
        "circle_radius_mm": radius,
        "sketch_support": hole_sketch.get("support") or hole_sketch.get("plane"),
    }
