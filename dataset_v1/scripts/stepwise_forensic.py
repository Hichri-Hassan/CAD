"""Stepwise FreeCAD compilation forensic script (runs inside freecadcmd)."""

from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path


def _ensure_project_root() -> Path:
    root_str = os.environ.get("CAD_COMPILER_ROOT")
    if not root_str:
        raise RuntimeError("CAD_COMPILER_ROOT environment variable is required.")
    root = Path(root_str)
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    return root


def stepwise_compile(json_path: Path) -> dict:
    import FreeCAD as App

    from compiler.context import CompileContext, unit_scale_factor
    from compiler.operations.fillet_chamfer import execute_chamfer, execute_fillet
    from compiler.operations.hole import execute_hole
    from compiler.operations.pad_pocket import execute_pad, execute_pocket
    from compiler.operations.sketch import execute_sketch

    cad_json = json.loads(json_path.read_text(encoding="utf-8"))
    metadata = cad_json["metadata"]
    operations = cad_json["operations"]

    doc = App.newDocument("Forensic")
    body = doc.addObject("PartDesign::Body", "Body")
    doc.recompute()

    context = CompileContext(
        doc=doc,
        body=body,
        unit_scale=unit_scale_factor(metadata["unit"]),
    )
    executors = {
        "Sketch": execute_sketch,
        "Pad": execute_pad,
        "Pocket": execute_pocket,
        "Hole": execute_hole,
        "Fillet": execute_fillet,
        "Chamfer": execute_chamfer,
    }

    steps = []
    for operation in operations:
        op_id = operation["id"]
        op_type = operation["type"]
        step_info = {
            "operation_id": op_id,
            "operation_type": op_type,
            "valid": True,
            "state": [],
            "error": "",
            "freecad_error": "",
        }
        try:
            obj = executors[op_type](operation, context)
            context.register(op_id, obj)
            doc.recompute()
            step_info["state"] = list(getattr(obj, "State", []))
            step_info["valid"] = bool(getattr(obj, "isValid", lambda: True)())
            step_info["error"] = str(getattr(obj, "Error", "") or "")
            if not step_info["valid"] or "Error" in step_info["state"]:
                steps.append(step_info)
                break
        except Exception as exc:  # noqa: BLE001
            step_info["valid"] = False
            step_info["freecad_error"] = str(exc)
            steps.append(step_info)
            break
        steps.append(step_info)

    App.closeDocument(doc.Name)
    return {
        "operation_count": len(operations),
        "steps": steps,
        "failed": any(not step["valid"] or "Error" in step["state"] for step in steps),
    }


def main() -> int:
    _ensure_project_root()
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: stepwise_forensic.py <input.json> <output.json>"}))
        return 2

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    try:
        result = stepwise_compile(input_path)
        output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return 0
    except Exception as exc:  # noqa: BLE001
        output_path.write_text(
            json.dumps({"error": str(exc), "traceback": traceback.format_exc()}, indent=2),
            encoding="utf-8",
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
