#!/usr/bin/env python3
"""Generate stage HPO report and best-configuration artifact."""

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

from training.hpo.metrics import ExperimentMetrics  # noqa: E402
from training.hpo.optimizer import HierarchicalOptimizer  # noqa: E402
from training.hpo.search_space import get_stage_definition, load_hpo_defaults, load_stage_definitions  # noqa: E402
from training.hpo.tracking import ExperimentTracker  # noqa: E402


def collect_rows(stage_id: str, tracker: ExperimentTracker) -> list[dict]:
    rows: list[dict] = []
    for result in tracker.list_stage_results(stage_id):
        metrics = ExperimentMetrics.from_dict(result.metrics)
        core = metrics.core
        rows.append(
            {
                "experiment": f"{result.stage}/{result.run_id}",
                "run_dir": result.run_dir,
                "lora_r": result.config.searchable.lora_r,
                "learning_rate": result.config.searchable.learning_rate,
                "num_epochs": result.config.searchable.num_epochs,
                "lora_dropout": result.config.searchable.lora_dropout,
                "lora_alpha": result.config.searchable.lora_alpha,
                "train_loss": core.train_loss,
                "val_loss": core.val_loss,
                "training_time_seconds": core.training_time_seconds,
                "trainable_parameters": core.trainable_parameters,
                "checkpoint_path": core.checkpoint_path,
                "status": result.status,
            }
        )
    return rows


def sort_rows(rows: list[dict], metric: str = "val_loss") -> list[dict]:
    completed = [row for row in rows if row["status"] == "completed" and row.get(metric) is not None]
    failed = [row for row in rows if row["status"] != "completed" or row.get(metric) is None]
    completed.sort(key=lambda row: row[metric])
    failed.sort(key=lambda row: row["experiment"])
    return completed + failed


def write_markdown_report(
    path: Path,
    stage_id: str,
    rows: list[dict],
    best_row: dict | None,
    selection_reason: str,
) -> None:
    lines = [
        f"# {stage_id.upper()} HPO Report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Comparison Table",
        "",
        "| Experiment | LoRA r | LR | Train Loss | Val Loss | Time (s) | Trainable Params | Status |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]

    for row in rows:
        lines.append(
            f"| {row['experiment']} | {row['lora_r']} | {row['learning_rate']:.0e} | "
            f"{_fmt(row['train_loss'])} | {_fmt(row['val_loss'])} | "
            f"{_fmt(row['training_time_seconds'])} | {_fmt_int(row['trainable_parameters'])} | "
            f"{row['status']} |"
        )

    lines.extend(["", "## Best Configuration", ""])
    if best_row:
        lines.extend(
            [
                f"- **Experiment:** `{best_row['experiment']}`",
                f"- **LoRA rank:** {best_row['lora_r']}",
                f"- **Learning rate:** {best_row['learning_rate']}",
                f"- **Validation loss:** {best_row['val_loss']}",
                f"- **Checkpoint:** `{best_row['checkpoint_path']}`",
                "",
                selection_reason,
            ]
        )
    else:
        lines.append("No completed experiment with validation loss was available.")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_best_config(path: Path, stage_id: str, best_row: dict, best_result) -> None:
    payload = {
        "stage": stage_id,
        "selected_at": datetime.now(timezone.utc).isoformat(),
        "selection_metric": "val_loss",
        "selection_direction": "min",
        "best_experiment": best_row["experiment"],
        "best_run_dir": best_row["run_dir"],
        "best_checkpoint": best_row["checkpoint_path"],
        "best_val_loss": best_row["val_loss"],
        "best_train_loss": best_row["train_loss"],
        "searchable_hyperparameters": {
            "lora_r": best_row["lora_r"],
            "learning_rate": best_row["learning_rate"],
            "num_epochs": best_row["num_epochs"],
            "lora_dropout": best_row["lora_dropout"],
            "lora_alpha": best_row["lora_alpha"],
        },
        "frozen_for_next_stage": {
            "lora_r": best_row["lora_r"],
            "learning_rate": best_row["learning_rate"],
        },
        "full_config": best_result.config.to_dict(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _fmt(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _fmt_int(value) -> str:
    if value is None:
        return "—"
    return f"{value:,}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Report HPO stage results and save best config.")
    parser.add_argument(
        "--stage",
        default="stage1",
        help="Stage identifier (default: stage1).",
    )
    parser.add_argument(
        "--experiments-root",
        type=Path,
        default=PROJECT_ROOT / "training" / "experiments",
        help="Experiments root directory.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Markdown report output path.",
    )
    parser.add_argument(
        "--best-config",
        type=Path,
        default=None,
        help="Best configuration YAML output path.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    stage_id = args.stage
    experiments_root = args.experiments_root.resolve()
    report_path = args.report or experiments_root / stage_id / f"{stage_id}_report.md"
    best_config_path = args.best_config or PROJECT_ROOT / "training" / "best_configs" / f"{stage_id}_best.yaml"

    defaults = load_hpo_defaults()
    stages = load_stage_definitions()
    stage_def = get_stage_definition(stage_id, stages)
    tracker = ExperimentTracker(experiments_root)
    optimizer = HierarchicalOptimizer(defaults=defaults, stages=stages, tracker=tracker)

    rows = collect_rows(stage_id, tracker)
    rows = sort_rows(rows, metric=stage_def.selection_metric)

    results = tracker.list_stage_results(stage_id)
    completed = [result for result in results if result.status == "completed"]

    best_row = None
    best_result = None
    selection_reason = ""

    if completed:
        best_result = optimizer.select_best(stage_id, results, metric=stage_def.selection_metric)
        best_row = next(row for row in rows if row["experiment"] == f"{best_result.stage}/{best_result.run_id}")
        selection_reason = (
            f"Selected because `{best_row['experiment']}` achieved the lowest validation loss "
            f"({best_row['val_loss']:.4f}) among all completed {stage_id} runs using metric "
            f"`{stage_def.selection_metric}`."
        )

    write_markdown_report(report_path, stage_id, rows, best_row, selection_reason)
    if best_row and best_result:
        write_best_config(best_config_path, stage_id, best_row, best_result)

    summary = {
        "stage": stage_id,
        "total_runs": len(rows),
        "completed": sum(1 for row in rows if row["status"] == "completed"),
        "failed": sum(1 for row in rows if row["status"] == "failed"),
        "report": str(report_path),
        "best_config": str(best_config_path) if best_row else None,
        "best_experiment": best_row["experiment"] if best_row else None,
    }
    summary_path = experiments_root / stage_id / f"{stage_id}_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return 0 if summary["failed"] == 0 and summary["completed"] == summary["total_runs"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
