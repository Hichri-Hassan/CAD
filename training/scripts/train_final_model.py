#!/usr/bin/env python3
"""Plan and train the final CAD Copilot model using best HPO hyperparameters."""

from __future__ import annotations

import argparse
import json
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
from training.lora_trainer import DEFAULT_SYSTEM_PROMPT_PATH, TrainOptions, train_experiment


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train final model from stage3 best config.")
    parser.add_argument(
        "--stage3-best",
        type=Path,
        default=PROJECT_ROOT / "training" / "best_configs" / "stage3_best.yaml",
        help="Best configuration YAML from Stage 3.",
    )
    parser.add_argument(
        "--final-dir",
        type=Path,
        default=PROJECT_ROOT / "training" / "experiments" / "final",
        help="Final model experiment directory.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Delete and recreate the final experiment directory.",
    )
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help="Only create the experiment directory without training.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run a short smoke-test training pass.",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help="Optional step limit for smoke tests.",
    )
    return parser


def _ensure_clean_dir(path: Path, *, overwrite: bool) -> Path:
    if path.exists():
        if not overwrite:
            raise FileExistsError(
                f"{path} already exists. Use --overwrite to delete and recreate."
            )
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def plan_final_experiment(
    *,
    stage3_best_path: Path,
    final_dir: Path,
    overwrite: bool,
) -> Path:
    with stage3_best_path.open(encoding="utf-8") as handle:
        stage3_best = yaml.safe_load(handle)

    full_config = stage3_best["full_config"]
    fixed = FixedHyperparameters(**full_config["fixed"])
    reproducibility = ReproducibilityInfo(**full_config["reproducibility"])
    searchable_raw = full_config["searchable"]

    searchable = SearchableHyperparameters(
        lora_r=int(searchable_raw["lora_r"]),
        learning_rate=float(searchable_raw["learning_rate"]),
        num_epochs=int(searchable_raw["num_epochs"]),
        lora_dropout=float(searchable_raw["lora_dropout"]),
        lora_alpha=int(searchable_raw["lora_alpha"]),
    )

    _ensure_clean_dir(final_dir, overwrite=overwrite)
    tracker = ExperimentTracker(final_dir.parent)
    run_id = "run_001"
    run_config = RunConfig(
        stage="final",
        run_id=run_id,
        searchable=searchable,
        fixed=fixed,
        reproducibility=reproducibility,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    plan = ExperimentPlan(
        stage="final",
        run_id=run_id,
        run_index=1,
        config=run_config,
        run_dir=str(tracker.run_dir("final", run_id)),
        search_overrides={"source": "stage3_best"},
        frozen_from={"stage3_best": str(stage3_best_path)},
    )
    tracker.initialize_run(plan)
    return Path(plan.run_dir)


def write_final_best_config(
    *,
    result,
    stage3_best_path: Path,
    final_run_dir: Path,
) -> Path:
    out_path = PROJECT_ROOT / "training" / "best_configs" / "final_best.yaml"
    core = result.metrics.get("core", {})
    payload = {
        "stage": "final",
        "selected_at": datetime.now(timezone.utc).isoformat(),
        "source_stage3_best": str(stage3_best_path),
        "best_run_dir": str(final_run_dir),
        "best_checkpoint": core.get("checkpoint_path"),
        "best_val_loss": core.get("val_loss"),
        "best_train_loss": core.get("train_loss"),
        "hyperparameters": yaml.safe_load(stage3_best_path.read_text(encoding="utf-8")).get(
            "frozen_for_final_training", {}
        ),
        "full_config": result.config.to_dict(),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return out_path


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    stage3_best_path = args.stage3_best.resolve()
    if not stage3_best_path.exists():
        raise FileNotFoundError(f"Stage3 best config not found: {stage3_best_path}")

    final_run_dir = plan_final_experiment(
        stage3_best_path=stage3_best_path,
        final_dir=args.final_dir.resolve(),
        overwrite=args.overwrite,
    )
    print(f"Planned final experiment at {final_run_dir}")

    if args.plan_only:
        return 0

    result = train_experiment(
        TrainOptions(
            experiment_dir=final_run_dir,
            dry_run=args.dry_run,
            max_steps=args.max_steps,
            system_prompt_path=DEFAULT_SYSTEM_PROMPT_PATH,
        )
    )
    best_config_path = write_final_best_config(
        result=result,
        stage3_best_path=stage3_best_path,
        final_run_dir=final_run_dir,
    )

    summary = {
        "status": result.status,
        "final_run_dir": str(final_run_dir),
        "checkpoint": result.metrics.get("core", {}).get("checkpoint_path"),
        "val_loss": result.metrics.get("core", {}).get("val_loss"),
        "best_config": str(best_config_path),
    }
    summary_path = args.final_dir.resolve() / "final_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if result.status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
