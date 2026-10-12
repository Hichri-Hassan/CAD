#!/usr/bin/env python3
"""Generate Stage 2 epoch-search report and best-configuration artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from training.hpo.metrics import ExperimentMetrics
from training.hpo.tracking import ExperimentTracker


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Report Stage 2 epoch-only HPO results.")
    parser.add_argument(
        "--stage2-dir",
        type=Path,
        default=PROJECT_ROOT / "training" / "experiments" / "stage2",
        help="Stage 2 experiment directory.",
    )
    parser.add_argument(
        "--stage2-report",
        type=Path,
        default=None,
        help="Optional output path for stage2_report.md",
    )
    return parser


def _read_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _fmt(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.4f}"


def _discover_runs(stage2_dir: Path) -> list[Path]:
    return sorted(p for p in stage2_dir.glob("run_*") if p.is_dir())


def collect_results(stage2_dir: Path, tracker: ExperimentTracker) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for result in tracker.list_stage_results("stage2"):
        cfg = result.config
        core = ExperimentMetrics.from_dict(result.metrics).core
        rows.append(
            {
                "experiment": f"{result.stage}/{result.run_id}",
                "run_id": result.run_id,
                "epochs": cfg.searchable.num_epochs,
                "lora_r": cfg.searchable.lora_r,
                "learning_rate": cfg.searchable.learning_rate,
                "lora_dropout": cfg.searchable.lora_dropout,
                "lora_alpha": cfg.searchable.lora_alpha,
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
    best_status: str,
    stage2_dir: Path,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    config_yaml_path = Path(best_row["run_dir"]) / "config.yaml"
    full_config = _read_yaml(config_yaml_path)

    payload = {
        "stage": "stage2",
        "selected_at": datetime.now(timezone.utc).isoformat(),
        "selection_metric": "val_loss",
        "selection_direction": "min",
        "best_experiment": best_row["experiment"],
        "best_run_dir": best_row["run_dir"],
        "best_checkpoint": best_row["checkpoint_path"],
        "best_val_loss": best_row["val_loss"],
        "best_train_loss": best_row["train_loss"],
        "frozen_for_final_training": {
            "num_epochs": best_row["epochs"],
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
        "status": best_status,
        "artifacts_dir": str(stage2_dir),
    }

    out_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def plot_losses(stage2_dir: Path, rows: list[dict[str, Any]], best_experiment: str) -> None:
    completed = [r for r in rows if r["status"] == "completed" and r["val_loss"] is not None]
    if not completed:
        return

    xs = sorted({r["epochs"] for r in completed})
    train_by_epoch = {r["epochs"]: r["train_loss"] for r in completed}
    val_by_epoch = {r["epochs"]: r["val_loss"] for r in completed}

    # Train loss vs epochs
    plt.figure()
    plt.plot(xs, [train_by_epoch.get(x) for x in xs], marker="o", label="train")
    plt.xlabel("epochs")
    plt.ylabel("train loss")
    plt.title("Training loss vs epochs (Stage 2)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(stage2_dir / "plot_train_loss_vs_epochs.png")
    plt.close()

    # Val loss vs epochs
    plt.figure()
    plt.plot(xs, [val_by_epoch.get(x) for x in xs], marker="o", label="val")
    plt.xlabel("epochs")
    plt.ylabel("validation loss")
    plt.title("Validation loss vs epochs (Stage 2)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(stage2_dir / "plot_val_loss_vs_epochs.png")
    plt.close()

    # Train vs val
    plt.figure()
    plt.plot(xs, [train_by_epoch.get(x) for x in xs], marker="o", label="train")
    plt.plot(xs, [val_by_epoch.get(x) for x in xs], marker="o", label="val")
    plt.xlabel("epochs")
    plt.ylabel("loss")
    plt.title("Train vs validation loss (Stage 2)")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(stage2_dir / "plot_train_vs_val_loss.png")
    plt.close()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    stage2_dir = args.stage2_dir.resolve()
    if not stage2_dir.exists():
        raise FileNotFoundError(f"Stage2 dir not found: {stage2_dir}")

    tracker = ExperimentTracker(stage2_dir.parent)
    rows = collect_results(stage2_dir, tracker)

    if not rows:
        raise RuntimeError(f"No stage2 runs found in {stage2_dir}")

    completed = [r for r in rows if r["status"] == "completed" and r["val_loss"] is not None]
    failed = [r for r in rows if r["status"] != "completed"]

    if not completed:
        raise RuntimeError("No completed stage2 runs with validation loss available.")

    completed.sort(key=lambda r: r["val_loss"])
    best_row = completed[0]
    best_experiment = best_row["experiment"]

    plot_losses(stage2_dir, rows, best_experiment=best_experiment)

    report_path = (
        args.stage2_report
        or stage2_dir / "stage2_report.md"
    )

    # Comparison table
    ordered = completed + [r for r in failed if r not in completed]
    lines: list[str] = [
        "# STAGE2 HPO Report (Epoch Search)",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Comparison Table",
        "",
        "| Experiment | Epochs | LoRA r | LR | Train Loss | Val Loss | Time (s) | Trainable Params | Status |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in ordered:
        lines.append(
            f"| {r['experiment']} | {r['epochs']} | {r['lora_r']} | {r['learning_rate']:.0e} | "
            f"{_fmt(r['train_loss'])} | {_fmt(r['val_loss'])} | "
            f"{r['training_time_seconds'] if r['training_time_seconds'] is not None else '—'} | "
            f"{r['trainable_parameters'] if r['trainable_parameters'] is not None else '—'} | "
            f"{r['status']} |"
        )

    # Best config explanation
    lines.extend(
        [
            "",
            "## Best Configuration",
            "",
            f"- **Experiment:** `{best_row['experiment']}`",
            f"- **Epochs:** {best_row['epochs']}",
            f"- **LoRA r:** {best_row['lora_r']}",
            f"- **Learning rate:** {best_row['learning_rate']}",
            f"- **LoRA alpha:** {best_row['lora_alpha']}",
            f"- **LoRA dropout:** {best_row['lora_dropout']}",
            f"- **Validation loss:** {_fmt(best_row['val_loss'])}",
            f"- **Checkpoint:** `{best_row['checkpoint_path']}`",
            "",
            "Selected because it achieved the lowest validation loss among all completed Stage 2 runs.",
        ]
    )

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    best_config_path = PROJECT_ROOT / "training" / "best_configs" / "stage2_best.yaml"
    write_best_config(
        out_path=best_config_path,
        best_row=best_row,
        best_status=best_row["status"],
        stage2_dir=stage2_dir,
    )

    summary_payload = {
        "stage": "stage2",
        "total_runs": len(rows),
        "completed": len(completed),
        "failed": len(failed),
        "report": str(report_path),
        "best_config": str(best_config_path),
        "best_experiment": best_experiment,
        "best_val_loss": best_row["val_loss"],
        "best_train_loss": best_row["train_loss"],
    }

    summary_path = PROJECT_ROOT / "training" / "best_configs" / "stage2_summary.json"
    summary_path.write_text(json.dumps(summary_payload, indent=2) + "\n", encoding="utf-8")

    # Concise console output
    print(json.dumps(summary_payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

