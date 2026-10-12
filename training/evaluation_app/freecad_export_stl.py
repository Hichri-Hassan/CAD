"""Headless FreeCAD STL export script (run via FreeCADCmd)."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: freecadcmd export_stl.py <input.FCStd> <output.stl>", file=sys.stderr)
        return 1

    fcstd_path = Path(sys.argv[1]).resolve()
    stl_path = Path(sys.argv[2]).resolve()

    import FreeCAD as App
    import MeshPart

    doc = App.openDocument(str(fcstd_path))
    objects = [
        obj
        for obj in doc.Objects
        if hasattr(obj, "Shape") and obj.Shape and not obj.Shape.isNull()
    ]
    if not objects:
        print("No exportable shapes found", file=sys.stderr)
        App.closeDocument(doc.Name)
        return 1

    mesh = MeshPart.meshFromShape(
        Shape=objects[-1].Shape,
        LinearDeflection=0.1,
        AngularDeflection=0.5,
    )
    mesh.write(str(stl_path))
    App.closeDocument(doc.Name)
    print(f"STL exported: {stl_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
