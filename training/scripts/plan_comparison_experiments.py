#!/usr/bin/env python3
"""Plan baseline vs primitives LoRA comparison experiments."""

from __future__ import annotations

import argparse
import json
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


COMPARISON_EXPERIMENTS = {
    "baseline_lora": {
        "dataset_path": "dataset_v1/train/comparison/baseline_training_data.jsonl",
        "dataset_version": "baseline_cad_v1_200",
        "description": "Fresh LoRA trained only on the original CAD dataset.",
    },
    "primitives_lora": {
        "dataset_path": "dataset_v1/train/comparison/merged_training_data.jsonl",
        "dataset_version": "cad_v1_plus_primitives_700",
        "description": "Fresh LoRA trained on original CAD dataset plus primitive dataset.",
    },
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan comparison LoRA experiments.")
    parser.add_argument(
        "--best-config",
        type=Path,
        default=PROJECT_ROOT / "training" / "best_configs" / "final_best.yaml",
        help="Source hyperparameter config from final HPO.",
    )
    parser.add_argument(
        "--split-manifest",
        type=Path,
        default=PROJECT_ROOT / "dataset_v1" / "train" / "comparison" / "comparison_split_manifest.json",
        help="Geometry-aware split manifest shared by both experiments.",
    )
    parser.add_argument(
        "--experiments-root",
        type=Path,
        default=PROJECT_ROOT / "training" / "experiments",
        help="Root directory for experiment folders.",
    )
    parser.add_argument(
        "--experiment",
        choices=["baseline_lora", "primitives_lora", "both"],
        default="both",
        help="Which experiment directories to create.",
    )
    parser.add_argument(
        "--run-id",
        default="run_001",
        help="Run identifier inside each experiment stage directory.",
    )
    return parser


def _load_best_config(path: Path) -> dict:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload["full_config"]


def plan_experiment(
    *,
    stage: str,
    run_id: str,
    full_config: dict,
    dataset_path: str,
    dataset_version: str,
    split_manifest_path: Path,
    experiments_root: Path,
    description: str,
) -> Path:
    searchable = SearchableHyperparameters(**full_config["searchable"])
    fixed = FixedHyperparameters(**full_config["fixed"])
    reproducibility = ReproducibilityInfo(
        seed=int(full_config["reproducibility"]["seed"]),
        dataset_version=dataset_version,
        dataset_path=dataset_path,
        model_version=full_config["reproducibility"]["model_version"],
        base_config=full_config["reproducibility"]["base_config"],
        split_manifest_path=split_manifest_path.relative_to(PROJECT_ROOT).as_posix(),
        split_strategy="geometry_aware",
        val_ratio=0.1,
    )
    run_config = RunConfig(
        stage=stage,
        run_id=run_id,
        searchable=searchable,
        fixed=fixed,
        reproducibility=reproducibility,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    tracker = ExperimentTracker(experiments_root)
    run_dir = tracker.run_dir(stage, run_id)
    if run_dir.exists():
        raise FileExistsError(f"Experiment already exists: {run_dir}")

    plan = ExperimentPlan(
        stage=stage,
        run_id=run_id,
        run_index=1,
        config=run_config,
        run_dir=str(run_dir),
        search_overrides={
            "comparison_experiment": True,
            "description": description,
            "train_from_base_model": True,
        },
        frozen_from={
            "final_best": str(PROJECT_ROOT / "training" / "best_configs" / "final_best.yaml"),
            "split_manifest": str(split_manifest_path),
        },
    )
    tracker.initialize_run(plan)
    return run_dir


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    best_config_path = args.best_config.resolve()
    split_manifest_path = args.split_manifest.resolve()
    if not best_config_path.exists():
        raise FileNotFoundError(f"Best config not found: {best_config_path}")
    if not split_manifest_path.exists():
        raise FileNotFoundError(
            f"Split manifest not found: {split_manifest_path}. "
            "Run prepare_comparison_datasets.py first."
        )

    full_config = _load_best_config(best_config_path)
    selected = ["baseline_lora", "primitives_lora"] if args.experiment == "both" else [args.experiment]
    planned: dict[str, str] = {}
    for stage in selected:
        spec = COMPARISON_EXPERIMENTS[stage]
        run_dir = plan_experiment(
            stage=stage,
            run_id=args.run_id,
            full_config=full_config,
            dataset_path=spec["dataset_path"],
            dataset_version=spec["dataset_version"],
            split_manifest_path=split_manifest_path,
            experiments_root=args.experiments_root.resolve(),
            description=spec["description"],
        )
        planned[stage] = str(run_dir)
        print(f"Planned {stage} at {run_dir}")

    manifest_path = args.experiments_root.resolve() / "comparison_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "planned_at": datetime.now(timezone.utc).isoformat(),
                "source_best_config": str(best_config_path),
                "split_manifest": str(split_manifest_path),
                "experiments": planned,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote comparison manifest to {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
