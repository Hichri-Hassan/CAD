#!/usr/bin/env python3
"""Execute LoRA fine-tuning for a single planned HPO experiment."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from training.lora_trainer import (  # noqa: E402
    DEFAULT_SYSTEM_PROMPT_PATH,
    TrainOptions,
    fail_experiment,
    load_experiment_config,
    train_experiment,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train one LoRA experiment from the HPO framework.")
    parser.add_argument(
        "--experiment",
        type=Path,
        required=True,
        help="Path to an experiment directory (e.g. training/experiments/stage1/run_001).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run a short pipeline validation (defaults to 5 optimization steps).",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help="Override the number of optimization steps.",
    )
    parser.add_argument(
        "--system-prompt",
        type=Path,
        default=DEFAULT_SYSTEM_PROMPT_PATH,
        help="Optional system prompt file for chat formatting.",
    )
    return parser


def print_summary(result) -> None:
    config = result.config
    metrics = result.metrics.get("core", {})
    print("----------------------------------------")
    print("Experiment summary")
    print(f"Experiment : {config.stage}/{config.run_id}")
    print(f"Status     : {result.status}")
    print(f"LoRA r     : {config.searchable.lora_r}")
    print(f"LR         : {config.searchable.learning_rate}")
    print(f"Epochs     : {config.searchable.num_epochs}")
    print(f"Dropout    : {config.searchable.lora_dropout}")
    print(f"Alpha      : {config.searchable.lora_alpha}")
    print(f"Train loss : {metrics.get('train_loss')}")
    print(f"Val loss   : {metrics.get('val_loss')}")
    print(f"Trainable  : {metrics.get('trainable_parameters')}")
    print(f"Time (s)   : {metrics.get('training_time_seconds')}")
    print(f"Checkpoint : {metrics.get('checkpoint_path')}")
    print("----------------------------------------")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    experiment_dir = args.experiment.resolve()
    if not experiment_dir.exists():
        print(f"Experiment directory not found: {experiment_dir}", file=sys.stderr)
        return 1

    options = TrainOptions(
        experiment_dir=experiment_dir,
        max_steps=args.max_steps,
        dry_run=args.dry_run,
        system_prompt_path=args.system_prompt,
    )

    config = load_experiment_config(experiment_dir)
    print(f"Starting experiment {config.stage}/{config.run_id}")
    if options.dry_run:
        print("Dry-run mode enabled.")

    try:
        result = train_experiment(options)
    except Exception as exc:  # noqa: BLE001
        fail_experiment(experiment_dir, config, exc)
        print(f"Experiment failed: {exc}", file=sys.stderr)
        return 1

    print_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
