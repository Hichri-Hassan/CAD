"""Execute CAD JSON operations inside a FreeCAD document."""

from __future__ import annotations

from typing import Any

from compiler.context import CompileContext, unit_scale_factor
from compiler.loader import load_cad_json
from compiler.operations.fillet_chamfer import execute_chamfer, execute_fillet
from compiler.operations.hole import execute_hole
from compiler.operations.pad_pocket import execute_pad, execute_pocket
from compiler.operations.sketch import execute_sketch


def compile_document(cad_json: dict[str, Any]) -> CompileContext:
    """Build a FreeCAD document from CAD JSON."""
    import FreeCAD as App

    metadata = cad_json["metadata"]
    operations = cad_json["operations"]

    doc = App.newDocument("CompiledPart")
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

    for operation in operations:
        op_id = operation["id"]
        op_type = operation["type"]
        executor = executors[op_type]
        obj = executor(operation, context)
        context.register(op_id, obj)
        context.doc.recompute()
        _raise_if_invalid(obj, op_type, op_id)

    context.doc.recompute()
    _raise_if_document_errors(context.doc)
    return context


def _raise_if_invalid(obj: Any, op_type: str, op_id: str) -> None:
    if hasattr(obj, "isValid") and not obj.isValid():
        raise RuntimeError(f"FreeCAD object invalid after {op_type} '{op_id}'.")

    if hasattr(obj, "State") and "Error" in obj.State:
        raise RuntimeError(f"FreeCAD error after {op_type} '{op_id}': {obj.State}")


def _raise_if_document_errors(doc: Any) -> None:
    errors = [
        obj.Name
        for obj in doc.Objects
        if hasattr(obj, "State") and "Error" in obj.State
    ]
    if errors:
        raise RuntimeError(f"FreeCAD document contains errors in: {', '.join(errors)}")


def compile_file(input_path: str, output_path: str) -> CompileContext:
    """Load JSON, compile, and save .FCStd."""
    from pathlib import Path

    cad_json = load_cad_json(Path(input_path))
    context = compile_document(cad_json)
    context.doc.saveAs(output_path)
    return context
