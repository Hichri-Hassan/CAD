"""Main FCStd to CAD JSON parser."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from parser.extractors.features import (
    extract_chamfer,
    extract_fillet,
    extract_hole,
    extract_pad,
    extract_pocket,
)
from parser.extractors.sketch import extract_sketch
from parser.fcstd_reader import FCStdDocument, read_fcstd

logger = logging.getLogger(__name__)

PARSER_VERSION = "0.1"

SUPPORTED_TYPES = {
    "Sketcher::SketchObject",
    "PartDesign::Pad",
    "PartDesign::Pocket",
    "PartDesign::Hole",
    "PartDesign::Fillet",
    "PartDesign::Chamfer",
}


class ParseStatus(str, Enum):
    VALID = "valid"
    PARTIALLY_SUPPORTED = "partially_supported"
    UNSUPPORTED = "unsupported"
    CORRUPTED = "corrupted"


class ParserMode(str, Enum):
    STRICT = "strict"
    LENIENT = "lenient"


@dataclass
class ParseResult:
    """Parser output including CAD JSON and diagnostic metadata."""

    status: ParseStatus
    cad_json: dict[str, Any]
    warnings: list[str] = field(default_factory=list)
    unsupported_features: list[str] = field(default_factory=list)


def parse_fcstd(
    path: Path | str,
    mode: ParserMode = ParserMode.LENIENT,
) -> ParseResult:
    """Parse an .FCStd file and return CAD JSON."""
    path = Path(path)
    warnings: list[str] = []
    unsupported: list[str] = []

    try:
        document = read_fcstd(path)
    except (OSError, ValueError, KeyError) as exc:
        logger.exception("Failed to read FCStd file")
        return ParseResult(
            status=ParseStatus.CORRUPTED,
            cad_json=_empty_output(path),
            warnings=[str(exc)],
        )

    if not document.body_feature_order:
        warnings.append("No PartDesign Body feature tree found.")
        return ParseResult(
            status=ParseStatus.UNSUPPORTED,
            cad_json=_build_metadata(document, [], warnings),
            warnings=warnings,
        )

    operations: list[dict[str, Any]] = []
    name_to_op_id: dict[str, str] = {}
    op_counter = 1

    for feature_name in document.body_feature_order:
        fc_type = document.object_types.get(feature_name)
        obj = document.object_data.get(feature_name)
        if fc_type is None or obj is None:
            unsupported.append(feature_name)
            warnings.append(f"Missing object data for feature '{feature_name}'.")
            continue

        if fc_type not in SUPPORTED_TYPES:
            unsupported.append(f"{feature_name} ({fc_type})")
            warnings.append(f"Unsupported feature type: {feature_name} ({fc_type})")
            continue

        op_id = f"op_{op_counter:03d}"
        name_to_op_id[feature_name] = op_id
        op_counter += 1

        try:
            operation = _extract_operation(
                fc_type=fc_type,
                obj=obj,
                op_id=op_id,
                id_map=name_to_op_id,
            )
        except Exception as exc:  # noqa: BLE001 - V0 reports and continues in lenient mode
            msg = f"Failed to extract '{feature_name}': {exc}"
            logger.warning(msg)
            warnings.append(msg)
            unsupported.append(feature_name)
            continue

        operations.append(operation)

    status = _determine_status(operations, unsupported, mode)
    cad_json = _build_metadata(document, operations, warnings, path)

    return ParseResult(
        status=status,
        cad_json=cad_json,
        warnings=warnings,
        unsupported_features=unsupported,
    )


def _extract_operation(
    fc_type: str,
    obj: Any,
    op_id: str,
    id_map: dict[str, str],
) -> dict[str, Any]:
    if fc_type == "Sketcher::SketchObject":
        return extract_sketch(obj, op_id, id_map)
    if fc_type == "PartDesign::Pad":
        return extract_pad(obj, op_id, id_map)
    if fc_type == "PartDesign::Pocket":
        return extract_pocket(obj, op_id, id_map)
    if fc_type == "PartDesign::Hole":
        return extract_hole(obj, op_id, id_map)
    if fc_type == "PartDesign::Fillet":
        return extract_fillet(obj, op_id, id_map)
    if fc_type == "PartDesign::Chamfer":
        return extract_chamfer(obj, op_id, id_map)
    raise ValueError(f"Unsupported type: {fc_type}")


def _determine_status(
    operations: list[dict[str, Any]],
    unsupported: list[str],
    mode: ParserMode,
) -> ParseStatus:
    if not operations:
        return ParseStatus.UNSUPPORTED
    if unsupported:
        if mode == ParserMode.STRICT:
            return ParseStatus.UNSUPPORTED
        return ParseStatus.PARTIALLY_SUPPORTED
    return ParseStatus.VALID


def _build_metadata(
    document: FCStdDocument,
    operations: list[dict[str, Any]],
    warnings: list[str],
    source_path: Path | None = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "version": "1.0",
        "unit": document.unit,
        "source_format": "FCStd",
        "parser_version": PARSER_VERSION,
    }
    if source_path is not None:
        metadata["source_path"] = str(source_path)
    if document.label:
        metadata["source_label"] = document.label

    result: dict[str, Any] = {
        "metadata": metadata,
        "operations": operations,
    }
    return result


def _empty_output(path: Path) -> dict[str, Any]:
    return {
        "metadata": {
            "version": "1.0",
            "unit": "mm",
            "source_format": "FCStd",
            "parser_version": PARSER_VERSION,
            "source_path": str(path),
        },
        "operations": [],
    }


def write_json(result: ParseResult, output_path: Path) -> None:
    """Write parse result to a JSON file with stable formatting."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(result.cad_json, handle, indent=2)
        handle.write("\n")
