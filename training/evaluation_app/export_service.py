"""Export comparison reports and metrics."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from training.evaluation_app.data_loader import EvalExample
from training.evaluation_app.metrics import aggregate_metrics


def build_markdown_report(examples: list[EvalExample], aggregate: dict[str, Any]) -> str:
    now = datetime.now(timezone.utc).isoformat()
    lines = [
        "# CAD Copilot Evaluation Report",
        "",
        f"Generated: {now}",
        "",
        "## Dataset Metrics",
        "",
        f"- Examples: {aggregate.get('count', 0)}",
        f"- JSON validity: {aggregate.get('json_validity_rate', 0):.1%}",
        f"- Schema validity: {aggregate.get('schema_validity_rate', 0):.1%}",
    ]
    compile_rate = aggregate.get("compilation_success_rate")
    if compile_rate is not None:
        lines.append(f"- Compilation success: {compile_rate:.1%}")
    lines.extend(
        [
            f"- Operation precision: {_fmt(aggregate.get('operation_precision'))}",
            f"- Operation recall: {_fmt(aggregate.get('operation_recall'))}",
            f"- Operation F1: {_fmt(aggregate.get('operation_f1'))}",
            f"- Operation-type accuracy: {_fmt(aggregate.get('operation_type_accuracy'))}",
            f"- Exact match rate: {aggregate.get('exact_match_rate', 0):.1%}",
            "",
            "## Error Categories",
            "",
        ]
    )
    for label, count in aggregate.get("error_counts", {}).items():
        if count:
            lines.append(f"- {label}: {count}")

    lines.extend(["", "## Per-example", "", "| Model | Prompt | Op F1 | Exact | Errors |", "|---|---|---:|---:|---|"])
    for example in examples:
        errors = ", ".join(example.analysis.error_labels) or "—"
        lines.append(
            f"| {example.model_id} | {example.prompt[:60]} | "
            f"{_fmt(example.analysis.metrics.f1)} | "
            f"{'yes' if example.analysis.metrics.exact_match else 'no'} | {errors} |"
        )
    return "\n".join(lines) + "\n"


def export_json_metrics(examples: list[EvalExample], aggregate: dict[str, Any]) -> dict[str, Any]:
    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "aggregate": aggregate,
        "examples": [
            {
                "model_id": ex.model_id,
                "prompt": ex.prompt,
                "json_valid": ex.json_valid,
                "schema_valid": ex.schema_valid,
                "compilation_success": ex.compilation_success,
                "metrics": {
                    "precision": ex.analysis.metrics.precision,
                    "recall": ex.analysis.metrics.recall,
                    "f1": ex.analysis.metrics.f1,
                    "type_accuracy": ex.analysis.metrics.type_accuracy,
                    "exact_match": ex.analysis.metrics.exact_match,
                },
                "error_labels": ex.analysis.error_labels,
            }
            for ex in examples
        ],
    }


def write_exports(
    output_dir: Path,
    examples: list[EvalExample],
    *,
    include_markdown: bool = True,
    include_json: bool = True,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    aggregate = aggregate_metrics([ex.analysis for ex in examples])
    written: dict[str, Path] = {}

    if include_markdown:
        md_path = output_dir / "comparison_report.md"
        md_path.write_text(build_markdown_report(examples, aggregate), encoding="utf-8")
        written["markdown"] = md_path

    if include_json:
        json_path = output_dir / "metrics.json"
        json_path.write_text(
            json.dumps(export_json_metrics(examples, aggregate), indent=2) + "\n",
            encoding="utf-8",
        )
        written["json"] = json_path

    return written


def _fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.1%}"
    return str(value)
