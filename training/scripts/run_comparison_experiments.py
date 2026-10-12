#!/usr/bin/env python3
"""Prepare datasets, plan, and train comparison LoRA experiments."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from training.lora_trainer import DEFAULT_SYSTEM_PROMPT_PATH, TrainOptions, train_experiment


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run comparison LoRA training workflow.")
    parser.add_argument(
        "--experiment",
        choices=["baseline_lora", "primitives_lora", "both"],
        default="both",
        help="Which experiment(s) to train.",
    )
    parser.add_argument("--prepare-data", action="store_true", help="Rebuild comparison datasets.")
    parser.add_argument("--plan", action="store_true", help="Create experiment directories.")
    parser.add_argument("--train", action="store_true", help="Train planned experiments.")
    parser.add_argument("--report", action="store_true", help="Write Markdown reports after training.")
    parser.add_argument("--dry-run", action="store_true", help="Run short smoke-test training.")
    parser.add_argument("--max-steps", type=int, default=None, help="Optional training step limit.")
    parser.add_argument(
        "--run-id",
        default="run_001",
        help="Run identifier inside each experiment stage directory.",
    )
    return parser


def _run_script(script_name: str, *args: str) -> None:
    script_path = PROJECT_ROOT / "training" / "scripts" / script_name
    command = [sys.executable, str(script_path), *args]
    print(f"Running: {' '.join(command)}")
    subprocess.run(command, check=True)


def _experiment_dir(stage: str, run_id: str) -> Path:
    return PROJECT_ROOT / "training" / "experiments" / stage / run_id


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    selected = ["baseline_lora", "primitives_lora"] if args.experiment == "both" else [args.experiment]

    if args.prepare_data:
        _run_script("prepare_comparison_datasets.py")

    if args.plan:
        plan_args = ["--experiment", args.experiment, "--run-id", args.run_id]
        _run_script("plan_comparison_experiments.py", *plan_args)

    if not (args.prepare_data or args.plan or args.train or args.report):
        print("Nothing to do. Pass --prepare-data, --plan, --train, and/or --report.", file=sys.stderr)
        return 1

    if args.train:
        for stage in selected:
            experiment_dir = _experiment_dir(stage, args.run_id)
            if not experiment_dir.exists():
                raise FileNotFoundError(
                    f"Missing experiment directory: {experiment_dir}. Run with --plan first."
                )
            print(f"Training {stage}/{args.run_id}")
            result = train_experiment(
                TrainOptions(
                    experiment_dir=experiment_dir,
                    dry_run=args.dry_run,
                    max_steps=args.max_steps,
                    system_prompt_path=DEFAULT_SYSTEM_PROMPT_PATH,
                )
            )
            if result.status != "completed":
                return 1

    if args.report:
        for stage in selected:
            experiment_dir = _experiment_dir(stage, args.run_id)
            _run_script(
                "report_comparison_experiment.py",
                "--experiment-dir",
                str(experiment_dir),
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
