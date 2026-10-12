#!/usr/bin/env python3
"""Plan Stage 3 alpha-only HPO experiments.

Stage 3 searches ONLY:
  - lora_alpha in [16, 32, 64]

Everything else is fixed to the Stage 2 best configuration stored at:
  training/best_configs/stage2_best.yaml
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from training.hpo.experiment import (
    ExperimentPlan,
    FixedHyperparameters,
    ReproducibilityInfo,
    RunConfig,
    SearchableHyperparameters,
)
from training.hpo.tracking import ExperimentTracker


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan Stage 3 alpha-only HPO runs.")
    parser.add_argument(
        "--stage3-dir",
        type=Path,
        default=PROJECT_ROOT / "training" / "experiments" / "stage3",
        help="Stage 3 experiment directory.",
    )
    parser.add_argument(
        "--stage2-best",
        type=Path,
        default=PROJECT_ROOT / "training" / "best_configs" / "stage2_best.yaml",
        help="Path to stage2 best config YAML.",
    )
    parser.add_argument(
        "--alphas",
        type=int,
        nargs="*",
        default=[16, 32, 64],
        help="LoRA alpha values to evaluate (default: 16 32 64).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Delete and recreate the stage3 directory.",
    )
    return parser


def _ensure_clean_dir(path: Path, *, overwrite: bool) -> None:
    if path.exists():
        if not overwrite:
            raise FileExistsError(
                f"{path} already exists. Use --overwrite to delete and recreate."
            )
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    stage3_dir = args.stage3_dir.resolve()
    stage3_dir.parent.mkdir(parents=True, exist_ok=True)
    _ensure_clean_dir(stage3_dir, overwrite=args.overwrite)

    with args.stage2_best.open(encoding="utf-8") as handle:
        stage2_best = yaml.safe_load(handle)

    full_config = stage2_best["full_config"]
    fixed_raw = full_config["fixed"]
    reproducibility_raw = full_config["reproducibility"]
    searchable_raw = full_config["searchable"]

    fixed = FixedHyperparameters(**fixed_raw)
    reproducibility = ReproducibilityInfo(**reproducibility_raw)

    experiments_root = stage3_dir.parent.resolve()
    tracker = ExperimentTracker(experiments_root)

    for run_index, alpha in enumerate(args.alphas, start=1):
        run_id = f"run_{run_index:03d}"
        searchable = SearchableHyperparameters(
            lora_r=int(searchable_raw["lora_r"]),
            learning_rate=float(searchable_raw["learning_rate"]),
            num_epochs=int(searchable_raw["num_epochs"]),
            lora_dropout=float(searchable_raw["lora_dropout"]),
            lora_alpha=int(alpha),
        )

        run_config = RunConfig(
            stage="stage3",
            run_id=run_id,
            searchable=searchable,
            fixed=fixed,
            reproducibility=reproducibility,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        plan = ExperimentPlan(
            stage="stage3",
            run_id=run_id,
            run_index=run_index,
            config=run_config,
            run_dir=str(tracker.run_dir("stage3", run_id)),
            search_overrides={"lora_alpha": alpha},
            frozen_from={"stage2_best": True},
        )
        tracker.initialize_run(plan)

    print(
        f"Planned {len(args.alphas)} Stage 3 runs in {stage3_dir} "
        f"(lora_alpha={args.alphas})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
