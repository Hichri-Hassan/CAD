"""Entry point executed inside the FreeCAD Python environment."""

from __future__ import annotations

import argparse
import os
import sys
import traceback
from pathlib import Path


def _ensure_project_root() -> Path:
    env_root = os.environ.get("CAD_COMPILER_ROOT")
    if env_root:
        root = Path(env_root)
    else:
        root = Path(__file__).resolve().parent.parent
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    return root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile CAD JSON inside FreeCAD.")
    parser.add_argument("input", type=Path, help="Input CAD JSON file")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Output .FCStd path")
    args = parser.parse_args(argv)

    _ensure_project_root()

    try:
        import FreeCAD as App

        from compiler.runner import compile_file

        context = compile_file(str(args.input.resolve()), str(args.output.resolve()))
        print(f"Compiled successfully: {args.output}")
        print(f"Operations: {len(context.objects)}")
        if context.warnings:
            print(f"Warnings: {len(context.warnings)}")
            for warning in context.warnings:
                print(f"  - {warning}")
        App.closeDocument(context.doc.Name)
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Compilation failed: {exc}", file=sys.stderr)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
