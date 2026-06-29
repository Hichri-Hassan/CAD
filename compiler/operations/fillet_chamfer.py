"""Execute Fillet and Chamfer operations in FreeCAD."""

from __future__ import annotations

from typing import Any


def execute_fillet(operation: dict[str, Any], context: Any) -> Any:
    fillet = context.body.newObject("PartDesign::Fillet", operation["id"])
    fillet.Radius = operation["radius"] * context.unit_scale
    _apply_edge_selection(fillet, "Base", operation.get("edges", []), context)
    return fillet


def execute_chamfer(operation: dict[str, Any], context: Any) -> Any:
    chamfer = context.body.newObject("PartDesign::Chamfer", operation["id"])
    chamfer.Size = operation["distance"] * context.unit_scale
    _apply_edge_selection(chamfer, "Base", operation.get("edges", []), context)
    return chamfer


def _apply_edge_selection(
    feature: Any,
    property_name: str,
    edges: list[dict[str, Any]],
    context: Any,
) -> None:
    if not edges:
        context.warnings.append(
            f"{feature.Label}: no edges specified; feature may fail at recompute."
        )
        return

    if len(edges) == 1 and edges[0].get("type") == "all":
        feature.UseAllEdges = True
        return

    references: list[tuple[Any, str]] = []
    for edge in edges:
        reference = context.resolve(edge["reference"])
        selector = edge["selector"]
        references.append((reference, selector))

    if len(references) == 1:
        feature.Base = references[0]
    else:
        # FreeCAD V0: apply first edge reference; multi-edge selection is future work.
        feature.Base = references[0]
        if len(references) > 1:
            context.warnings.append(
                f"{feature.Label}: multiple edges specified; only the first is applied in V0."
            )
