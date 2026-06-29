# Cube / Hole Regression Report

**Date:** 2026-06-28  
**Change under test:** `attachment_offset` parser/compiler fix  
**Pipeline:** `cube.FCStd` / `hole.FCStd` → parser → JSON → compiler → `*_rebuilt.FCStd`

## Summary

| Model | Result |
|---|---|
| cube | **PASS** |
| hole | **PASS** |

No regressions detected. The `attachment_offset` change is backward-compatible for models where all sketch offsets are identity (field omitted from JSON).

---

## Outputs

| Model | JSON | Rebuilt FCStd |
|---|---|---|
| cube | `output/cube.json` | `output/cube_rebuilt.FCStd` |
| hole | `output/hole.json` | `output/hole_rebuilt.FCStd` |

---

## cube.FCStd

| Check | Result |
|---|---|
| `attachment_offset` in JSON | Absent (all identity) — correct |
| Feature order | Sketch → Pad → Sketch → Hole |
| Pad face signatures | Match original |
| Pad bounding box | Match original |
| Sketch plane/support | Origin/XZ_Plane + Pad/Face4 |
| Sketch attachment offset | All zero |
| Hole global position | (-15.805, -16.235, 30.891) — match |
| Hole diameter / depth | Ø6.0 mm, depth 10.0 mm — match |
| Final body bbox / volume | Match original |
| Document errors | None |

---

## hole.FCStd

| Check | Result |
|---|---|
| `attachment_offset` in JSON | Absent (all identity) — correct |
| Feature order | Sketch → Pad → Sketch → Hole → Chamfer → Fillet |
| Pad face signatures | Match original |
| Pad bounding box | Match original |
| Sketch plane/support | Origin/XZ_Plane + Pad/Face4 |
| Sketch attachment offset | All zero |
| Hole global position | (-23.851, -5.460, 34.196) — match |
| Hole diameter / depth | Ø6.0 mm, depth 16.0 mm — match |
| Chamfer Edge7 / Fillet Edge6 | Up-to-date, selectors resolve |
| Final body bbox / volume | Match original |
| Document errors | None |

---

## Conclusion

The `attachment_offset` fix does not regress cube or hole models. Identity offsets are correctly omitted at parse time and default to zero at compile time, preserving the previously validated topology and geometry.

Validation script: `output/validate_cube_hole_regression.py`
