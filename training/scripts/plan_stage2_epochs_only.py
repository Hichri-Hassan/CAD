#!/usr/bin/env python3
"""Plan Stage 2 epoch-only HPO experiments.

Stage 2 searches ONLY:
  - num_epochs in [1..8]

Everything else is fixed to the Stage 1 best configuration stored at:
  training/best_configs/stage1_best.yaml
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
    parser = argparse.ArgumentParser(description="Plan Stage 2 epoch-only HPO runs.")
    parser.add_argument(
        "--stage2-dir",
        type=Path,
        default=PROJECT_ROOT / "training" / "experiments" / "stage2",
        help="Stage 2 experiment directory.",
    )
    parser.add_argument(
        "--stage1-best",
        type=Path,
        default=PROJECT_ROOT / "training" / "best_configs" / "stage1_best.yaml",
        help="Path to stage1 best config YAML.",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        nargs="*",
        default=list(range(1, 9)),
        help="Epoch values to evaluate (default: 1..8).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Delete and recreate the stage2 directory.",
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

    stage2_dir = args.stage2_dir.resolve()
    stage2_dir.parent.mkdir(parents=True, exist_ok=True)
    _ensure_clean_dir(stage2_dir, overwrite=args.overwrite)

    with args.stage1_best.open(encoding="utf-8") as handle:
        stage1_best = yaml.safe_load(handle)

    full_config = stage1_best["full_config"]
    fixed_raw = full_config["fixed"]
    reproducibility_raw = full_config["reproducibility"]
    searchable_raw = full_config["searchable"]

    fixed = FixedHyperparameters(**fixed_raw)
    reproducibility = ReproducibilityInfo(**reproducibility_raw)

    experiments_root = stage2_dir.parent.resolve()
    tracker = ExperimentTracker(experiments_root)

    for run_index, epochs in enumerate(args.epochs, start=1):
        run_id = f"run_{run_index:03d}"
        searchable = SearchableHyperparameters(
            lora_r=int(searchable_raw["lora_r"]),
            learning_rate=float(searchable_raw["learning_rate"]),
            num_epochs=int(epochs),
            lora_dropout=float(searchable_raw["lora_dropout"]),
            lora_alpha=int(searchable_raw["lora_alpha"]),
        )

        run_config = RunConfig(
            stage="stage2",
            run_id=run_id,
            searchable=searchable,
            fixed=fixed,
            reproducibility=reproducibility,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        plan = ExperimentPlan(
            stage="stage2",
            run_id=run_id,
            run_index=run_index,
            config=run_config,
            run_dir=str(tracker.run_dir("stage2", run_id)),
            search_overrides={"num_epochs": epochs},
            frozen_from={"stage1_best": True},
        )
        tracker.initialize_run(plan)

    print(
        f"Planned {len(args.epochs)} Stage 2 runs in {stage2_dir} "
        f"(num_epochs={args.epochs})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

