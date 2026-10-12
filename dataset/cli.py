"""CLI for the CAD dataset pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from dataset.extract import extract_repository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dataset",
        description="Stage 1 CAD dataset pipeline: extract .FCStd files from a repository.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract_parser = subparsers.add_parser(
        "extract",
        help="Scan a repository and copy .FCStd files into a flat dataset folder.",
    )
    extract_parser.add_argument(
        "repository",
        type=Path,
        help="Path to the repository root (e.g. FreeCAD-library/).",
    )
    extract_parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("examples"),
        help="Output directory for copied files and index (default: examples/).",
    )
    extract_parser.add_argument(
        "--repository-name",
        type=str,
        default=None,
        help="Repository label stored in the index (default: repository folder name).",
    )
    extract_parser.add_argument(
        "--id-width",
        type=int,
        default=6,
        help="Zero-padded width for dataset IDs (default: 6 -> 000001).",
    )
    extract_parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress messages.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "extract":
        extract_repository(
            repository_path=args.repository,
            output_dir=args.output,
            repository_name=args.repository_name,
            id_width=args.id_width,
            progress=not args.quiet,
        )
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
