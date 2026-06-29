# 02 — Parser Specification

## 1. Purpose

The parser converts existing FreeCAD `.FCStd` files into the project’s standardized CAD JSON format.

```text
.FCStd
    ↓
Parser
    ↓
CAD JSON
```

The parser is mainly used for dataset creation.

## 2. Parser Goal

The parser should extract the construction history of a CAD model and represent it as a sequence of supported CAD operations.

The output JSON should describe the design intent, not FreeCAD internal implementation details.

## 3. Input

The parser takes a `.FCStd` file as input.

A `.FCStd` file is treated as an archive containing FreeCAD document data.

The parser may inspect internal files such as:

- `Document.xml`
- object/property files
- embedded sketch data
- other files required by FreeCAD

The exact implementation details are left to the developer/Cursor.

## 4. Output

The parser outputs one CAD JSON file per input model.

Example:

```json
{
  "metadata": {
    "version": "1.0",
    "unit": "mm",
    "source_format": "FCStd"
  },
  "operations": []
}
```

## 5. Supported Features in V1

The parser must only support:

- Sketch
- Pad
- Pocket
- Hole
- Fillet
- Chamfer

`Pocket` and `Hole` are independent first-class operations. The parser must preserve each FreeCAD feature type as its corresponding JSON operation without converting one into another.

Unsupported features should be ignored or flagged depending on parser mode.

## 6. General Rules

The parser must:

- preserve construction order;
- preserve sketch geometry exactly as it exists in the FreeCAD model;
- extract only supported features;
- ignore UI/display properties;
- avoid FreeCAD internal names when possible;
- output deterministic JSON;
- include metadata;
- fail safely on corrupted or unsupported files;
- produce logs for debugging.

The parser must **never rewrite sketch geometry**. For example, if a sketch contains a circle whose radius differs from a `PartDesign::Hole` diameter parameter, the sketch is exported exactly as stored in FreeCAD.

## 7. Supported Operation Requirements

### 7.1 Sketch

The parser should extract:

- sketch ID;
- sketch plane or support face;
- attachment offset when non-zero;
- 2D entities;
- dimensions when available;
- constraints when available.

The parser emits sketch entities in **FreeCAD `GeometryList` order** — the same construction order used when the sketch was created. This order affects Pad topology and face numbering downstream, so it must be preserved faithfully.

Supported sketch entities in V1:

- Line
- Circle
- Arc
- Rectangle (compiler-only for manually authored JSON; parser emits constituent Lines)
- Point

For closed rectangles, the parser emits **four Line entities in original construction order** rather than collapsing to a single `Rectangle` entity. Collapsing would discard winding order and can change OpenCascade face numbering after Pad.

Point entities represent hole placement markers or other point geometry in a sketch:

```json
{
  "id": "e_001",
  "type": "Point",
  "position": [25, 25]
}
```

### 7.2 Pad

The parser should extract:

- operation ID;
- referenced sketch/profile;
- extrusion length;
- direction if available;
- reversed direction if available;
- symmetric/midplane mode if available.

Minimum required fields:

```json
{
  "id": "op_002",
  "type": "Pad",
  "profile": "op_001",
  "length": 10
}
```

### 7.3 Pocket

The parser should extract:

- operation ID;
- referenced sketch/profile;
- pocket depth;
- through-all mode if available;
- reversed direction if available.

Minimum required fields:

```json
{
  "id": "op_004",
  "type": "Pocket",
  "profile": "op_003",
  "depth": 10
}
```

### 7.4 Hole

The parser should extract a native `PartDesign::Hole` feature as a `Hole` operation.

When the source model contains a FreeCAD `PartDesign::Hole` feature, the parser must:

1. emit the hole placement sketch as a normal `Sketch` operation (which may contain `Point` or `Circle` entities);
2. emit a `Hole` operation referencing that sketch.

Minimum required fields:

```json
{
  "id": "op_004",
  "type": "Hole",
  "profile": "op_003",
  "diameter": 6,
  "depth": 10
}
```

Advanced `PartDesign::Hole` parameters are outside Parser V0 scope and must be ignored, including:

- threads;
- countersinks;
- counterbores;
- drill angles;
- other manufacturing-specific parameters.

Face and edge selectors from FreeCAD (e.g. `Face4`, `Edge7`) must be preserved exactly as they appear in the source file.

### 7.5 Fillet

The parser should extract:

- operation ID;
- radius;
- selected edges if available.

Minimum required fields:

```json
{
  "id": "op_005",
  "type": "Fillet",
  "radius": 2
}
```

If edge references are unreliable, the parser may store them as a best-effort field.

### 7.6 Chamfer

The parser should extract:

- operation ID;
- chamfer distance;
- selected edges if available.

Minimum required fields:

```json
{
  "id": "op_006",
  "type": "Chamfer",
  "distance": 1
}
```

## 8. Metadata Requirements

Each output JSON must include:

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

Important metadata fields:

| Field | Meaning |
|---|---|
| version | CAD JSON schema version |
| unit | Unit used by numeric dimensions |
| source_format | Original file format |
| parser_version | Version of the parser |
| source_path | Optional original file path |
| license | Optional source license |

## 9. Error Handling

The parser should classify files as:

- `valid`
- `partially_supported`
- `unsupported`
- `corrupted`

If a file contains unsupported features, the parser should not crash.

It should either:

- ignore unsupported features and mark the file as `partially_supported`;
- or reject the file depending on configuration.

## 10. Parser Modes

Recommended parser modes:

### Strict Mode

Rejects files containing unsupported operations.

### Lenient Mode

Extracts supported operations and logs unsupported ones.

## 11. Validation

After parsing, the output JSON should be passed through the JSON validator.

The parser output is valid only if:

- required metadata exists;
- operations are ordered;
- operation IDs are unique;
- required fields are present;
- references point to existing operations.

## 12. V1 Success Criteria

Parser V1 is successful if it can convert simple FreeCAD parts containing:

- one sketch;
- one pad;
- one pocket or hole;
- optional fillets or chamfers;

into valid CAD JSON.
