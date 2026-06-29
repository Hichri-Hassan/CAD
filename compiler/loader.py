"""Load and validate CAD JSON input."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SUPPORTED_OPERATIONS = {"Sketch", "Pad", "Pocket", "Hole", "Fillet", "Chamfer"}
SUPPORTED_ENTITIES = {"Line", "Circle", "Arc", "Rectangle", "Point"}
SUPPORTED_UNITS = {"mm", "cm", "m", "inch"}


def load_cad_json(path: Path | str) -> dict[str, Any]:
    """Load a CAD JSON file and perform basic structural validation."""
    path = Path(path)
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)

    if "metadata" not in data:
        raise ValueError("Missing metadata section.")
    if "operations" not in data:
        raise ValueError("Missing operations section.")

    metadata = data["metadata"]
    if "version" not in metadata:
        raise ValueError("Missing metadata.version.")
    if "unit" not in metadata:
        raise ValueError("Missing metadata.unit.")
    if metadata["unit"] not in SUPPORTED_UNITS:
        raise ValueError(f"Unsupported unit: {metadata['unit']}")

    operations = data["operations"]
    if not isinstance(operations, list) or not operations:
        raise ValueError("operations must be a non-empty array.")

    seen_ids: set[str] = set()
    for index, operation in enumerate(operations):
        op_id = operation.get("id")
        op_type = operation.get("type")
        if not op_id or not op_type:
            raise ValueError(f"Operation at index {index} missing id or type.")
        if op_id in seen_ids:
            raise ValueError(f"Duplicate operation id: {op_id}")
        if op_type not in SUPPORTED_OPERATIONS:
            raise ValueError(f"Unsupported operation type: {op_type}")
        _validate_operation_fields(operation, seen_ids)
        seen_ids.add(op_id)

    return data


def _validate_operation_fields(operation: dict[str, Any], prior_ids: set[str]) -> None:
    op_type = operation["type"]
    op_id = operation["id"]

    if op_type == "Sketch":
        if "entities" not in operation:
            raise ValueError(f"Sketch {op_id} missing entities.")
        if "plane" not in operation and "support" not in operation:
            raise ValueError(f"Sketch {op_id} missing plane or support.")
        if "attachment_offset" in operation:
            _validate_attachment_offset(operation["attachment_offset"], op_id)
        for entity in operation["entities"]:
            entity_type = entity.get("type")
            if entity_type not in SUPPORTED_ENTITIES:
                raise ValueError(f"Unsupported sketch entity type: {entity_type}")

    elif op_type == "Pad":
        _require_reference(operation, "profile", prior_ids)
        if "length" not in operation:
            raise ValueError(f"Pad {op_id} missing length.")

    elif op_type == "Pocket":
        _require_reference(operation, "profile", prior_ids)
        if "depth" not in operation:
            raise ValueError(f"Pocket {op_id} missing depth.")

    elif op_type == "Hole":
        _require_reference(operation, "profile", prior_ids)
        if "diameter" not in operation:
            raise ValueError(f"Hole {op_id} missing diameter.")
        if "depth" not in operation:
            raise ValueError(f"Hole {op_id} missing depth.")

    elif op_type == "Fillet":
        if "radius" not in operation:
            raise ValueError(f"Fillet {op_id} missing radius.")

    elif op_type == "Chamfer":
        if "distance" not in operation:
            raise ValueError(f"Chamfer {op_id} missing distance.")


def _require_reference(operation: dict[str, Any], field: str, prior_ids: set[str]) -> None:
    op_id = operation["id"]
    reference = operation.get(field)
    if not reference:
        raise ValueError(f"{operation['type']} {op_id} missing {field}.")
    if reference not in prior_ids:
        raise ValueError(
            f"{operation['type']} {op_id} references unknown operation: {reference}"
        )


def _validate_attachment_offset(offset: Any, op_id: str) -> None:
    if not isinstance(offset, dict):
        raise ValueError(f"Sketch {op_id} attachment_offset must be an object.")
    position = offset.get("position")
    rotation = offset.get("rotation")
    if not isinstance(position, list) or len(position) != 3:
        raise ValueError(f"Sketch {op_id} attachment_offset.position must be [x, y, z].")
    if not isinstance(rotation, list) or len(rotation) != 4:
        raise ValueError(
            f"Sketch {op_id} attachment_offset.rotation must be [qx, qy, qz, qw]."
        )
