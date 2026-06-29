"""Command-line interface for Compiler V0."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from compiler.freecad_launcher import find_freecadcmd, run_in_freecad
from compiler.loader import load_cad_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="CAD Copilot Compiler V0 — convert CAD JSON to FreeCAD .FCStd files.",
    )
    parser.add_argument("input", type=Path, help="Path to input CAD JSON file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output .FCStd path (default: output/<input_stem>.FCStd)",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate JSON without invoking FreeCAD",
    )

    args = parser.parse_args(argv)
    input_path: Path = args.input
    output_path = args.output or Path("output") / f"{input_path.stem}.FCStd"

    if not input_path.exists():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        return 1

    try:
        load_cad_json(input_path)
        print(f"JSON validation: OK ({input_path.name})")
    except ValueError as exc:
        print(f"JSON validation failed: {exc}", file=sys.stderr)
        return 1

    if args.validate_only:
        return 0

    freecadcmd = find_freecadcmd()
    if freecadcmd is None:
        print(
            "Error: FreeCAD command-line executable not found.\n"
            "Install FreeCAD and ensure FreeCADCmd is available, "
            "or set FREECAD_CMD.",
            file=sys.stderr,
        )
        return 2

    script_path = Path(__file__).resolve().parent / "freecad_main.py"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    result = run_in_freecad(
        script_path,
        [
            str(input_path.resolve()),
            "-o",
            str(output_path.resolve()),
        ],
    )

    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)

    if result.returncode != 0:
        print(f"Compilation failed with exit code {result.returncode}", file=sys.stderr)
        return result.returncode

    print(f"Output: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
