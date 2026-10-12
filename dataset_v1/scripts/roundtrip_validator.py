"""Validate parser → JSON → compiler round-trip for V1 candidates."""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

from compiler.freecad_launcher import find_freecadcmd, run_in_freecad
from compiler.loader import load_cad_json
from parser.document_parser import ParseResult, ParseStatus, parse_fcstd


@dataclass
class RoundTripResult:
    """Outcome of round-trip validation for one model."""

    fcstd_path: Path
    passed: bool
    parse_status: str
    operation_count: int
    unsupported_features: list[str]
    error: str = ""


def is_fully_parsed(result: ParseResult) -> bool:
    """Return True when the parser fully supports every feature in the model."""
    return (
        result.status == ParseStatus.VALID
        and not result.unsupported_features
        and len(result.cad_json.get("operations", [])) > 0
    )


def validate_roundtrip(fcstd_path: Path | str) -> RoundTripResult:
    """Parse, validate JSON, compile, and confirm FreeCAD accepts the result."""
    fcstd_path = Path(fcstd_path)
    try:
        result = parse_fcstd(fcstd_path)
    except Exception as exc:  # noqa: BLE001
        return RoundTripResult(
            fcstd_path=fcstd_path,
            passed=False,
            parse_status="exception",
            operation_count=0,
            unsupported_features=[],
            error=str(exc),
        )

    if not is_fully_parsed(result):
        return RoundTripResult(
            fcstd_path=fcstd_path,
            passed=False,
            parse_status=result.status.value,
            operation_count=len(result.cad_json.get("operations", [])),
            unsupported_features=list(result.unsupported_features),
            error="Not fully parsed or contains unsupported features.",
        )

    try:
        load_cad_json_dict(result.cad_json)
    except ValueError as exc:
        return RoundTripResult(
            fcstd_path=fcstd_path,
            passed=False,
            parse_status=result.status.value,
            operation_count=len(result.cad_json.get("operations", [])),
            unsupported_features=[],
            error=f"JSON validation failed: {exc}",
        )

    if find_freecadcmd() is None:
        return RoundTripResult(
            fcstd_path=fcstd_path,
            passed=False,
            parse_status=result.status.value,
            operation_count=len(result.cad_json.get("operations", [])),
            unsupported_features=[],
            error="FreeCAD command-line executable not found.",
        )

    compile_error = _compile_cad_json(result.cad_json)
    if compile_error:
        return RoundTripResult(
            fcstd_path=fcstd_path,
            passed=False,
            parse_status=result.status.value,
            operation_count=len(result.cad_json.get("operations", [])),
            unsupported_features=[],
            error=compile_error,
        )

    return RoundTripResult(
        fcstd_path=fcstd_path,
        passed=True,
        parse_status=result.status.value,
        operation_count=len(result.cad_json.get("operations", [])),
        unsupported_features=[],
    )


def load_cad_json_dict(data: dict) -> dict:
    """Validate an in-memory CAD JSON document via the compiler loader."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", encoding="utf-8") as handle:
        json.dump(data, handle)
        temp_path = Path(handle.name)
    try:
        return load_cad_json(temp_path)
    finally:
        temp_path.unlink(missing_ok=True)


def _compile_cad_json(cad_json: dict) -> str:
    """Compile CAD JSON to a temporary FCStd. Return error message or empty string."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", encoding="utf-8") as json_file:
        json.dump(cad_json, json_file)
        json_path = Path(json_file.name)

    output_path = json_path.with_suffix(".FCStd")
    script_path = Path(__file__).resolve().parents[2] / "compiler" / "freecad_main.py"

    try:
        proc = run_in_freecad(
            script_path,
            [str(json_path.resolve()), "-o", str(output_path.resolve())],
        )
    finally:
        json_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        return detail or f"Compilation failed with exit code {proc.returncode}"
    return ""
