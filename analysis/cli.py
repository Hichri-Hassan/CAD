"""CLI for dataset analysis."""

from __future__ import annotations

import argparse
from pathlib import Path

from analysis.forensics.runner import run_forensic_analysis


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="analysis",
        description="Analyze a collection of FreeCAD .FCStd models and generate dataset statistics.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Run statistical dataset analysis (operations, sketches, parameters).",
    )
    _add_common_args(analyze_parser)

    classify_parser = subparsers.add_parser(
        "classify",
        help="Forensic document classification and parser failure analysis.",
    )
    _add_common_args(classify_parser)

    return parser


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--examples",
        type=Path,
        default=Path("examples"),
        help="Directory containing extracted .FCStd models (default: examples/).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("analysis/output"),
        help="Output directory for reports and figures (default: analysis/output/).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Analyze only the first N models (useful for testing).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output.",
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "analyze":
        from analysis.runner import run_analysis

        run_analysis(
            examples_dir=args.examples,
            output_dir=args.output,
            limit=args.limit,
            progress=not args.quiet,
        )
    elif args.command == "classify":
        run_forensic_analysis(
            examples_dir=args.examples,
            output_dir=args.output,
            limit=args.limit,
            progress=not args.quiet,
        )
    else:
        parser.error(f"Unknown command: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
