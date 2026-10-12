"""Orchestrate dataset analysis over a collection of FCStd models."""

from __future__ import annotations

import csv
from pathlib import Path

from analysis.aggregator import aggregate_dataset
from analysis.exporters import export_all_csv
from analysis.model_analyzer import analyze_model
from analysis.models import ModelStats
from analysis.report import generate_summary_report
from analysis.visualizer import generate_all_figures


def load_index_metadata(examples_dir: Path) -> dict[str, dict[str, str]]:
    """Load dataset index.csv metadata keyed by copied filename."""
    index_path = examples_dir / "index.csv"
    if not index_path.exists():
        return {}

    metadata: dict[str, dict[str, str]] = {}
    with index_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            copied = row.get("copied_filename", "")
            if not copied:
                continue
            if copied not in metadata or row.get("is_canonical", "true") == "true":
                metadata[copied] = {
                    "dataset_id": row.get("id", ""),
                    "repository": row.get("repository_name", ""),
                    "original_relative_path": row.get("original_relative_path", ""),
                    "original_filename": row.get("original_filename", ""),
                }
    return metadata


def discover_models(examples_dir: Path) -> list[Path]:
    """Find all FCStd models in the examples directory."""
    return sorted(examples_dir.glob("*.FCStd"))


def run_analysis(
    examples_dir: Path | str,
    output_dir: Path | str,
    *,
    limit: int | None = None,
    progress: bool = True,
) -> None:
    """Analyze all models in examples_dir and write outputs to output_dir."""
    examples_dir = Path(examples_dir).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    model_paths = discover_models(examples_dir)
    if limit is not None:
        model_paths = model_paths[:limit]

    if not model_paths:
        raise FileNotFoundError(f"No .FCStd files found in {examples_dir}")

    index_meta = load_index_metadata(examples_dir)
    models: list[ModelStats] = []
    total = len(model_paths)

    if progress:
        print(f"Analyzing {total} models from {examples_dir}")

    for index, path in enumerate(model_paths, start=1):
        meta = index_meta.get(path.name, {})
        model_stats = analyze_model(
            path,
            dataset_id=meta.get("dataset_id", ""),
            repository=meta.get("repository", ""),
            original_relative_path=meta.get("original_relative_path", ""),
        )
        models.append(model_stats)

        if progress and (index == 1 or index % 100 == 0 or index == total):
            print(f"  Progress: {index}/{total}", flush=True)

    if progress:
        print("Aggregating dataset statistics...")

    dataset = aggregate_dataset(models)

    if progress:
        print("Writing CSV outputs...")

    export_all_csv(output_dir, dataset)

    if progress:
        print("Generating figures...")

    figures = generate_all_figures(output_dir, dataset)
    figure_names = [fig.name for fig in figures]

    if progress:
        print("Writing summary report...")

    report_path = generate_summary_report(output_dir, dataset, figure_names)

    if progress:
        print("----------------------------------------")
        print(f"Models analyzed     : {dataset.total_models}")
        print(f"Successfully parsed : {dataset.successfully_parsed}")
        print(f"Partially parsed    : {dataset.partially_parsed}")
        print(f"Parser failures     : {dataset.parser_failures}")
        print(f"Corrupted files     : {dataset.corrupted_files}")
        print(f"Output directory    : {output_dir}")
        print(f"Summary report      : {report_path}")
        print("----------------------------------------")
