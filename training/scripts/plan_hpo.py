#!/usr/bin/env python3
"""Prepare hierarchical HPO experiment directories without starting training."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from training.hpo.optimizer import HierarchicalOptimizer  # noqa: E402
from training.hpo.search_space import load_hpo_defaults, load_stage_definitions  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plan hierarchical LoRA HPO experiments for CAD Copilot V1.",
    )
    parser.add_argument(
        "--stage",
        choices=["all", "stage1", "stage2", "stage3"],
        default="all",
        help="Which optimization stage to prepare (default: all).",
    )
    parser.add_argument(
        "--defaults",
        type=Path,
        default=PROJECT_ROOT / "training" / "configs" / "hpo_defaults.yaml",
        help="Fixed HPO defaults YAML.",
    )
    parser.add_argument(
        "--stages-config",
        type=Path,
        default=PROJECT_ROOT / "training" / "configs" / "hpo_stages.yaml",
        help="Stage search-space YAML.",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Print the search strategy summary without writing experiment directories.",
    )
    return parser


def print_summary(optimizer: HierarchicalOptimizer) -> None:
    summary = optimizer.summary()
    print("Hierarchical HPO strategy")
    print("=========================")
    print(f"Total planned runs : {summary['total_combinations']}")
    print(f"Fixed parameters   : {', '.join(summary['fixed_parameters'])}")
    print()
    for stage in summary["stages"]:
        print(f"{stage['stage_id']} — {stage['name']}")
        print(f"  combinations: {stage['combinations']}")
        print(f"  search      : {stage['search']}")
        if stage["depends_on"]:
            print(f"  depends on  : {stage['depends_on']}")
        print()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    defaults = load_hpo_defaults(args.defaults)
    stages = load_stage_definitions(args.stages_config)
    optimizer = HierarchicalOptimizer(defaults=defaults, stages=stages)

    print_summary(optimizer)
    if args.summary_only:
        return 0

    if args.stage == "all":
        all_plans = optimizer.prepare_experiments()
    else:
        plans = optimizer.plan_stage(args.stage)
        optimizer.tracker.write_stage_manifest(
            args.stage,
            plans,
            stage=next(stage for stage in stages if stage.stage_id == args.stage),
        )
        for plan in plans:
            optimizer.tracker.initialize_run(plan)
        all_plans = {args.stage: plans}

    print("Prepared experiment directories:")
    for stage_id, plans in all_plans.items():
        print(f"  {stage_id}: {len(plans)} runs -> {optimizer.tracker.stage_dir(stage_id)}")
    print(f"Master manifest: {optimizer.tracker.experiments_root / 'hpo_master_manifest.json'}")
    print(json.dumps({"status": "planned", "training": "not_started"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
