"""Prepare and merge CAD training datasets for comparison experiments."""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from dataset_v1.scripts.training_export import iter_training_examples


@dataclass(frozen=True)
class DatasetSourceStats:
    source: str
    examples: int
    geometries: int


@dataclass(frozen=True)
class MergeStats:
    total_examples: int
    cad_examples: int
    primitive_examples: int
    total_geometries: int
    cad_geometries: int
    primitive_geometries: int
    duplicates_removed: int
    invalid_examples: int


def canonical_output_json(output: dict[str, Any]) -> str:
    return json.dumps(output, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def example_dedup_key(record: dict[str, Any]) -> tuple[str, str]:
    user_input = record["input"].strip()
    output = record["output"]
    return user_input, canonical_output_json(output)


def geometry_group_key(record: dict[str, Any]) -> str:
    if record.get("geometry_id"):
        return str(record["geometry_id"])
    if record.get("shape_id"):
        return f"primitive:{record['shape_id']}"
    if record.get("model_id"):
        return f"cad:{record['model_id']}"
    output = record.get("output", {})
    operations = output.get("operations") if isinstance(output, dict) else None
    if not isinstance(operations, list):
        raise ValueError("Record is missing output.operations for geometry grouping.")
    payload = json.dumps(operations, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"hash:{digest}"


def validate_training_record(record: dict[str, Any], *, line_number: int | None = None) -> None:
    prefix = f"line {line_number}: " if line_number is not None else ""
    if not isinstance(record, dict):
        raise ValueError(f"{prefix}record must be an object")

    user_input = record.get("input")
    if not isinstance(user_input, str) or not user_input.strip():
        raise ValueError(f"{prefix}missing or empty input")

    output = record.get("output")
    if not isinstance(output, dict):
        raise ValueError(f"{prefix}missing output object")
    operations = output.get("operations")
    if not isinstance(operations, list) or not operations:
        raise ValueError(f"{prefix}missing or empty output.operations")


def load_jsonl_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            record = json.loads(stripped)
            validate_training_record(record, line_number=line_number)
            records.append(record)
    if not records:
        raise ValueError(f"No training records found in {path}")
    return records


def build_cad_records(
    *,
    json_dir: Path,
    metadata_path: Path | None,
    source_tag: str = "cad_v1",
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for example in iter_training_examples(json_dir, metadata_path=metadata_path):
        records.append(
            {
                "input": example.input,
                "output": {"operations": example.operations},
                "model_id": example.model_id,
                "prompt_index": example.prompt_index,
                "geometry_id": f"cad:{example.model_id}",
                "dataset_source": source_tag,
            }
        )
    return records


def build_primitive_records(path: Path, *, source_tag: str = "primitives_v1") -> list[dict[str, Any]]:
    records = load_jsonl_records(path)
    enriched: list[dict[str, Any]] = []
    for record in records:
        shape_id = record.get("shape_id")
        if not shape_id:
            raise ValueError(f"Primitive record is missing shape_id: {record.get('input', '')[:80]}")
        enriched.append(
            {
                **record,
                "geometry_id": f"primitive:{shape_id}",
                "dataset_source": source_tag,
            }
        )
    return enriched


def dedupe_records(records: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, Any]] = []
    removed = 0
    for record in records:
        key = example_dedup_key(record)
        if key in seen:
            removed += 1
            continue
        seen.add(key)
        unique.append(record)
    return unique, removed


def assign_geometry_splits(
    records: list[dict[str, Any]],
    *,
    seed: int,
    val_ratio: float = 0.1,
) -> dict[str, str]:
    geometry_ids = sorted({geometry_group_key(record) for record in records})
    if not geometry_ids:
        raise ValueError("No geometry groups found for split assignment.")

    rng = random.Random(seed)
    shuffled = list(geometry_ids)
    rng.shuffle(shuffled)
    val_size = max(1, int(len(shuffled) * val_ratio))
    val_ids = set(shuffled[:val_size])
    return {geometry_id: ("val" if geometry_id in val_ids else "train") for geometry_id in geometry_ids}


def split_records_by_geometry(
    records: list[dict[str, Any]],
    geometry_splits: dict[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    train_records: list[dict[str, Any]] = []
    val_records: list[dict[str, Any]] = []
    for record in records:
        geometry_id = geometry_group_key(record)
        split = geometry_splits.get(geometry_id)
        if split is None:
            raise KeyError(f"Geometry group missing from split manifest: {geometry_id}")
        if split == "val":
            val_records.append(record)
        else:
            train_records.append(record)
    if not train_records or not val_records:
        raise ValueError("Geometry split produced an empty train or validation set.")
    return train_records, val_records


def write_jsonl(records: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def build_split_manifest(
    *,
    geometry_splits: dict[str, str],
    records: list[dict[str, Any]],
    seed: int,
    val_ratio: float,
) -> dict[str, Any]:
    train_geometries = sorted(geometry_id for geometry_id, split in geometry_splits.items() if split == "train")
    val_geometries = sorted(geometry_id for geometry_id, split in geometry_splits.items() if split == "val")

    train_records, val_records = split_records_by_geometry(records, geometry_splits)
    by_source_train: dict[str, int] = {}
    by_source_val: dict[str, int] = {}
    for record in train_records:
        source = str(record.get("dataset_source", "unknown"))
        by_source_train[source] = by_source_train.get(source, 0) + 1
    for record in val_records:
        source = str(record.get("dataset_source", "unknown"))
        by_source_val[source] = by_source_val.get(source, 0) + 1

    return {
        "seed": seed,
        "val_ratio": val_ratio,
        "split_strategy": "geometry_aware",
        "geometry_splits": geometry_splits,
        "train_geometries": train_geometries,
        "val_geometries": val_geometries,
        "counts": {
            "train_examples": len(train_records),
            "val_examples": len(val_records),
            "train_geometries": len(train_geometries),
            "val_geometries": len(val_geometries),
            "train_by_source": by_source_train,
            "val_by_source": by_source_val,
        },
    }


def merge_comparison_datasets(
    *,
    cad_json_dir: Path,
    cad_metadata_path: Path | None,
    primitive_training_path: Path,
    output_dir: Path,
    seed: int = 42,
    val_ratio: float = 0.1,
) -> dict[str, Any]:
    cad_records = build_cad_records(json_dir=cad_json_dir, metadata_path=cad_metadata_path)
    primitive_records = build_primitive_records(primitive_training_path)

    merged_records, duplicates_removed = dedupe_records([*cad_records, *primitive_records])
    geometry_splits = assign_geometry_splits(merged_records, seed=seed, val_ratio=val_ratio)
    split_manifest = build_split_manifest(
        geometry_splits=geometry_splits,
        records=merged_records,
        seed=seed,
        val_ratio=val_ratio,
    )

    baseline_path = output_dir / "baseline_training_data.jsonl"
    merged_path = output_dir / "merged_training_data.jsonl"
    manifest_path = output_dir / "comparison_split_manifest.json"
    stats_path = output_dir / "dataset_statistics.json"

    write_jsonl(cad_records, baseline_path)
    write_jsonl(merged_records, merged_path)
    manifest_path.write_text(json.dumps(split_manifest, indent=2) + "\n", encoding="utf-8")

    stats = {
        "seed": seed,
        "val_ratio": val_ratio,
        "baseline_dataset": str(baseline_path),
        "merged_dataset": str(merged_path),
        "split_manifest": str(manifest_path),
        "baseline_examples": len(cad_records),
        "merged_examples": len(merged_records),
        "cad_examples": len(cad_records),
        "primitive_examples": len(primitive_records),
        "cad_geometries": len({geometry_group_key(record) for record in cad_records}),
        "primitive_geometries": len({geometry_group_key(record) for record in primitive_records}),
        "total_geometries": len(geometry_splits),
        "duplicates_removed": duplicates_removed,
        "train_examples": split_manifest["counts"]["train_examples"],
        "val_examples": split_manifest["counts"]["val_examples"],
        "train_geometries": split_manifest["counts"]["train_geometries"],
        "val_geometries": split_manifest["counts"]["val_geometries"],
        "train_by_source": split_manifest["counts"]["train_by_source"],
        "val_by_source": split_manifest["counts"]["val_by_source"],
    }
    stats_path.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    return stats
