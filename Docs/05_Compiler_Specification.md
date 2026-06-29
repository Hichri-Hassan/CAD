# 05 — Compiler Specification

## 1. Purpose

The compiler converts CAD JSON into executable FreeCAD operations.

```text
CAD JSON
    ↓
Compiler
    ↓
FreeCAD API
    ↓
.FCStd / .STEP
```

The compiler is part of the runtime pipeline.

## 2. Role of the Compiler

The compiler should not make creative design decisions.

It should only:

- read the CAD JSON;
- validate operation order;
- execute operations in FreeCAD;
- save the resulting `.FCStd`;
- export `.STEP`.

## 3. Input

The compiler takes a valid CAD JSON file.

The JSON must already have passed validation.

## 4. Output

The compiler should output:

- a FreeCAD document;
- a `.FCStd` file;
- optionally a `.STEP` file;
- execution logs.

## 5. Compiler Pipeline

```text
Load JSON
    ↓
Validate JSON
    ↓
Initialize FreeCAD document
    ↓
Execute operations in order
    ↓
Recompute document
    ↓
Save .FCStd
    ↓
Export .STEP
```

## 6. Operation Execution

### 6.1 Sketch

The compiler creates a FreeCAD sketch on the specified plane or support face.

It restores `AttachmentOffset` when `attachment_offset` is present in JSON, then recomputes before adding geometry.

It then adds all sketch entities:

- lines;
- circles;
- arcs;
- rectangles;
- points.

Constraints may be added if supported.

### 6.2 Pad

The compiler takes a referenced sketch and creates an extrusion.

Required data:

- profile reference;
- length;
- direction;
- reversed mode;
- symmetric mode.

### 6.3 Pocket

The compiler takes a referenced sketch and creates a cut.

Required data:

- profile reference;
- depth or through-all mode;
- reversed mode.

### 6.4 Hole

The compiler creates a native `PartDesign::Hole` feature.

Required data:

- profile reference (placement sketch);
- diameter;
- depth or through-all mode;
- reversed mode.

The compiler must attach the placement sketch to its support face before creating the hole, and must not convert a Hole into a Pocket.

Advanced manufacturing hole features (threads, countersinks, counterbores, drill angles) are outside Compiler V0 scope.

### 6.5 Fillet

The compiler applies a fillet to selected edges.

If stable edge references are not available in V1, the compiler may support only simple/global fillet behavior or fail gracefully.

### 6.6 Chamfer

The compiler applies a chamfer to selected edges.

If edge references are unreliable, the compiler should fail gracefully rather than producing incorrect geometry.

## 7. References

Operations may reference previous operations (e.g., a Pad references the Sketch used as its profile).

The compiler must correctly resolve these references before executing each operation.

The mechanism used to resolve references is left to the implementation.

## 8. Units

The compiler must interpret numeric values according to `metadata.unit`.

Example:

```json
{
  "metadata": {
    "unit": "mm"
  }
}
```

If `unit` is `m`, the compiler must convert values before passing them to FreeCAD if needed.

## 9. Error Handling

The compiler should fail safely.

Possible errors:

- invalid JSON;
- missing operation reference;
- unsupported operation type;
- invalid sketch;
- failed FreeCAD operation;
- failed STEP export.

The compiler should produce useful error messages.

## 10. Compiler Modes

### Strict Mode

Stop immediately when an operation fails.

### Best-Effort Mode

Try to execute supported operations and log failures.

For V1, strict mode is preferred.

## 11. V1 Success Criteria

Compiler V1 is successful if it can generate simple parts from valid CAD JSON:

- rectangular plate;
- cube;
- plate with through hole;
- filleted block;
- chamfered block.

## 12. Long-Term Goals

Future compiler versions may support:

- assemblies;
- advanced constraints;
- patterns;
- revolutions;
- lofts;
- sweeps;
- shell;
- stable face/edge references;
- automatic repair of invalid JSON.
