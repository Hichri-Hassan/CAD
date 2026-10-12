"""Determine why the current parser succeeds or fails for each document."""

from __future__ import annotations

from parser.document_parser import ParseResult, ParseStatus, parse_fcstd

from analysis.constants import PARSER_SUPPORTED_TYPES
from analysis.forensics.models import DocumentForensics


def attach_parser_status(doc: DocumentForensics, path: str) -> DocumentForensics:
    """Run the existing parser (read-only) and record status."""
    try:
        result: ParseResult = parse_fcstd(path)
    except Exception as exc:  # noqa: BLE001
        doc.parser_status = "exception"
        doc.parser_error = str(exc)
        doc.parse_success = False
        doc.failure_reason = "Parser exception"
        return doc

    doc.parser_status = result.status.value
    doc.parser_error = "; ".join(result.warnings[:5])
    doc.unsupported_features = list(result.unsupported_features)
    operations = result.cad_json.get("operations", [])
    doc.parsed_operation_count = len(operations)
    doc.parse_success = result.status in {ParseStatus.VALID, ParseStatus.PARTIALLY_SUPPORTED} and len(
        operations
    ) > 0

    if doc.parse_success:
        doc.failure_reason = ""
        return doc

    doc.failure_reason = determine_failure_reason(doc, result)
    return doc


def determine_failure_reason(doc: DocumentForensics, result: ParseResult) -> str:
    """Map forensic structure + parser output to a primary failure reason."""
    if doc.read_error:
        return "Corrupted archive"

    if result.status == ParseStatus.CORRUPTED:
        return "Corrupted archive"

    if doc.flags.get("is_empty"):
        return "Empty document"

    if not doc.has_partdesign_body:
        if doc.flags.get("has_app_part") or (
            doc.flags.get("has_assembly_link") and doc.body_count > 1
        ):
            return "Assembly structure"
        if doc.flags.get("has_part_extrusion") or doc.flags.get("has_part_feature"):
            return "Part Workbench instead of PartDesign"
        if doc.flags.get("has_imported_part") and doc.sketch_count == 0:
            return "Imported geometry only"
        if doc.flags.get("has_mesh") and not doc.flags.get("has_part_feature"):
            return "Mesh-only model"
        if doc.flags.get("has_techdraw"):
            return "TechDraw document"
        if doc.flags.get("has_draft"):
            return "Draft document"
        return "No PartDesign Body"

    if doc.body_count > 1:
        return "Multiple PartDesign Bodies"

    if doc.has_partdesign_body and not doc.has_body_named_body:
        return "PartDesign Body not named 'Body'"

    if result.status == ParseStatus.UNSUPPORTED and not result.cad_json.get("operations"):
        unsupported_types = _unsupported_partdesign_types(doc)
        if unsupported_types:
            return "Unsupported PartDesign feature"
        return "Unknown"

    if doc.unsupported_features or result.status == ParseStatus.PARTIALLY_SUPPORTED:
        return "Unsupported PartDesign feature"

    if result.warnings:
        return "Parser exception"

    return "Unknown"


def _unsupported_partdesign_types(doc: DocumentForensics) -> list[str]:
    unsupported: list[str] = []
    for body in doc.bodies:
        for feature_name in body.feature_names:
            for obj in doc.objects:
                if obj.name == feature_name and obj.type_id not in PARSER_SUPPORTED_TYPES:
                    unsupported.append(obj.type_id)
    return unsupported
