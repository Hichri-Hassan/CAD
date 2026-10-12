"""Generate compact structured summaries from CAD JSON operations."""

from __future__ import annotations

from typing import Any


def generate_summary(cad_json: dict[str, Any]) -> dict[str, Any]:
    """Build a compact engineering summary suitable for prompt generation."""
    operations = cad_json.get("operations", [])
    metadata = cad_json.get("metadata", {})
    unit = metadata.get("unit", "mm")

    counts = {
        "sketches": 0,
        "pads": 0,
        "pockets": 0,
        "holes": 0,
        "fillets": 0,
        "chamfers": 0,
    }
    dimensions: dict[str, list[float]] = {
        "extrusion_heights": [],
        "pocket_depths": [],
        "hole_diameters": [],
        "hole_depths": [],
        "fillet_radii": [],
        "chamfer_distances": [],
    }
    sequence: list[str] = []
    characteristics: list[str] = []

    for operation in operations:
        op_type = operation.get("type")
        if op_type == "Sketch":
            counts["sketches"] += 1
            sequence.append(_describe_sketch(operation, unit))
        elif op_type == "Pad":
            counts["pads"] += 1
            length = operation.get("length")
            if isinstance(length, (int, float)):
                dimensions["extrusion_heights"].append(float(length))
            sequence.append(_describe_pad(operation, unit))
        elif op_type == "Pocket":
            counts["pockets"] += 1
            depth = operation.get("depth")
            if isinstance(depth, (int, float)):
                dimensions["pocket_depths"].append(float(depth))
            sequence.append(_describe_pocket(operation, unit))
        elif op_type == "Hole":
            counts["holes"] += 1
            diameter = operation.get("diameter")
            depth = operation.get("depth")
            if isinstance(diameter, (int, float)):
                dimensions["hole_diameters"].append(float(diameter))
            if isinstance(depth, (int, float)):
                dimensions["hole_depths"].append(float(depth))
            sequence.append(_describe_hole(operation, unit))
        elif op_type == "Fillet":
            counts["fillets"] += 1
            radius = operation.get("radius")
            if isinstance(radius, (int, float)):
                dimensions["fillet_radii"].append(float(radius))
            sequence.append(_describe_fillet(operation, unit))
        elif op_type == "Chamfer":
            counts["chamfers"] += 1
            distance = operation.get("distance")
            if isinstance(distance, (int, float)):
                dimensions["chamfer_distances"].append(float(distance))
            sequence.append(_describe_chamfer(operation, unit))

    if counts["holes"] > 0:
        characteristics.append(f"{counts['holes']} hole(s)")
    if counts["pockets"] > 0:
        characteristics.append(f"{counts['pockets']} recessed pocket(s)")
    if counts["fillets"] > 0:
        characteristics.append(f"{counts['fillets']} rounded corner(s)")
    if counts["chamfers"] > 0:
        characteristics.append(f"{counts['chamfers']} chamfered edge(s)")
    if counts["pads"] == 1 and counts["pockets"] == 0 and counts["holes"] <= 1:
        characteristics.append("single solid base part")
    if counts["holes"] >= 2:
        characteristics.append("multiple holes")

    overall_shape = _infer_overall_shape(counts, dimensions)

    return {
        "unit": unit,
        "overall_shape": overall_shape,
        "operation_sequence": sequence,
        "feature_counts": counts,
        "dimensions": {key: values for key, values in dimensions.items() if values},
        "characteristics": characteristics,
        "total_operations": len(operations),
    }


def summary_to_text(summary: dict[str, Any]) -> str:
    """Render the structured summary as compact plain text for the LLM."""
    lines = [
        f"Unit: {summary.get('unit', 'mm')}",
        f"Overall shape: {summary.get('overall_shape', 'unknown')}",
        f"Total construction steps: {summary.get('total_operations', 0)}",
    ]

    counts = summary.get("feature_counts", {})
    count_bits = [f"{value} {name}" for name, value in counts.items() if value]
    if count_bits:
        lines.append("Feature counts: " + ", ".join(count_bits))

    dimensions = summary.get("dimensions", {})
    if dimensions:
        lines.append("Key dimensions:")
        for name, values in dimensions.items():
            label = name.replace("_", " ")
            if len(values) == 1:
                lines.append(f"  - {label}: {values[0]} {summary.get('unit', 'mm')}")
            else:
                joined = ", ".join(str(v) for v in values[:8])
                lines.append(f"  - {label}: {joined} {summary.get('unit', 'mm')}")

    sequence = summary.get("operation_sequence", [])
    if sequence:
        lines.append("Visible geometry:")
        for index, step in enumerate(sequence, start=1):
            lines.append(f"  {index}. {step}")

    characteristics = summary.get("characteristics", [])
    if characteristics:
        lines.append("Notable characteristics: " + "; ".join(characteristics))

    return "\n".join(lines)


def _describe_sketch(operation: dict[str, Any], unit: str) -> str:
    entities = operation.get("entities", [])
    entity_types = {entity.get("type") for entity in entities}
    plane = operation.get("plane") or operation.get("support", {}).get("selector", "face")
    if "Circle" in entity_types:
        return f"circular profile on {plane}"
    if "Point" in entity_types:
        return f"reference point on {plane}"
    if "Line" in entity_types and len(entities) >= 4:
        return f"closed rectangular outline on {plane}"
    return f"2D outline on {plane}"


def _describe_pad(operation: dict[str, Any], unit: str) -> str:
    length = operation.get("length", "?")
    return f"rectangular block, overall height {length} {unit}"


def _describe_pocket(operation: dict[str, Any], unit: str) -> str:
    depth = operation.get("depth", "?")
    if depth == "through":
        return "through pocket cut"
    return f"recessed pocket, depth {depth} {unit}"


def _describe_hole(operation: dict[str, Any], unit: str) -> str:
    diameter = operation.get("diameter", "?")
    depth = operation.get("depth", "?")
    hole_type = "through hole" if depth == "through" else "blind hole"
    return f"{hole_type}, diameter {diameter} {unit}"


def _describe_fillet(operation: dict[str, Any], unit: str) -> str:
    radius = operation.get("radius", "?")
    return f"rounded corner, radius {radius} {unit}"


def _describe_chamfer(operation: dict[str, Any], unit: str) -> str:
    distance = operation.get("distance", "?")
    return f"chamfered edge, distance {distance} {unit}"


def _infer_overall_shape(counts: dict[str, int], dimensions: dict[str, list[float]]) -> str:
    if counts["pads"] >= 1 and counts["pockets"] == 0 and counts["holes"] == 0:
        return "rectangular block"
    if counts["pads"] >= 1 and counts["pockets"] >= 1:
        return "rectangular plate with recessed pockets"
    if counts["pads"] >= 1 and counts["holes"] >= 1:
        return "rectangular block with holes"
    if counts["holes"] >= 1:
        return "part with holes"
    if counts["fillets"] or counts["chamfers"]:
        return "block with edge treatments"
    return "mechanical part"
