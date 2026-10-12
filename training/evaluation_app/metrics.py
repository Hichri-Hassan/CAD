"""Metrics and error classification for CAD generation evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from training.scripts.evaluate_generation import (
    exact_operations_match,
    operation_type_accuracy,
    validate_training_schema,
)


ERROR_LABELS = (
    "Invalid JSON",
    "Schema error",
    "Compiler failure",
    "Missing operation",
    "Extra operation",
    "Wrong operation type",
    "Wrong parameter",
    "Wrong ordering",
)


@dataclass
class OperationMetrics:
    precision: float | None
    recall: float | None
    f1: float | None
    type_accuracy: float | None
    exact_match: bool
    reference_count: int
    generated_count: int
    reference_types: list[str]
    generated_types: list[str]


@dataclass
class ExampleAnalysis:
    model_id: str
    prompt: str
    json_valid: bool
    schema_valid: bool
    compilation_success: bool | None
    metrics: OperationMetrics
    error_labels: list[str] = field(default_factory=list)
    generation_status: str = "not_generated"


def _operation_types(operations: list[dict[str, Any]] | None) -> list[str]:
    if not operations:
        return []
    return [str(op.get("type", "?")) for op in operations]


def _type_multiset(operations: list[dict[str, Any]] | None) -> dict[str, int]:
    counts: dict[str, int] = {}
    for op_type in _operation_types(operations):
        counts[op_type] = counts.get(op_type, 0) + 1
    return counts


def operation_precision_recall_f1(
    generated: list[dict[str, Any]] | None,
    reference: list[dict[str, Any]],
) -> tuple[float | None, float | None, float | None]:
    if generated is None:
        return None, None, None

    ref_types = _operation_types(reference)
    gen_types = _operation_types(generated)
    if not ref_types and not gen_types:
        return 1.0, 1.0, 1.0
    if not gen_types:
        return 0.0, 0.0, 0.0 if ref_types else 1.0, 1.0, 1.0
    if not ref_types:
        return 0.0, 0.0, 0.0

    ref_counts = _type_multiset(reference)
    gen_counts = _type_multiset(generated)
    true_positive = sum(min(gen_counts.get(t, 0), ref_counts.get(t, 0)) for t in set(ref_counts) | set(gen_counts))
    precision = true_positive / len(gen_types)
    recall = true_positive / len(ref_types)
    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)
    return precision, recall, f1


def classify_errors(
    *,
    json_valid: bool,
    schema_valid: bool,
    compilation_success: bool | None,
    generated: list[dict[str, Any]] | None,
    reference: list[dict[str, Any]],
) -> list[str]:
    labels: list[str] = []
    if not json_valid:
        labels.append("Invalid JSON")
        return labels
    if not schema_valid:
        labels.append("Schema error")
        return labels
    if compilation_success is False:
        labels.append("Compiler failure")

    if generated is None:
        return labels

    ref_types = _operation_types(reference)
    gen_types = _operation_types(generated)
    ref_counts = _type_multiset(reference)
    gen_counts = _type_multiset(generated)

    if len(gen_types) < len(ref_types):
        labels.append("Missing operation")
    if len(gen_types) > len(ref_types):
        labels.append("Extra operation")

    for op_type, ref_n in ref_counts.items():
        gen_n = gen_counts.get(op_type, 0)
        if gen_n < ref_n:
            if "Missing operation" not in labels:
                labels.append("Missing operation")
        if gen_n > ref_n:
            if "Extra operation" not in labels:
                labels.append("Extra operation")

    positional_mismatch = False
    param_mismatch = False
    for index in range(max(len(reference), len(generated))):
        if index >= len(reference) or index >= len(generated):
            continue
        ref_op = reference[index]
        gen_op = generated[index]
        if ref_op.get("type") != gen_op.get("type"):
            positional_mismatch = True
        elif ref_op != gen_op:
            param_mismatch = True

    if positional_mismatch:
        labels.append("Wrong operation type")
    if param_mismatch:
        labels.append("Wrong parameter")

    if (
        sorted(ref_types) == sorted(gen_types)
        and ref_types != gen_types
        and not positional_mismatch
        and generated != reference
    ):
        labels.append("Wrong ordering")
    elif ref_types != gen_types and not positional_mismatch and not param_mismatch:
        if "Wrong ordering" not in labels and sorted(ref_types) == sorted(gen_types):
            labels.append("Wrong ordering")

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for label in labels:
        if label not in seen:
            seen.add(label)
            unique.append(label)
    return unique


def analyze_example(
    *,
    model_id: str,
    prompt: str,
    reference_ops: list[dict[str, Any]],
    generated_ops: list[dict[str, Any]] | None,
    json_valid: bool,
    schema_valid: bool,
    compilation_success: bool | None,
    generation_status: str = "generated",
) -> ExampleAnalysis:
    precision, recall, f1 = operation_precision_recall_f1(generated_ops, reference_ops)
    metrics = OperationMetrics(
        precision=precision,
        recall=recall,
        f1=f1,
        type_accuracy=operation_type_accuracy(generated_ops, reference_ops),
        exact_match=exact_operations_match(generated_ops, reference_ops),
        reference_count=len(reference_ops),
        generated_count=len(generated_ops) if generated_ops else 0,
        reference_types=_operation_types(reference_ops),
        generated_types=_operation_types(generated_ops),
    )
    error_labels = classify_errors(
        json_valid=json_valid,
        schema_valid=schema_valid,
        compilation_success=compilation_success,
        generated=generated_ops,
        reference=reference_ops,
    )
    return ExampleAnalysis(
        model_id=model_id,
        prompt=prompt,
        json_valid=json_valid,
        schema_valid=schema_valid,
        compilation_success=compilation_success,
        metrics=metrics,
        error_labels=error_labels,
        generation_status=generation_status,
    )


def validate_payload_schema(payload: dict[str, Any] | None) -> bool:
    if payload is None:
        return False
    return validate_training_schema(payload)


def aggregate_metrics(analyses: list[ExampleAnalysis]) -> dict[str, Any]:
    if not analyses:
        return {}

    n = len(analyses)
    json_rate = sum(1 for a in analyses if a.json_valid) / n
    schema_rate = sum(1 for a in analyses if a.schema_valid) / n
    exact_rate = sum(1 for a in analyses if a.metrics.exact_match) / n

    compile_items = [a.compilation_success for a in analyses if a.compilation_success is not None]
    compile_rate = sum(1 for ok in compile_items if ok) / len(compile_items) if compile_items else None

    def _mean(values: list[float | None]) -> float | None:
        nums = [v for v in values if v is not None]
        return sum(nums) / len(nums) if nums else None

    error_counts: dict[str, int] = {label: 0 for label in ERROR_LABELS}
    for analysis in analyses:
        for label in analysis.error_labels:
            error_counts[label] = error_counts.get(label, 0) + 1

    return {
        "count": n,
        "json_validity_rate": json_rate,
        "schema_validity_rate": schema_rate,
        "compilation_success_rate": compile_rate,
        "operation_precision": _mean([a.metrics.precision for a in analyses]),
        "operation_recall": _mean([a.metrics.recall for a in analyses]),
        "operation_f1": _mean([a.metrics.f1 for a in analyses]),
        "operation_type_accuracy": _mean([a.metrics.type_accuracy for a in analyses]),
        "exact_match_rate": exact_rate,
        "error_counts": error_counts,
    }
