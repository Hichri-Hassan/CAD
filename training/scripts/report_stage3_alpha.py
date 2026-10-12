#!/usr/bin/env python3
"""Generate Stage 3 alpha-search report and best-configuration artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from training.hpo.metrics import ExperimentMetrics
from training.hpo.tracking import ExperimentTracker


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Report Stage 3 alpha-only HPO results.")
    parser.add_argument(
        "--stage3-dir",
        type=Path,
        default=PROJECT_ROOT / "training" / "experiments" / "stage3",
        help="Stage 3 experiment directory.",
    )
    parser.add_argument(
        "--stage3-report",
        type=Path,
        default=None,
        help="Optional output path for stage3_report.md",
    )
    return parser


def _fmt(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.4f}"


def collect_results(stage3_dir: Path, tracker: ExperimentTracker) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in tracker.list_stage_results("stage3"):
        cfg = result.config
        core = ExperimentMetrics.from_dict(result.metrics).core
        rows.append(
            {
                "experiment": f"{result.stage}/{result.run_id}",
                "run_id": result.run_id,
                "lora_alpha": cfg.searchable.lora_alpha,
                "lora_r": cfg.searchable.lora_r,
                "learning_rate": cfg.searchable.learning_rate,
                "num_epochs": cfg.searchable.num_epochs,
                "lora_dropout": cfg.searchable.lora_dropout,
                "train_loss": core.train_loss,
                "val_loss": core.val_loss,
                "training_time_seconds": core.training_time_seconds,
                "trainable_parameters": core.trainable_parameters,
                "checkpoint_path": core.checkpoint_path,
                "status": result.status,
                "run_dir": result.run_dir,
            }
        )
    return rows


def write_best_config(
    *,
    out_path: Path,
    best_row: dict[str, Any],
    stage3_dir: Path,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    config_yaml_path = Path(best_row["run_dir"]) / "config.yaml"
    full_config = yaml.safe_load(config_yaml_path.read_text(encoding="utf-8"))

    payload = {
        "stage": "stage3",
        "selected_at": datetime.now(timezone.utc).isoformat(),
        "selection_metric": "val_loss",
        "selection_direction": "min",
        "best_experiment": best_row["experiment"],
        "best_run_dir": best_row["run_dir"],
        "best_checkpoint": best_row["checkpoint_path"],
        "best_val_loss": best_row["val_loss"],
        "best_train_loss": best_row["train_loss"],
        "frozen_for_final_training": {
            "num_epochs": best_row["num_epochs"],
            "lora_r": best_row["lora_r"],
            "learning_rate": best_row["learning_rate"],
            "lora_alpha": best_row["lora_alpha"],
            "lora_dropout": best_row["lora_dropout"],
            "optimizer": full_config["fixed"]["optimizer"],
            "scheduler": full_config["fixed"]["scheduler"],
            "warmup_ratio": full_config["fixed"]["warmup_ratio"],
            "weight_decay": full_config["fixed"]["weight_decay"],
            "max_seq_length": full_config["fixed"]["max_seq_length"],
            "target_modules": full_config["fixed"]["target_modules"],
            "seed": full_config["reproducibility"]["seed"],
            "dataset_version": full_config["reproducibility"]["dataset_version"],
            "dataset_path": full_config["reproducibility"]["dataset_path"],
            "model_version": full_config["reproducibility"]["model_version"],
        },
        "full_config": full_config,
        "status": best_row["status"],
        "artifacts_dir": str(stage3_dir),
    }

    out_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    stage3_dir = args.stage3_dir.resolve()
    if not stage3_dir.exists():
        raise FileNotFoundError(f"Stage3 dir not found: {stage3_dir}")

    tracker = ExperimentTracker(stage3_dir.parent)
    rows = collect_results(stage3_dir, tracker)

    if not rows:
        raise RuntimeError(f"No stage3 runs found in {stage3_dir}")

    completed = [r for r in rows if r["status"] == "completed" and r["val_loss"] is not None]
    failed = [r for r in rows if r["status"] != "completed"]

    if not completed:
        raise RuntimeError("No completed stage3 runs with validation loss available.")

    completed.sort(key=lambda r: r["val_loss"])
    best_row = completed[0]

    report_path = args.stage3_report or stage3_dir / "stage3_report.md"
    ordered = completed + [r for r in failed if r not in completed]

    lines: list[str] = [
        "# STAGE3 HPO Report (LoRA Alpha Search)",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Comparison Table",
        "",
        "| Experiment | Alpha | LoRA r | LR | Epochs | Train Loss | Val Loss | Time (s) | Status |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in ordered:
        lines.append(
            f"| {r['experiment']} | {r['lora_alpha']} | {r['lora_r']} | {r['learning_rate']:.0e} | "
            f"{r['num_epochs']} | {_fmt(r['train_loss'])} | {_fmt(r['val_loss'])} | "
            f"{r['training_time_seconds'] if r['training_time_seconds'] is not None else '—'} | "
            f"{r['status']} |"
        )

    lines.extend(
        [
            "",
            "## Best Configuration",
            "",
            f"- **Experiment:** `{best_row['experiment']}`",
            f"- **LoRA alpha:** {best_row['lora_alpha']}",
            f"- **LoRA r:** {best_row['lora_r']}",
            f"- **Learning rate:** {best_row['learning_rate']}",
            f"- **Epochs:** {best_row['num_epochs']}",
            f"- **Validation loss:** {_fmt(best_row['val_loss'])}",
            f"- **Checkpoint:** `{best_row['checkpoint_path']}`",
            "",
            "Selected because it achieved the lowest validation loss among all completed Stage 3 runs.",
        ]
    )

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    best_config_path = PROJECT_ROOT / "training" / "best_configs" / "stage3_best.yaml"
    write_best_config(out_path=best_config_path, best_row=best_row, stage3_dir=stage3_dir)

    summary_payload = {
        "stage": "stage3",
        "total_runs": len(rows),
        "completed": len(completed),
        "failed": len(failed),
        "report": str(report_path),
        "best_config": str(best_config_path),
        "best_experiment": best_row["experiment"],
        "best_val_loss": best_row["val_loss"],
        "best_train_loss": best_row["train_loss"],
        "best_lora_alpha": best_row["lora_alpha"],
    }

    summary_path = PROJECT_ROOT / "training" / "best_configs" / "stage3_summary.json"
    summary_path.write_text(json.dumps(summary_payload, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(summary_payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
