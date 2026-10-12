#!/usr/bin/env python3
"""Prepare the accumulated dataset and experiment config for the Hole LoRA.

Merges: original CAD + primitives + through-holes + blind-holes
Produces: geometry-aware train/val split, merged JSONL, split manifest, experiment config.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from training.dataset_merge import (
    assign_geometry_splits,
    build_cad_records,
    build_split_manifest,
    dedupe_records,
    geometry_group_key,
    load_jsonl_records,
    split_records_by_geometry,
    write_jsonl,
)


def load_feature_records(features_dir: Path, family_folder: str, source_tag: str) -> list[dict[str, Any]]:
    """Load training records from feature meta.json + canonical JSON files."""
    family_dir = features_dir / family_folder
    if not family_dir.exists():
        return []

    records: list[dict[str, Any]] = []
    for meta_path in sorted(family_dir.glob("*.meta.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if not meta.get("passed_validation"):
            continue
        shape_id = meta["shape_id"]
        json_path = (PROJECT_ROOT / meta["json_path"]).resolve()
        if not json_path.exists():
            continue
        cad_json = json.loads(json_path.read_text(encoding="utf-8"))
        operations = cad_json["operations"]
        prompts = meta.get("prompts", [])
        fcstd_path = meta.get("fcstd_path", "")

        for prompt_index, prompt in enumerate(prompts):
            records.append({
                "input": prompt,
                "output": {"operations": operations},
                "shape_id": shape_id,
                "shape_type": meta.get("shape_type", ""),
                "prompt_index": prompt_index,
                "fcstd_path": fcstd_path,
                "dataset_source": source_tag,
                "geometry_id": f"feature:{shape_id}",
            })
    return records


from typing import Any


def main() -> int:
    output_dir = PROJECT_ROOT / "training" / "experiments" / "hole_lora_benchmark"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load all sources
    cad_records = build_cad_records(
        json_dir=PROJECT_ROOT / "dataset_v1" / "models",
        metadata_path=PROJECT_ROOT / "dataset_v1" / "metadata.csv",
    )

    prim_path = PROJECT_ROOT / "output" / "primitives" / "primitive_training_data.jsonl"
    prim_records: list[dict[str, Any]] = []
    if prim_path.exists():
        raw = load_jsonl_records(prim_path)
        for r in raw:
            sid = r.get("shape_id", "")
            r["geometry_id"] = f"primitive:{sid}"
            r.setdefault("dataset_source", "primitives_v1")
            prim_records.append(r)

    features_dir = PROJECT_ROOT / "output" / "features"
    through_records = load_feature_records(features_dir, "through_holes", "through_hole_v1")
    blind_records = load_feature_records(features_dir, "blind_holes", "blind_hole_v1")

    # 2. Report raw counts
    print("=== Raw counts ===")
    print(f"  Original CAD:  {len(cad_records)}")
    print(f"  Primitives:    {len(prim_records)}")
    print(f"  Through-holes: {len(through_records)}")
    print(f"  Blind-holes:   {len(blind_records)}")
    raw_total = len(cad_records) + len(prim_records) + len(through_records) + len(blind_records)
    print(f"  Raw total:     {raw_total}")

    # 3. Merge + dedupe
    all_records = cad_records + prim_records + through_records + blind_records
    merged, duplicates = dedupe_records(all_records)
    print(f"\n=== After dedup ===")
    print(f"  Duplicates removed: {duplicates}")
    print(f"  Total unique:       {len(merged)}")

    # 4. Count by source
    source_counts = Counter(r.get("dataset_source", "unknown") for r in merged)
    print(f"\n=== By source ===")
    for src, cnt in sorted(source_counts.items()):
        print(f"  {src}: {cnt}")

    # 5. Count unique geometries
    geo_ids = {geometry_group_key(r) for r in merged}
    print(f"\n=== Unique geometries: {len(geo_ids)} ===")

    # 6. Geometry-aware split
    geometry_splits = assign_geometry_splits(merged, seed=42, val_ratio=0.1)
    manifest = build_split_manifest(
        geometry_splits=geometry_splits,
        records=merged,
        seed=42,
        val_ratio=0.1,
    )

    train_records, val_records = split_records_by_geometry(merged, geometry_splits)
    print(f"\n=== Split (seed=42, val_ratio=0.1) ===")
    print(f"  Train examples:    {len(train_records)}")
    print(f"  Val examples:      {len(val_records)}")
    print(f"  Train geometries:  {manifest['counts']['train_geometries']}")
    print(f"  Val geometries:    {manifest['counts']['val_geometries']}")

    # 7. Save merged JSONL + manifest
    merged_path = output_dir / "hole_lora_training_data.jsonl"
    manifest_path = output_dir / "split_manifest.json"
    stats_path = output_dir / "dataset_statistics.json"

    write_jsonl(merged, merged_path)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    stats = {
        "cad_examples": len(cad_records),
        "primitive_examples": len(prim_records),
        "through_hole_examples": len(through_records),
        "blind_hole_examples": len(blind_records),
        "raw_total": raw_total,
        "duplicates_removed": duplicates,
        "total_unique": len(merged),
        "unique_geometries": len(geo_ids),
        "train_examples": len(train_records),
        "val_examples": len(val_records),
        "train_geometries": manifest["counts"]["train_geometries"],
        "val_geometries": manifest["counts"]["val_geometries"],
        "source_counts": dict(source_counts),
    }
    stats_path.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")

    # 8. Create experiment config (benchmark: 100 steps)
    config = {
        "stage": "hole_lora_benchmark",
        "run_id": "run_001",
        "searchable": {
            "lora_r": 8,
            "learning_rate": 0.0003,
            "num_epochs": 8,
            "lora_dropout": 0.05,
            "lora_alpha": 64,
        },
        "fixed": {
            "weight_decay": 0.01,
            "max_seq_length": 4096,
            "optimizer": "adamw_torch",
            "scheduler": "cosine",
            "warmup_ratio": 0.1,
            "per_device_train_batch_size": 2,
            "per_device_eval_batch_size": 2,
            "gradient_accumulation_steps": 4,
            "logging_steps": 1,
            "eval_steps": 200,
            "save_steps": 50,
            "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        },
        "reproducibility": {
            "seed": 42,
            "dataset_version": "hole_lora_v1",
            "dataset_path": str(merged_path.relative_to(PROJECT_ROOT)),
            "model_version": "Qwen/Qwen2.5-3B-Instruct",
            "base_config": "training/configs/qwen_3b.yaml",
            "split_manifest_path": str(manifest_path.relative_to(PROJECT_ROOT)),
            "split_strategy": "geometry_aware",
            "val_ratio": 0.1,
        },
    }

    run_dir = output_dir / "run_001"
    run_dir.mkdir(parents=True, exist_ok=True)
    config_path = run_dir / "config.yaml"

    import yaml
    config_path.write_text(yaml.dump(config, default_flow_style=False, sort_keys=False), encoding="utf-8")

    print(f"\n=== Outputs ===")
    print(f"  Dataset:  {merged_path}")
    print(f"  Manifest: {manifest_path}")
    print(f"  Stats:    {stats_path}")
    print(f"  Config:   {config_path}")
    print(f"\nReady for benchmark: python3 training/scripts/train_lora.py --experiment {run_dir} --max-steps 100")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
