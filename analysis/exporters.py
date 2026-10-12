"""Export analysis results to CSV files."""

from __future__ import annotations

import csv
from pathlib import Path

from analysis.aggregator import distribution_percentages, numeric_summary, top_items
from analysis.models import DatasetStats, ModelStats


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def export_model_statistics(path: Path, models: list[ModelStats]) -> None:
    fields = [
        "filename",
        "dataset_id",
        "repository",
        "original_relative_path",
        "file_size_bytes",
        "parse_status",
        "parse_success",
        "feature_tree_depth",
        "partdesign_operation_count",
        "sketch_count",
        "parsed_operation_count",
        "total_entities",
        "total_constraints",
        "parser_error",
    ]
    rows = []
    for model in models:
        rows.append(
            {
                "filename": model.filename,
                "dataset_id": model.dataset_id,
                "repository": model.repository,
                "original_relative_path": model.original_relative_path,
                "file_size_bytes": model.file_size_bytes,
                "parse_status": model.parse_status,
                "parse_success": str(model.parse_success).lower(),
                "feature_tree_depth": model.feature_tree_depth,
                "partdesign_operation_count": model.partdesign_operation_count,
                "sketch_count": model.sketch_count,
                "parsed_operation_count": model.parsed_operation_count,
                "total_entities": model.total_entities,
                "total_constraints": model.total_constraints,
                "parser_error": model.parser_error,
            }
        )
    _write_csv(path, fields, rows)


def export_count_distribution(path: Path, counts: dict[str, int], label_field: str) -> None:
    total = sum(counts.values())
    rows = []
    for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        pct = (count / total * 100.0) if total else 0.0
        rows.append({label_field: name, "count": count, "percentage": round(pct, 4)})
    _write_csv(path, [label_field, "count", "percentage"], rows)


def export_parameter_statistics(path: Path, parameters: dict[str, list[float | str]]) -> None:
    rows = []
    for param_name, values in sorted(parameters.items()):
        numeric_values = [float(v) for v in values if isinstance(v, (int, float))]
        categorical = [str(v) for v in values if not isinstance(v, (int, float))]
        summary = numeric_summary([int(v) for v in numeric_values]) if numeric_values else {}
        rows.append(
            {
                "parameter": param_name,
                "count": len(values),
                "numeric_count": len(numeric_values),
                "categorical_count": len(categorical),
                "mean": round(summary.get("mean", 0.0), 4) if numeric_values else "",
                "median": round(summary.get("median", 0.0), 4) if numeric_values else "",
                "min": round(summary.get("min", 0.0), 4) if numeric_values else "",
                "max": round(summary.get("max", 0.0), 4) if numeric_values else "",
                "sample_values": ";".join(str(v) for v in values[:20]),
            }
        )
    _write_csv(
        path,
        [
            "parameter",
            "count",
            "numeric_count",
            "categorical_count",
            "mean",
            "median",
            "min",
            "max",
            "sample_values",
        ],
        rows,
    )


def export_parser_failures(path: Path, dataset: DatasetStats) -> None:
    _write_csv(
        path,
        ["filename", "dataset_id", "status", "error", "unsupported_features"],
        dataset.parser_failures_detail,
    )


def export_dataset_statistics(path: Path, dataset: DatasetStats) -> None:
    file_summary = numeric_summary(dataset.file_sizes)
    op_summary = numeric_summary(dataset.operations_per_model)
    sketch_summary = numeric_summary(dataset.sketches_per_model)
    depth_summary = numeric_summary(dataset.feature_tree_depths)

    rows = [
        {"metric": "total_models", "value": dataset.total_models},
        {"metric": "successfully_parsed", "value": dataset.successfully_parsed},
        {"metric": "partially_parsed", "value": dataset.partially_parsed},
        {"metric": "parser_failures", "value": dataset.parser_failures},
        {"metric": "corrupted_files", "value": dataset.corrupted_files},
        {"metric": "unsupported_models", "value": dataset.unsupported_models},
        {"metric": "avg_file_size_bytes", "value": round(file_summary["mean"], 2)},
        {"metric": "median_file_size_bytes", "value": round(file_summary["median"], 2)},
        {"metric": "min_file_size_bytes", "value": round(file_summary["min"], 2)},
        {"metric": "max_file_size_bytes", "value": round(file_summary["max"], 2)},
        {"metric": "total_operations", "value": sum(dataset.operation_counts.values())},
        {"metric": "avg_operations_per_model", "value": round(op_summary["mean"], 4)},
        {"metric": "median_operations_per_model", "value": round(op_summary["median"], 4)},
        {"metric": "avg_sketches_per_model", "value": round(sketch_summary["mean"], 4)},
        {"metric": "median_sketches_per_model", "value": round(sketch_summary["median"], 4)},
        {"metric": "avg_feature_tree_depth", "value": round(depth_summary["mean"], 4)},
        {"metric": "max_feature_tree_depth", "value": round(depth_summary["max"], 2)},
        {"metric": "total_sketch_entities", "value": sum(dataset.geometry_counts.values())},
        {"metric": "total_sketch_constraints", "value": sum(dataset.constraint_counts.values())},
        {"metric": "construction_geometry_count", "value": dataset.construction_geometry_count},
    ]
    _write_csv(path, ["metric", "value"], rows)


def export_all_csv(output_dir: Path, dataset: DatasetStats) -> None:
    """Write all CSV outputs."""
    export_dataset_statistics(output_dir / "dataset_statistics.csv", dataset)
    export_model_statistics(output_dir / "model_statistics.csv", dataset.model_stats)
    export_count_distribution(
        output_dir / "operation_distribution.csv",
        dataset.operation_counts,
        "operation",
    )
    export_count_distribution(
        output_dir / "geometry_distribution.csv",
        dataset.geometry_counts,
        "geometry_type",
    )
    export_count_distribution(
        output_dir / "constraint_distribution.csv",
        dataset.constraint_counts,
        "constraint_type",
    )
    export_count_distribution(
        output_dir / "unsupported_operations.csv",
        dataset.unsupported_operation_counts,
        "operation",
    )
    export_parameter_statistics(output_dir / "parameter_statistics.csv", dataset.parameters)
    export_parser_failures(output_dir / "parser_failures.csv", dataset)
