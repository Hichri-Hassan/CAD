#!/usr/bin/env python3
"""Run Stage 3 HPO, final training, and generation evaluation sequentially."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYTHON = sys.executable


def run_step(label: str, command: list[str]) -> None:
    print(f"\n=== {label} ===")
    print(" ".join(command))
    result = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Step failed ({label}) with exit code {result.returncode}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Complete Stage 3 alpha search, final training, and evaluation.",
    )
    parser.add_argument(
        "--skip-stage3",
        action="store_true",
        help="Skip Stage 3 training (use existing runs).",
    )
    parser.add_argument(
        "--skip-final-train",
        action="store_true",
        help="Skip final model training.",
    )
    parser.add_argument(
        "--skip-eval",
        action="store_true",
        help="Skip generation evaluation.",
    )
    parser.add_argument(
        "--overwrite-stage3",
        action="store_true",
        help="Recreate Stage 3 experiment directory before planning.",
    )
    parser.add_argument(
        "--overwrite-final",
        action="store_true",
        help="Recreate final experiment directory before training.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if not args.skip_stage3:
        plan_cmd = [
            PYTHON,
            "training/scripts/plan_stage3_alpha_only.py",
            "--overwrite",
        ]
        if not args.overwrite_stage3:
            plan_cmd.remove("--overwrite")
        run_step("Plan Stage 3", plan_cmd)
        run_step(
            "Run Stage 3",
            [
                PYTHON,
                "training/scripts/run_hpo_stage.py",
                "--stage-dir",
                "training/experiments/stage3",
            ],
        )
        run_step(
            "Report Stage 3",
            [PYTHON, "training/scripts/report_stage3_alpha.py"],
        )

    if not args.skip_final_train:
        final_cmd = [
            PYTHON,
            "training/scripts/train_final_model.py",
            "--overwrite",
        ]
        if not args.overwrite_final:
            final_cmd.remove("--overwrite")
        run_step("Train final model", final_cmd)

    if not args.skip_eval:
        best_config = PROJECT_ROOT / "training" / "best_configs" / "final_best.yaml"
        if not best_config.exists():
            best_config = PROJECT_ROOT / "training" / "best_configs" / "stage3_best.yaml"
        import yaml

        payload = yaml.safe_load(best_config.read_text(encoding="utf-8"))
        adapter = payload.get("best_checkpoint") or payload.get("best_run_dir", "")
        if adapter and not str(adapter).endswith("adapter"):
            adapter = str(Path(adapter) / "checkpoints" / "adapter")
        run_step(
            "Evaluate generation quality",
            [
                PYTHON,
                "training/scripts/evaluate_generation.py",
                "--adapter",
                str(adapter),
            ],
        )

    print("\nPipeline complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
