#!/usr/bin/env python3
"""Generate a Markdown report for a comparison LoRA experiment."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Write a comparison experiment report.")
    parser.add_argument(
        "--experiment-dir",
        type=Path,
        required=True,
        help="Experiment directory, e.g. training/experiments/baseline_lora/run_001",
    )
    parser.add_argument(
        "--dataset-stats",
        type=Path,
        default=PROJECT_ROOT / "dataset_v1" / "train" / "comparison" / "dataset_statistics.json",
        help="Merged dataset statistics JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Report output path (default: <experiment-dir>/experiment_report.md).",
    )
    return parser


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def render_report(
    *,
    experiment_dir: Path,
    dataset_stats: dict,
) -> str:
    config = yaml.safe_load((experiment_dir / "config.yaml").read_text(encoding="utf-8"))
    result = _load_json(experiment_dir / "result.json")
    metrics = result.get("metrics", {}).get("core", {})
    split_info = _load_json(experiment_dir / "dataset" / "split_info.json")
    manifest = _load_json(experiment_dir / "manifest.json")

    searchable = config.get("searchable", {})
    fixed = config.get("fixed", {})
    reproducibility = config.get("reproducibility", {})

    lines = [
        f"# {config.get('stage')} Experiment Report",
        "",
        manifest.get("search_overrides", {}).get("description", ""),
        "",
        "## Dataset",
        "",
        f"- **Dataset path:** `{reproducibility.get('dataset_path')}`",
        f"- **Dataset version:** `{reproducibility.get('dataset_version')}`",
        f"- **Split strategy:** `{reproducibility.get('split_strategy', 'random')}`",
        f"- **Validation ratio:** `{reproducibility.get('val_ratio', 0.1)}`",
        f"- **Split manifest:** `{reproducibility.get('split_manifest_path', 'n/a')}`",
        f"- **Train examples:** {split_info.get('train_examples', 'n/a')}",
        f"- **Validation examples:** {split_info.get('val_examples', 'n/a')}",
        "",
        "### Global dataset statistics",
        "",
        f"- Baseline CAD examples: {dataset_stats.get('baseline_examples', 'n/a')}",
        f"- Primitive examples: {dataset_stats.get('primitive_examples', 'n/a')}",
        f"- Merged examples: {dataset_stats.get('merged_examples', 'n/a')}",
        f"- Duplicates removed during merge: {dataset_stats.get('duplicates_removed', 'n/a')}",
        "",
        "## Hyperparameters",
        "",
        "| Parameter | Value |",
        "|---|---|",
        f"| Base model | `{reproducibility.get('model_version')}` |",
        f"| LoRA rank | {searchable.get('lora_r')} |",
        f"| LoRA alpha | {searchable.get('lora_alpha')} |",
        f"| LoRA dropout | {searchable.get('lora_dropout')} |",
        f"| Learning rate | {searchable.get('learning_rate')} |",
        f"| Epochs | {searchable.get('num_epochs')} |",
        f"| Optimizer | {fixed.get('optimizer')} |",
        f"| Scheduler | {fixed.get('scheduler')} |",
        f"| Warmup ratio | {fixed.get('warmup_ratio')} |",
        f"| Weight decay | {fixed.get('weight_decay')} |",
        f"| Train batch size | {fixed.get('per_device_train_batch_size')} |",
        f"| Eval batch size | {fixed.get('per_device_eval_batch_size')} |",
        f"| Gradient accumulation | {fixed.get('gradient_accumulation_steps')} |",
        f"| Max sequence length | {fixed.get('max_seq_length')} |",
        f"| Random seed | {reproducibility.get('seed')} |",
        "",
        "## Training results",
        "",
        f"- **Status:** {result.get('status', 'unknown')}",
        f"- **Completed at:** {result.get('completed_at', 'n/a')}",
        f"- **Final train loss:** {metrics.get('train_loss', 'n/a')}",
        f"- **Final validation loss:** {metrics.get('val_loss', 'n/a')}",
        f"- **Training time (s):** {metrics.get('training_time_seconds', 'n/a')}",
        f"- **Trainable parameters:** {metrics.get('trainable_parameters', 'n/a')}",
        f"- **Adapter checkpoint:** `{metrics.get('checkpoint_path', 'n/a')}`",
        "",
        "## Artifacts",
        "",
        f"- Config: `{experiment_dir / 'config.yaml'}`",
        f"- Result JSON: `{experiment_dir / 'result.json'}`",
        f"- Train loss curve: `{experiment_dir / 'curves' / 'train_loss.json'}`",
        f"- Validation loss curve: `{experiment_dir / 'curves' / 'eval_loss.json'}`",
        f"- TensorBoard logs: `{experiment_dir / 'logs'}`",
        f"- Dataset split info: `{experiment_dir / 'dataset' / 'split_info.json'}`",
        "",
        "## Evaluation",
        "",
        "Compare against the previous adapter with:",
        "",
        "```bash",
        "python3 training/scripts/evaluate_generation.py \\",
        f"  --adapter {experiment_dir / 'checkpoints' / 'adapter'}",
        "```",
        "",
        "Previous production adapter:",
        "",
        "```bash",
        "python3 training/scripts/evaluate_generation.py \\",
        "  --adapter training/experiments/final/run_001/checkpoints/adapter",
        "```",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    experiment_dir = args.experiment_dir.resolve()
    if not experiment_dir.exists():
        raise FileNotFoundError(f"Experiment directory not found: {experiment_dir}")

    dataset_stats = _load_json(args.dataset_stats.resolve())
    report = render_report(experiment_dir=experiment_dir, dataset_stats=dataset_stats)
    output_path = args.output or (experiment_dir / "experiment_report.md")
    output_path.write_text(report, encoding="utf-8")
    print(f"Wrote report to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
