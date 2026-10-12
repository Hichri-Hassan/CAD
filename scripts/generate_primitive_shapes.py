#!/usr/bin/env python3
"""Generate primitive FreeCAD shapes for dataset augmentation or testing.

Run inside FreeCAD (headless or GUI):

    FreeCADCmd scripts/generate_primitive_shapes.py --output-dir output/primitives

Or from the project root:

    ./scripts/run_generate_primitives.sh
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from primitive_catalog import DEFAULT_FAMILY_ORDER, PRIMITIVE_FAMILIES, generate_family_shapes


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate primitive FreeCAD shapes with varied dimensions."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/primitives"),
        help="Directory for saved .FCStd files (default: output/primitives).",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=20,
        help="Number of variants per shape family (default: 20).",
    )
    parser.add_argument(
        "--families",
        nargs="+",
        choices=list(PRIMITIVE_FAMILIES.keys()),
        default=None,
        help="Optional subset of primitive families to generate.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    output_dir = args.output_dir.resolve()
    count = max(1, args.count)
    families = args.families or DEFAULT_FAMILY_ORDER

    print(f"Output directory: {output_dir}")
    print(f"Generating {count} variants for: {', '.join(families)}")

    totals: dict[str, int] = {}
    for family_key in families:
        family = PRIMITIVE_FAMILIES[family_key]
        paths = generate_family_shapes(output_dir, family, count)
        totals[family_key] = len(paths)

    total = sum(totals.values())
    print(f"Done. Generated {total} files:")
    for family_key, family_count in totals.items():
        print(f"  {family_key}: {family_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
