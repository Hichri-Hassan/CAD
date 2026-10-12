#!/usr/bin/env python3
"""Create deterministic train/test split for frozen Dataset V1."""

from __future__ import annotations

import argparse
import csv
import json
import random
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_SEED = 42
TRAIN_COUNT = 40
TEST_COUNT = 7
METADATA_FIELDS = ("model_id", "original_filename", "json_filename")


def load_v1_records(v1_dir: Path) -> list[dict[str, str]]:
    metadata_path = v1_dir / "metadata.csv"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Missing V1 metadata: {metadata_path}")

    with metadata_path.open(encoding="utf-8", newline="") as handle:
        records = list(csv.DictReader(handle))

    if len(records) != TRAIN_COUNT + TEST_COUNT:
        raise ValueError(
            f"Expected {TRAIN_COUNT + TEST_COUNT} V1 models, found {len(records)} in {metadata_path}"
        )
    return records


def split_records(records: list[dict[str, str]], seed: int) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    rng = random.Random(seed)
    shuffled = records.copy()
    rng.shuffle(shuffled)
    train = shuffled[:TRAIN_COUNT]
    test = shuffled[TRAIN_COUNT:]
    if len(train) != TRAIN_COUNT or len(test) != TEST_COUNT:
        raise ValueError(f"Split produced {len(train)} train and {len(test)} test records.")
    return train, test


def write_split_metadata(split_dir: Path, rows: list[dict[str, str]]) -> None:
    split_dir.mkdir(parents=True, exist_ok=True)
    (split_dir / "models").mkdir(exist_ok=True)
    (split_dir / "json").mkdir(exist_ok=True)

    with (split_dir / "metadata.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=METADATA_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def copy_split_assets(
    *,
    split_dir: Path,
    rows: list[dict[str, str]],
    examples_dir: Path,
    v1_models_dir: Path,
) -> None:
    models_dir = split_dir / "models"
    json_dir = split_dir / "json"

    for row in rows:
        model_id = row["model_id"]
        original_filename = row["original_filename"]
        json_filename = row["json_filename"]

        source_fcstd = examples_dir / original_filename
        source_json = v1_models_dir / json_filename

        if not source_fcstd.exists():
            raise FileNotFoundError(f"Missing source FCStd: {source_fcstd}")
        if not source_json.exists():
            raise FileNotFoundError(f"Missing source JSON: {source_json}")

        shutil.copy2(source_fcstd, models_dir / original_filename)
        shutil.copy2(source_json, json_dir / json_filename)


def create_split(
    v1_dir: Path,
    examples_dir: Path,
    *,
    seed: int = DEFAULT_SEED,
) -> dict[str, list[str]]:
    """Create train/test directories and return model_id lists for each split."""
    records = load_v1_records(v1_dir)
    train_records, test_records = split_records(records, seed)
    v1_models_dir = v1_dir / "models"

    split_rows: dict[str, list[dict[str, str]]] = {}
    for split_name, selected_records in (("train", train_records), ("test", test_records)):
        rows = [
            {
                "model_id": record["model_id"],
                "original_filename": record["source_fcstd"],
                "json_filename": f"{record['model_id']}.json",
            }
            for record in selected_records
        ]
        split_dir = v1_dir / split_name
        write_split_metadata(split_dir, rows)
        copy_split_assets(
            split_dir=split_dir,
            rows=rows,
            examples_dir=examples_dir,
            v1_models_dir=v1_models_dir,
        )
        split_rows[split_name] = [row["model_id"] for row in rows]

    manifest = {
        "seed": seed,
        "train_count": TRAIN_COUNT,
        "test_count": TEST_COUNT,
        "train_model_ids": split_rows["train"],
        "test_model_ids": split_rows["test"],
    }
    manifest_path = v1_dir / "split_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return split_rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Create Dataset V1 train/test split.")
    parser.add_argument(
        "--v1-dir",
        type=Path,
        default=PROJECT_ROOT / "dataset_v1",
        help="Dataset V1 root directory.",
    )
    parser.add_argument(
        "--examples",
        type=Path,
        default=PROJECT_ROOT / "examples",
        help="Directory containing source .FCStd files.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help="Random seed for deterministic split (default: 42).",
    )
    args = parser.parse_args()

    split_rows = create_split(args.v1_dir, args.examples, seed=args.seed)
    print(f"Created train split: {len(split_rows['train'])} models")
    print(f"Created test split: {len(split_rows['test'])} models")
    print(f"Wrote {args.v1_dir / 'split_manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
