# 03 — JSON Specification

## 1. Purpose

This document defines the CAD JSON format used as the intermediate representation of the project.

The CAD JSON represents the design intent and construction history of a CAD model.

It is used by:

- the parser;
- the dataset builder;
- the AI model;
- the validator;
- the compiler.

## 2. High-Level Structure

A CAD JSON file contains:

```json
{
  "metadata": {},
  "operations": []
}
```

## 3. Metadata

The `metadata` section contains global information about the file.

Example:

```json
{
  "metadata": {
    "version": "1.0",
    "unit": "mm",
    "source_format": "FCStd",
    "parser_version": "0.1"
  }
}
```

### Required Fields

| Field | Type | Required | Description |
|---|---|---|---|
| version | string | yes | CAD JSON schema version |
| unit | string | yes | Measurement unit |

### Supported Units

V1 supported units:

- `mm`
- `cm`
- `m`
- `inch`

All numeric dimensions are interpreted according to `metadata.unit`.

## 4. Operations

The `operations` array represents the construction history.

Example:

```json
{
  "operations": [
    {
      "id": "op_001",
      "type": "Sketch"
    },
    {
      "id": "op_002",
      "type": "Pad"
    }
  ]
}
```

Rules:

- operations must be ordered;
- each operation must have a unique `id`;
- each operation must have a `type`;
- references must point to previous operations;
- unsupported operation types are invalid in V1.

## 5. Supported Operation Types

V1 supports:

- `Sketch`
- `Pad`
- `Pocket`
- `Hole`
- `Fillet`
- `Chamfer`

Both `Pocket` and `Hole` are first-class operation types.

## 6. Sketch Operation

A sketch defines 2D geometry.

Example:

```json
{
  "id": "op_001",
  "type": "Sketch",
  "plane": "XY",
  "entities": [],
  "constraints": []
}
```

### Fields

| Field | Type | Required | Description |
|---|---|---|---|
| id | string | yes | Operation ID |
| type | string | yes | Must be `Sketch` |
| plane | string | yes | Sketch plane or support |
| entities | array | yes | Sketch entities |
| constraints | array | no | Sketch constraints |
| attachment_offset | object | no | Sketch attachment offset relative to support |

### attachment_offset

Optional placement offset applied after attaching the sketch to its support plane or face. Omitted when zero/identity. Entity coordinates remain in sketch-local 2D space.

```json
{
  "attachment_offset": {
    "position": [20.0, -1.0, 0.0],
    "rotation": [0.0, 0.0, 0.0, 1.0]
  }
}
```

| Field | Type | Description |
|---|---|---|
| position | [x, y, z] | Translation in mm |
| rotation | [qx, qy, qz, qw] | Rotation quaternion |

### Supported Planes

V1 supported base planes:

- `XY`
- `XZ`
- `YZ`

Face-based sketches may use:

```json
{
  "support": {
    "type": "face",
    "reference": "op_002",
    "selector": "Face4"
  }
}
```

Face selectors should preserve the FreeCAD sub-element name exactly (e.g. `Face4`, not a semantic alias such as `top`).

## 7. Sketch Entities

### 7.1 Line

```json
{
  "id": "e_001",
  "type": "Line",
  "start": [0, 0],
  "end": [50, 0]
}
```

### 7.2 Circle

```json
{
  "id": "e_002",
  "type": "Circle",
  "center": [25, 25],
  "radius": 5
}
```

### 7.3 Arc

```json
{
  "id": "e_003",
  "type": "Arc",
  "center": [25, 25],
  "radius": 10,
  "start_angle": 0,
  "end_angle": 90
}
```

Angles are in degrees.

### 7.4 Rectangle

```json
{
  "id": "e_004",
  "type": "Rectangle",
  "origin": [0, 0],
  "width": 100,
  "height": 50
}
```

### 7.5 Point

```json
{
  "id": "e_005",
  "type": "Point",
  "position": [25, 25]
}
```

Point entities are commonly used as hole placement markers in face-based sketches.

## 8. Sketch Constraints

Constraints are optional in early V1, but the format should allow them.

Examples:

```json
{
  "type": "Horizontal",
  "entity": "e_001"
}
```

```json
{
  "type": "Coincident",
  "entity_1": "e_001",
  "entity_2": "e_002"
}
```

Supported constraints may include:

- Horizontal
- Vertical
- Coincident
- Equal
- Radius
- Distance
- Diameter

## 9. Pad Operation

A pad extrudes a sketch into a solid.

Example:

```json
{
  "id": "op_002",
  "type": "Pad",
  "profile": "op_001",
  "length": 10,
  "direction": "normal",
  "reversed": false,
  "symmetric": false
}
```

### Required Fields

| Field | Type | Required |
|---|---|---|
| id | string | yes |
| type | string | yes |
| profile | string | yes |
| length | number | yes |

## 10. Pocket Operation

A pocket removes material using a sketch.

Example:

```json
{
  "id": "op_004",
  "type": "Pocket",
  "profile": "op_003",
  "depth": 10,
  "through_all": false,
  "reversed": false
}
```

If the pocket goes through the full body:

```json
{
  "depth": "through_all"
}
```

## 11. Hole Operation

A hole creates a circular cut using a placement sketch and hole parameters.

Example:

```json
{
  "id": "op_004",
  "type": "Hole",
  "profile": "op_003",
  "diameter": 6,
  "depth": "through_all"
}
```

### Required Fields

| Field | Type | Required |
|---|---|---|
| id | string | yes |
| type | string | yes |
| profile | string | yes |
| diameter | number | yes |
| depth | number or `"through_all"` | yes |

The placement sketch may contain a `Point` or `Circle` entity. The `diameter` field supplies the hole size when the sketch uses a point marker.

## 12. Fillet Operation

A fillet rounds selected edges.

Example:

```json
{
  "id": "op_005",
  "type": "Fillet",
  "radius": 2,
  "edges": []
}
```

The `edges` field is optional in V1 because stable edge references may be difficult.

## 13. Chamfer Operation

A chamfer bevels selected edges.

Example:

```json
{
  "id": "op_006",
  "type": "Chamfer",
  "distance": 1,
  "edges": []
}
```

## 14. Complete Example

```json
{
  "metadata": {
    "version": "1.0",
    "unit": "mm",
    "source_format": "manual"
  },
  "operations": [
    {
      "id": "op_001",
      "type": "Sketch",
      "plane": "XY",
      "entities": [
        {
          "id": "e_001",
          "type": "Rectangle",
          "origin": [0, 0],
          "width": 100,
          "height": 50
        }
      ],
      "constraints": []
    },
    {
      "id": "op_002",
      "type": "Pad",
      "profile": "op_001",
      "length": 10
    },
    {
      "id": "op_003",
      "type": "Sketch",
      "support": {
        "type": "face",
        "reference": "op_002",
        "selector": "Face4"
      },
      "entities": [
        {
          "id": "e_002",
          "type": "Circle",
          "center": [50, 25],
          "radius": 5
        }
      ],
      "constraints": []
    },
    {
      "id": "op_004",
      "type": "Hole",
      "profile": "op_003",
      "diameter": 10,
      "depth": "through_all"
    },
    {
      "id": "op_005",
      "type": "Fillet",
      "radius": 2,
      "edges": []
    }
  ]
}
```

## 15. Validation Rules

A JSON file is valid if:

- `metadata.version` exists;
- `metadata.unit` exists;
- `operations` is a non-empty array;
- each operation has a unique ID;
- each operation has a supported type;
- required fields are present;
- numeric dimensions are positive;
- references point to previous operations.
