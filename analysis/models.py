"""Data models for dataset analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SketchStats:
    """Statistics for a single sketch."""

    sketch_name: str
    entity_count: int = 0
    constraint_count: int = 0
    geometry_counts: dict[str, int] = field(default_factory=dict)
    constraint_counts: dict[str, int] = field(default_factory=dict)
    construction_count: int = 0


@dataclass
class ModelStats:
    """Per-model analysis record."""

    filename: str
    dataset_id: str = ""
    repository: str = ""
    original_relative_path: str = ""
    file_size_bytes: int = 0

    parse_status: str = ""
    parse_success: bool = False
    parser_error: str = ""
    unsupported_features: list[str] = field(default_factory=list)

    feature_tree_depth: int = 0
    partdesign_operation_count: int = 0
    sketch_count: int = 0
    parsed_operation_count: int = 0

    operation_counts: dict[str, int] = field(default_factory=dict)
    unsupported_operation_counts: dict[str, int] = field(default_factory=dict)
    feature_sequence: list[str] = field(default_factory=list)

    sketches: list[SketchStats] = field(default_factory=list)
    parameters: dict[str, list[float | str]] = field(default_factory=dict)

    total_entities: int = 0
    total_constraints: int = 0


@dataclass
class DatasetStats:
    """Aggregated dataset-level statistics."""

    total_models: int = 0
    successfully_parsed: int = 0
    partially_parsed: int = 0
    parser_failures: int = 0
    corrupted_files: int = 0
    unsupported_models: int = 0

    file_sizes: list[int] = field(default_factory=list)
    operation_counts: dict[str, int] = field(default_factory=dict)
    unsupported_operation_counts: dict[str, int] = field(default_factory=dict)
    geometry_counts: dict[str, int] = field(default_factory=dict)
    constraint_counts: dict[str, int] = field(default_factory=dict)
    construction_geometry_count: int = 0

    operations_per_model: list[int] = field(default_factory=list)
    sketches_per_model: list[int] = field(default_factory=list)
    feature_tree_depths: list[int] = field(default_factory=list)

    parameters: dict[str, list[float | str]] = field(default_factory=dict)
    parser_failures_detail: list[dict[str, str]] = field(default_factory=list)

    operation_cooccurrence: dict[str, int] = field(default_factory=dict)
    feature_chain_counts: dict[str, int] = field(default_factory=dict)
    feature_sequence_lengths: list[int] = field(default_factory=list)

    model_stats: list[ModelStats] = field(default_factory=list)

    def summary_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable summary snapshot."""
        return {
            "total_models": self.total_models,
            "successfully_parsed": self.successfully_parsed,
            "partially_parsed": self.partially_parsed,
            "parser_failures": self.parser_failures,
            "corrupted_files": self.corrupted_files,
            "unsupported_models": self.unsupported_models,
        }
