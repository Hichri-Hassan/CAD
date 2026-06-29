"""Command-line interface for Parser V0."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from parser.document_parser import ParserMode, parse_fcstd, write_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="CAD Copilot Parser V0 — convert FreeCAD .FCStd files to CAD JSON.",
    )
    parser.add_argument("input", type=Path, help="Path to input .FCStd file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output JSON path (default: <input>.json)",
    )
    parser.add_argument(
        "--mode",
        choices=["strict", "lenient"],
        default="lenient",
        help="Parser mode (default: lenient)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    input_path: Path = args.input
    output_path = args.output or input_path.with_suffix(".json")
    mode = ParserMode.STRICT if args.mode == "strict" else ParserMode.LENIENT

    if not input_path.exists():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        return 1

    result = parse_fcstd(input_path, mode=mode)
    write_json(result, output_path)

    print(f"Status: {result.status.value}")
    print(f"Operations extracted: {len(result.cad_json.get('operations', []))}")
    if result.warnings:
        print(f"Warnings: {len(result.warnings)}")
        for warning in result.warnings:
            print(f"  - {warning}")
    print(f"Output: {output_path}")

    if result.status.value in {"corrupted", "unsupported"} and mode == ParserMode.STRICT:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
