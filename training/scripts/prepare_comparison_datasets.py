#!/usr/bin/env python3
"""Prepare baseline and merged datasets for LoRA comparison experiments."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from training.dataset_merge import merge_comparison_datasets


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare comparison training datasets.")
    parser.add_argument(
        "--cad-json-dir",
        type=Path,
        default=PROJECT_ROOT / "dataset_v1" / "train" / "json",
        help="Canonical CAD JSON directory for the baseline dataset.",
    )
    parser.add_argument(
        "--cad-metadata",
        type=Path,
        default=PROJECT_ROOT / "dataset_v1" / "train" / "metadata.csv",
        help="Metadata CSV for canonical CAD JSON files.",
    )
    parser.add_argument(
        "--primitive-training",
        type=Path,
        default=PROJECT_ROOT / "output" / "primitives" / "primitive_training_data.jsonl",
        help="Primitive SFT export JSONL.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "dataset_v1" / "train" / "comparison",
        help="Directory for merged datasets and split manifest.",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--val-ratio", type=float, default=0.1)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    stats = merge_comparison_datasets(
        cad_json_dir=args.cad_json_dir.resolve(),
        cad_metadata_path=args.cad_metadata.resolve(),
        primitive_training_path=args.primitive_training.resolve(),
        output_dir=args.output_dir.resolve(),
        seed=args.seed,
        val_ratio=args.val_ratio,
    )

    print("Dataset preparation complete.")
    print(f"  Baseline examples      : {stats['baseline_examples']}")
    print(f"  Primitive examples     : {stats['primitive_examples']}")
    print(f"  Merged total examples  : {stats['merged_examples']}")
    print(f"  Duplicates removed     : {stats['duplicates_removed']}")
    print(f"  Train examples         : {stats['train_examples']}")
    print(f"  Validation examples    : {stats['val_examples']}")
    print(f"  Train geometries       : {stats['train_geometries']}")
    print(f"  Validation geometries  : {stats['val_geometries']}")
    print(f"  Baseline dataset       : {stats['baseline_dataset']}")
    print(f"  Merged dataset         : {stats['merged_dataset']}")
    print(f"  Split manifest         : {stats['split_manifest']}")
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
