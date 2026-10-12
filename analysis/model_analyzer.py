"""Analyze a single FCStd model."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from parser.document_parser import ParseResult, ParseStatus, parse_fcstd

from analysis.models import ModelStats
from analysis.raw_inspector import inspect_body_features, load_document


def extract_parameters_from_operations(operations: list[dict[str, Any]]) -> dict[str, list[float | str]]:
    """Collect numerical parameter values from parsed CAD JSON operations."""
    params: dict[str, list[float | str]] = {
        "pad_length": [],
        "pocket_depth": [],
        "hole_diameter": [],
        "hole_depth": [],
        "fillet_radius": [],
        "chamfer_distance": [],
    }

    for operation in operations:
        op_type = operation.get("type")
        if op_type == "Pad" and "length" in operation:
            params["pad_length"].append(float(operation["length"]))
        elif op_type == "Pocket" and "depth" in operation:
            value = operation["depth"]
            if isinstance(value, (int, float)):
                params["pocket_depth"].append(float(value))
            else:
                params["pocket_depth"].append(str(value))
        elif op_type == "Hole":
            if "diameter" in operation:
                params["hole_diameter"].append(float(operation["diameter"]))
            if "depth" in operation:
                value = operation["depth"]
                if isinstance(value, (int, float)):
                    params["hole_depth"].append(float(value))
                else:
                    params["hole_depth"].append(str(value))
        elif op_type == "Fillet" and "radius" in operation:
            params["fillet_radius"].append(float(operation["radius"]))
        elif op_type == "Chamfer" and "distance" in operation:
            params["chamfer_distance"].append(float(operation["distance"]))

    return params


def analyze_model(
    path: Path | str,
    *,
    dataset_id: str = "",
    repository: str = "",
    original_relative_path: str = "",
) -> ModelStats:
    """Parse and inspect a single FCStd model."""
    path = Path(path)
    stats = ModelStats(
        filename=path.name,
        dataset_id=dataset_id,
        repository=repository,
        original_relative_path=original_relative_path,
        file_size_bytes=path.stat().st_size if path.exists() else 0,
    )

    try:
        document = load_document(str(path))
    except Exception as exc:  # noqa: BLE001
        stats.parse_status = ParseStatus.CORRUPTED.value
        stats.parser_error = str(exc)
        return stats

    if not document.body_feature_order:
        stats.parse_status = ParseStatus.UNSUPPORTED.value
        stats.parser_error = "No PartDesign Body feature tree found."
        return stats

    body_info = inspect_body_features(document)
    stats.feature_tree_depth = body_info["feature_tree_depth"]
    stats.partdesign_operation_count = body_info["partdesign_operation_count"]
    stats.sketch_count = body_info["sketch_count"]
    stats.operation_counts = body_info["operation_counts"]
    stats.unsupported_operation_counts = body_info["unsupported_operation_counts"]
    stats.feature_sequence = body_info["feature_sequence"]
    stats.sketches = body_info["sketches"]
    stats.total_entities = sum(sk.entity_count for sk in stats.sketches)
    stats.total_constraints = sum(sk.constraint_count for sk in stats.sketches)

    try:
        parse_result: ParseResult = parse_fcstd(path)
    except Exception as exc:  # noqa: BLE001
        stats.parse_status = "error"
        stats.parser_error = str(exc)
        return stats

    stats.parse_status = parse_result.status.value
    stats.unsupported_features = list(parse_result.unsupported_features)
    operations = parse_result.cad_json.get("operations", [])
    stats.parsed_operation_count = len(operations)
    stats.parameters = extract_parameters_from_operations(operations)

    if parse_result.status == ParseStatus.CORRUPTED:
        stats.parser_error = "; ".join(parse_result.warnings) or "Corrupted file"
    elif parse_result.status == ParseStatus.UNSUPPORTED:
        stats.parser_error = "; ".join(parse_result.warnings) or "Unsupported model"
    elif parse_result.warnings:
        stats.parser_error = "; ".join(parse_result.warnings[:3])

    stats.parse_success = parse_result.status in {
        ParseStatus.VALID,
        ParseStatus.PARTIALLY_SUPPORTED,
    } and stats.parsed_operation_count > 0

    return stats
