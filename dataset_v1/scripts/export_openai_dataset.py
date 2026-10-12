#!/usr/bin/env python3
"""Export OpenAI supervised fine-tuning JSONL from internal training data."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dataset_v1.scripts.training_export import export_openai_finetune_data  # noqa: E402
from dataset_v1.scripts.validate_openai_dataset import (  # noqa: E402
    print_validation_summary,
    validate_openai_dataset,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert internal training_data.jsonl to OpenAI fine-tuning format.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "dataset_v1" / "train" / "training_data.jsonl",
        help="Internal training dataset JSONL.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "dataset_v1" / "train" / "openai_finetune.jsonl",
        help="OpenAI fine-tuning JSONL output path.",
    )
    parser.add_argument(
        "--system-prompt",
        type=Path,
        default=PROJECT_ROOT / "dataset_v1" / "system_prompt.txt",
        help="System prompt file inserted into every conversation.",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip post-export validation.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    stats = export_openai_finetune_data(
        args.input,
        args.output,
        system_prompt_path=args.system_prompt,
    )
    print(f"Exported {stats['examples']} OpenAI fine-tuning conversations.")
    print(f"Input : {args.input}")
    print(f"Output: {args.output}")

    if args.skip_validation:
        return 0

    result = validate_openai_dataset(args.output, expected_count=stats["examples"])
    print()
    print_validation_summary(result, dataset_path=args.output, expected_count=stats["examples"])
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
