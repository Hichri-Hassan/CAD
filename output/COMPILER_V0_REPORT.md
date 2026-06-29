# Compiler V0 Report

> **Updated:** See [`ROUND_TRIP_REPORT.md`](ROUND_TRIP_REPORT.md) for the latest validation results after the Hole/Pocket architecture change and face attachment fix.

## Summary

Compiler V0 converts CAD JSON into FreeCAD `.FCStd` models using the FreeCAD Python API via `freecadcmd`.

**Usage:**

```bash
python3 -m compiler output/cube.json -o output/cube_compiled.FCStd
```

Both `Pocket` and `Hole` are supported as first-class operations. Holes are compiled as native `PartDesign::Hole` features.

---

## Latest Compilation Results

| Input | Output | Result |
|---|---|---|
| `cube.json` | `output/cube_compiled.FCStd` | **Success** |
| `hole.json` | `output/hole_compiled.FCStd` | **Success** |

Both files open in FreeCAD with all features `Up-to-date` and no document errors.

---

## Implementation

```
compiler/
  loader.py              # JSON loading and validation
  runner.py              # Document orchestration
  freecad_main.py        # Entry point inside FreeCAD
  freecad_launcher.py    # Locates and invokes freecadcmd
  operations/
    sketch.py            # Sketch + entity creation (face attachment fix)
    pad_pocket.py        # Pad and Pocket
    hole.py              # Native PartDesign::Hole
    fillet_chamfer.py    # Fillet and Chamfer
```

FreeCAD binary: `/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd`

---

## Face Attachment Fix

Face-based sketches now recompute the document after setting `AttachmentSupport` and before adding geometry. This ensures sketches attach to the correct face (e.g. `Face4` on a Pad) rather than appearing in global coordinates.

---

## Unsupported Cases (V0)

| Case | Behavior |
|---|---|
| Sketch constraints | Ignored |
| Advanced Hole parameters | Ignored |
| Multiple edge selection on Fillet/Chamfer | First edge only |
| Empty edge list on Fillet/Chamfer | Warning logged |

See [`ROUND_TRIP_REPORT.md`](ROUND_TRIP_REPORT.md) for full details on remaining issues and round-trip validation.
