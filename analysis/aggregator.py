"""Aggregate per-model statistics into dataset-level metrics."""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict

from parser.document_parser import ParseStatus

from analysis.models import DatasetStats, ModelStats


def _percentile(values: list[float | int], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * pct / 100.0
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _update_cooccurrence(sequence: list[str], matrix: dict[str, int]) -> None:
    for left, right in zip(sequence, sequence[1:]):
        key = f"{left} -> {right}"
        matrix[key] = matrix.get(key, 0) + 1


def _update_feature_chains(sequence: list[str], chains: dict[str, int], max_length: int = 4) -> None:
    for length in range(2, max_length + 1):
        for start in range(0, len(sequence) - length + 1):
            chain = " -> ".join(sequence[start : start + length])
            chains[chain] = chains.get(chain, 0) + 1


def aggregate_dataset(models: list[ModelStats]) -> DatasetStats:
    """Combine per-model records into dataset-wide statistics."""
    dataset = DatasetStats(total_models=len(models), model_stats=models)

    for model in models:
        dataset.file_sizes.append(model.file_size_bytes)
        dataset.operations_per_model.append(model.feature_tree_depth)
        dataset.sketches_per_model.append(model.sketch_count)
        dataset.feature_tree_depths.append(model.feature_tree_depth)
        dataset.feature_sequence_lengths.append(len(model.feature_sequence))

        if model.parse_status == ParseStatus.CORRUPTED.value:
            dataset.corrupted_files += 1
            dataset.parser_failures += 1
            dataset.parser_failures_detail.append(
                {
                    "filename": model.filename,
                    "dataset_id": model.dataset_id,
                    "status": model.parse_status,
                    "error": model.parser_error,
                    "unsupported_features": "; ".join(model.unsupported_features),
                }
            )
            continue

        if model.parse_status == ParseStatus.UNSUPPORTED.value or not model.parse_success:
            dataset.unsupported_models += 1
            if model.parse_status not in {ParseStatus.CORRUPTED.value, ParseStatus.VALID.value}:
                dataset.parser_failures += 1
                dataset.parser_failures_detail.append(
                    {
                        "filename": model.filename,
                        "dataset_id": model.dataset_id,
                        "status": model.parse_status,
                        "error": model.parser_error,
                        "unsupported_features": "; ".join(model.unsupported_features),
                    }
                )

        if model.parse_status == ParseStatus.VALID.value:
            dataset.successfully_parsed += 1
        elif model.parse_status == ParseStatus.PARTIALLY_SUPPORTED.value:
            dataset.partially_parsed += 1
            dataset.successfully_parsed += 1
        elif model.parse_success:
            dataset.successfully_parsed += 1

        for label, count in model.operation_counts.items():
            dataset.operation_counts[label] = dataset.operation_counts.get(label, 0) + count

        for label, count in model.unsupported_operation_counts.items():
            dataset.unsupported_operation_counts[label] = (
                dataset.unsupported_operation_counts.get(label, 0) + count
            )

        for sketch in model.sketches:
            for label, count in sketch.geometry_counts.items():
                dataset.geometry_counts[label] = dataset.geometry_counts.get(label, 0) + count
            for label, count in sketch.constraint_counts.items():
                dataset.constraint_counts[label] = dataset.constraint_counts.get(label, 0) + count
            dataset.construction_geometry_count += sketch.construction_count

        for param_name, values in model.parameters.items():
            dataset.parameters.setdefault(param_name, []).extend(values)

        if model.feature_sequence:
            _update_cooccurrence(model.feature_sequence, dataset.operation_cooccurrence)
            _update_feature_chains(model.feature_sequence, dataset.feature_chain_counts)

    return dataset


def distribution_percentages(counts: dict[str, int]) -> dict[str, float]:
    """Convert count dict to percentage distribution."""
    total = sum(counts.values())
    if total == 0:
        return {}
    return {key: (value / total) * 100.0 for key, value in sorted(counts.items(), key=lambda x: -x[1])}


def numeric_summary(values: list[int]) -> dict[str, float]:
    """Compute basic descriptive statistics."""
    if not values:
        return {"count": 0, "mean": 0.0, "median": 0.0, "min": 0.0, "max": 0.0, "p90": 0.0}
    return {
        "count": len(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "min": float(min(values)),
        "max": float(max(values)),
        "p90": _percentile(values, 90),
    }


def top_items(counter: dict[str, int], limit: int = 15) -> list[tuple[str, int]]:
    """Return the most frequent items."""
    return Counter(counter).most_common(limit)
