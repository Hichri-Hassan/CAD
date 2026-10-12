#!/usr/bin/env python3
"""Export supervised fine-tuning data from canonical Dataset V1 JSON files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dataset_v1.scripts.training_export import EXPORTERS, export_training_data  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Export training data from canonical CAD JSON files without modifying them."
        ),
    )
    parser.add_argument(
        "--json-dir",
        type=Path,
        default=PROJECT_ROOT / "dataset_v1" / "train" / "json",
        help="Directory containing canonical training JSON files.",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=PROJECT_ROOT / "dataset_v1" / "train" / "metadata.csv",
        help="Training split metadata CSV (optional ordering source).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "dataset_v1" / "train" / "training_data.jsonl",
        help="Output JSONL file path.",
    )
    parser.add_argument(
        "--format",
        choices=sorted(EXPORTERS),
        default="simple",
        help="Export format (default: simple input -> operations JSONL).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    stats = export_training_data(
        args.json_dir,
        args.output,
        metadata_path=args.metadata,
        format_name=args.format,
    )
    print(f"Exported {stats['examples']} examples from {stats['models']} models.")
    print(f"Output: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
