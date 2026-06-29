# Round-Trip Validation Report

## Summary

The architecture has been updated so that **Pocket** and **Hole** are independent first-class operations. The parser preserves FreeCAD feature types faithfully, and the compiler creates native `PartDesign::Hole` features.

The parser → JSON → compiler round-trip is **fully functional** for both test models.

---

## Changes Made

### Parser

- Removed `PartDesign::Hole` → `Pocket` conversion
- Added `extract_hole()` producing native `Hole` operations with `profile`, `diameter`, and `depth`
- Placement sketches are emitted as separate `Sketch` operations (including `Point` entities)
- Sketch geometry is never modified

### JSON Specification

- Reintroduced `Hole` as a supported operation type
- Required fields: `profile`, `diameter`, `depth` (or `"through_all"`)
- Updated complete example to use `Hole` instead of `Pocket` for circular cuts

### Compiler

- Added `compiler/operations/hole.py` — creates native `PartDesign::Hole` via FreeCAD API
- **Fixed face attachment bug**: recompute document after setting `AttachmentSupport` and before adding sketch geometry, so face-based sketches (e.g. on `Face4`) are correctly positioned on the Pad face
- **Fixed datum-plane attachment (90° rotation)**: base sketches attach via `(Origin, XZ_Plane)` instead of attaching directly to the datum plane object
- **Preserved sketch construction order**: parser emits Lines in FreeCAD `GeometryList` order; compiler adds geometry in that same order so Pad topology and face numbering match the original model

### Parser (topology fidelity)

- Removed rectangle collapse — four axis-aligned lines stay as individual `Line` entities in original construction order
- Constraints are preserved alongside line entities (no longer cleared by rectangle detection)

### Documentation

Updated: `01_System_Architecture.md`, `02_Parser_Specification.md`, `03_JSON_Specification.md`, `05_Compiler_Specification.md`, `06_AI_Model.md`

---

## Regenerated Outputs

### Parser JSON

**cube.json** — 4 operations:
```text
Sketch → Pad → Sketch (Circle on Face4) → Hole (Ø6, depth 10)
```

**hole.json** — 6 operations:
```text
Sketch → Pad → Sketch (Point on Face4) → Hole (Ø6, depth 16) → Chamfer → Fillet
```

### Compiled FCStd

| File | Status | Feature tree |
|---|---|---|
| `cube_compiled.FCStd` | All features Up-to-date, no errors | Sketch → Pad → Sketch → Hole |
| `hole_compiled.FCStd` | All features Up-to-date, no errors | Sketch → Pad → Sketch → Hole → Chamfer → Fillet |

### Feature tree comparison with originals

| Original | Compiled | Match |
|---|---|---|
| Sketch, Pad, Sketch001, Hole | op_001, op_002, op_003, op_004 | Same structure |
| Sketch, Pad, Sketch001, Hole, Chamfer, Fillet | op_001 … op_006 | Same structure |

Face attachment verified: `op_003` attaches to `op_002` / `Face4` with `MapMode=FlatFace`.

---

## Topology Fidelity Verification

Verified by comparing original and compiled FCStd files (no face-index remapping):

| Check | cube | hole |
|---|---|---|
| Pad face numbering (Face4 = top +Z face) | Match | Match |
| Base sketch attachment `(Origin, XZ_Plane)` | Match | Match |
| Hole sketch attachment `(Pad, Face4)` | Match | Match |
| Hole / circle global position | (−15.805, −16.235, 30.891) | (−23.851, −5.460, 34.196) |
| Chamfer `Edge7` on Hole | — | Up-to-date |
| Fillet `Edge6` on Chamfer | — | Up-to-date |
| Document errors | none | none |

Face-by-face normal and center-of-mass signatures are identical between original and compiled Pad solids for both models.

---

## Compiler Bug Fix

**Issue:** Second sketch (circle) was created in global coordinates instead of on Pad Face4, causing Pocket/Hole to miss the body.

**Root cause:** Sketch geometry was added before the attachment placement was computed.

**Fix:** Call `context.doc.recompute()` after setting `AttachmentSupport`/`MapMode` and before adding entities.

---

## Topology Bug Fix

**Issue:** Compiled Pad had different face numbering from the original — `Face4` referred to a side face instead of the top face, so the Hole sketch attached to the wrong physical surface.

**Root causes:**
1. Base sketch attached to `(XZ_Plane, '')` instead of `(Origin, XZ_Plane)`, causing a 90° Pad rotation
2. Rectangle lines were emitted in bottom-first order instead of FreeCAD's original left-edge-first construction order

**Fix:** Attach datum-plane sketches via `(body.Origin, plane_name)`; parser preserves FreeCAD `GeometryList` line order; compiler adds lines in JSON array order.

---

## Remaining Issues

1. **Circle radius vs Hole diameter** — `cube.json` sketch circle has radius 6.92 mm while Hole diameter is 6.0 mm (faithful to source FreeCAD model; not a round-trip bug).

2. **Edge selector stability** — Chamfer/Fillet edge indices (`Edge7`, `Edge6`) work for the test models but remain best-effort across recomputes.

3. **Sketch constraints** — Parsed but not applied by the compiler in V0.

4. **Advanced Hole parameters** — Threads, countersinks, etc. are ignored by parser and unsupported by compiler.

5. **Object naming** — Compiled models use `op_XXX` names instead of original FreeCAD names (`Sketch`, `Pad`, etc.). This is expected for the JSON-driven workflow.

---

## Round-Trip Status

| Model | Parse | Compile | Open in FreeCAD | Feature tree correct |
|---|---|---|---|---|
| cube | OK | OK | OK | OK |
| hole | OK | OK | OK | OK |

**The parser → JSON → compiler round-trip is fully functional for both test models.**
