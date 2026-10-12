#!/usr/bin/env python3
"""Run all experiments in one HPO stage sequentially."""

from __future__ import annotations

import argparse
import json
import subprocess
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


def load_status(experiment_dir: Path) -> dict:
    status_path = experiment_dir / "status.json"
    if not status_path.exists():
        return {"status": "planned"}
    return json.loads(status_path.read_text(encoding="utf-8"))


def should_skip(experiment_dir: Path, *, force: bool) -> bool:
    if force:
        return False
    status = load_status(experiment_dir)
    if status.get("status") != "completed":
        return False
    if status.get("dry_run"):
        return False
    return True


def discover_runs(stage_dir: Path) -> list[Path]:
    return sorted(path for path in stage_dir.glob("run_*") if path.is_dir())


def run_stage(
    stage_dir: Path,
    *,
    force: bool = False,
    dry_run: bool = False,
    max_steps: int | None = None,
) -> list[dict]:
    runs = discover_runs(stage_dir)
    if not runs:
        raise FileNotFoundError(f"No experiment runs found in {stage_dir}")

    outcomes: list[dict] = []
    total = len(runs)

    for index, experiment_dir in enumerate(runs, start=1):
        config = load_experiment_config(experiment_dir)
        label = f"{config.stage}/{config.run_id}"
        print(f"\n[{index}/{total}] {label}")

        if should_skip(experiment_dir, force=force):
            print("  Skipping (already completed).")
            outcomes.append(
                {
                    "experiment": label,
                    "run_dir": str(experiment_dir),
                    "status": "skipped",
                }
            )
            continue

        options = TrainOptions(
            experiment_dir=experiment_dir,
            dry_run=dry_run,
            max_steps=max_steps,
            system_prompt_path=DEFAULT_SYSTEM_PROMPT_PATH,
        )

        try:
            result = train_experiment(options)
            outcomes.append(
                {
                    "experiment": label,
                    "run_dir": str(experiment_dir),
                    "status": result.status,
                    "val_loss": result.metrics.get("core", {}).get("val_loss"),
                }
            )
            print(f"  Completed with val_loss={outcomes[-1]['val_loss']}")
        except Exception as exc:  # noqa: BLE001
            fail_experiment(experiment_dir, config, exc)
            print(f"  Failed: {exc}")
            outcomes.append(
                {
                    "experiment": label,
                    "run_dir": str(experiment_dir),
                    "status": "failed",
                    "error": str(exc),
                }
            )

    return outcomes


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run all experiments in an HPO stage sequentially.")
    parser.add_argument(
        "--stage-dir",
        type=Path,
        default=PROJECT_ROOT / "training" / "experiments" / "stage1",
        help="Directory containing stage experiment runs.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run experiments even if already completed.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run each experiment in dry-run mode (for testing only).",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help="Limit optimization steps per experiment.",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate stage report and best-config YAML after all runs finish.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    stage_dir = args.stage_dir.resolve()
    outcomes = run_stage(
        stage_dir,
        force=args.force,
        dry_run=args.dry_run,
        max_steps=args.max_steps,
    )

    completed = sum(1 for item in outcomes if item["status"] == "completed")
    failed = sum(1 for item in outcomes if item["status"] == "failed")
    skipped = sum(1 for item in outcomes if item["status"] == "skipped")

    print("\nStage run summary")
    print("-----------------")
    print(f"Completed : {completed}")
    print(f"Failed    : {failed}")
    print(f"Skipped   : {skipped}")

    if args.report and stage_dir.name:
        report_script = PROJECT_ROOT / "training" / "scripts" / "report_stage.py"
        report_result = subprocess.run(
            [sys.executable, str(report_script), "--stage", stage_dir.name],
            check=False,
        )
        return report_result.returncode

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
