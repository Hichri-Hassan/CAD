#!/usr/bin/env python3
"""Summarize prepared HPO experiments and stage selection readiness."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from training.hpo.metrics import ExperimentMetrics  # noqa: E402
from training.hpo.optimizer import HierarchicalOptimizer  # noqa: E402
from training.hpo.search_space import load_hpo_defaults, load_stage_definitions  # noqa: E402
from training.hpo.tracking import ExperimentTracker  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize hierarchical HPO experiment status.")
    parser.add_argument(
        "--experiments-root",
        type=Path,
        default=PROJECT_ROOT / "training" / "experiments",
        help="Root directory containing prepared HPO experiments.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    defaults = load_hpo_defaults()
    stages = load_stage_definitions()
    tracker = ExperimentTracker(args.experiments_root)
    optimizer = HierarchicalOptimizer(defaults=defaults, stages=stages, tracker=tracker)

    print("HPO experiment status")
    print("=====================")
    for stage in stages:
        results = tracker.list_stage_results(stage.stage_id)
        planned = sum(1 for result in results if result.status == "planned")
        completed = sum(1 for result in results if result.status == "completed")
        print(f"{stage.stage_id}: {len(results)} runs ({completed} completed, {planned} planned)")
        if completed:
            best = optimizer.select_best(stage.stage_id, results)
            metrics = ExperimentMetrics.from_dict(best.metrics)
            print(f"  best run: {best.run_id}")
            print(f"  {stage.selection_metric}: {metrics.selection_value(stage.selection_metric)}")
            print(f"  hyperparameters: {optimizer.best_hyperparameters(best)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
