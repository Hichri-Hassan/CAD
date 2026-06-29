# test.FCStd Round-Trip Diagnosis

## Symptom

In the rebuilt model (`test_compiled.FCStd`), the two Hole features appear almost collapsed together (~3.3 mm apart). In the original `test.FCStd`, they are ~16.8 mm apart.

## Verdict

| Hypothesis | Result | Evidence |
|---|---|---|
| **A) Parser extracts wrong coordinates** | **Rejected** | Circle centers in `test.json` match `Document.xml` `GeometryList` exactly |
| **B) JSON schema loses sketch frame data** | **Confirmed** | `AttachmentOffset` is present in XML but absent from JSON |
| **C) Compiler treats local coords as global** | **Rejected** | Compiler adds geometry in sketch-local 2D; first hole matches perfectly |
| **D) Compiler fails attachment/placement** | **Confirmed** | Compiler restores plane/support but never sets `AttachmentOffset` |

**Root cause:** `AttachmentOffset` is not parsed, not stored in JSON, and not restored by the compiler. Local sketch geometry is correct; the sketch **coordinate frame origin** is wrong for sketches that use a non-zero offset.

This is **not** a local-vs-global coordinate confusion bug. The compiler correctly uses local sketch coordinates — but without restoring `AttachmentOffset`, two sketches on the same datum plane share the same origin even when the original model offset one sketch by 20 mm.

---

## 1. Document.xml vs test.json — Geometry

### op_005 / Sketch002 (first Hole profile)

| Field | Document.xml | test.json |
|---|---|---|
| Circle center | (-25.850, 27.721) | (-25.85, 27.721) |
| Radius | 5.653 | 5.653 |
| AttachmentSupport | `(Origin, XZ_Plane)` | `"plane": "XZ"` |
| AttachmentOffset | (0, 0, 0) | **missing** |

### op_007 / Sketch003 (second Hole profile)

| Field | Document.xml | test.json |
|---|---|---|
| Circle center | (-29.085, 28.570) | (-29.085, 28.57) |
| Radius | 5.239 | 5.239 |
| AttachmentSupport | `(Origin, XZ_Plane)` | `"plane": "XZ"` |
| AttachmentOffset | **(20, -1, 0)** | **missing** |

Local geometry extraction is faithful. The ~3.3 mm distance between the two circle centers in sketch-local space is expected; the original model separates them globally via `AttachmentOffset`.

### op_003 / Sketch001 (Pocket profile) — secondary drift

| Field | Document.xml | test.json |
|---|---|---|
| AttachmentSupport | `(Origin, XY_Plane)` | `"plane": "XY"` |
| AttachmentOffset | **(0, 7, 19)** | **missing** |

Pocket profile centroid global position:
- Original: (-17.601, **7.000**, **19.000**)
- Compiled: (-17.601, **0.000**, **0.000**)

---

## 2. Sketch placement data from Document.xml

| Sketch | op_id | Support | AttachmentOffset | Placement base | MapMode | MapReversed |
|---|---|---|---|---|---|---|
| Sketch | op_001 | Origin / XZ_Plane | (0,0,0) | (0,0,0) + 90° Z rot | FlatFace (5) | false |
| Sketch001 | op_003 | Origin / XY_Plane | **(0,7,19)** | (0,7,19) | FlatFace (5) | false |
| Sketch002 | op_005 | Origin / XZ_Plane | (0,0,0) | (0,0,0) + 90° Z rot | FlatFace (5) | false |
| Sketch003 | op_007 | Origin / XZ_Plane | **(20,-1,0)** | (20,0,-1) + 90° Z rot | FlatFace (5) | false |

`Placement` in FreeCAD is the **computed** result of attachment support + `AttachmentOffset` + `MapMode`. The compiler must restore `AttachmentOffset` (not manually set `Placement`) so FreeCAD recomputes the frame correctly.

---

## 3. JSON schema gap

Current Sketch JSON fields:
```json
{
  "entities": [...],
  "constraints": [...],
  "plane": "XZ"
}
```

Missing fields required for faithful round-trip:
- `attachment_offset` — `{ "position": [x,y,z], "rotation": [qx,qy,qz,qw] }` or euler
- optionally `map_mode`, `map_reversed` (both are defaults here)

`support` (face reference) is already supported for face-attached sketches but not needed for this model.

---

## 4. Compiler behavior

`compiler/operations/sketch.py` currently:
1. Creates sketch object
2. Sets `MapMode = "FlatFace"` and `AttachmentSupport` (plane or face) ✓
3. Calls `doc.recompute()` ✓
4. Adds entities in local 2D coordinates ✓
5. **Does not set `AttachmentOffset`** ✗

---

## 5. Measured global hole positions (FreeCAD)

| | Hole 1 global | Hole 2 global | Distance between holes |
|---|---|---|---|
| **Original** | (-25.850, 0.000, 27.721) | (-9.085, 0.000, 27.570) | **16.766 mm** |
| **Compiled** | (-25.850, 0.000, 27.721) | (-29.085, 0.000, 28.570) | **3.345 mm** |

Hole 1 matches exactly (zero offset). Hole 2 is shifted by exactly the missing offset:
- Expected delta from offset (20,-1,0) on XZ plane → global X shift ≈ +20 mm
- Actual drift: (-29.085) − (-9.085) = **-20 mm** in X (sign convention handled by plane rotation)

---

## 6. Where drift is introduced

```
Document.xml  ──parser──►  test.json  ──compiler──►  test_compiled.FCStd
     │                         │                          │
     │  geometry ✓             │  geometry ✓              │  geometry ✓
     │  attachment_offset ✓    │  attachment_offset ✗     │  attachment_offset ✗
     │                         │                          │
     └─────────────────────────┴── DRIFT INTRODUCED HERE ─┘
                          (parser → JSON schema gap)
                                    +
                          (compiler cannot restore what JSON lacks)
```

---

## 7. Recommended fix (not yet applied)

1. **Parser** — extract `AttachmentOffset` from each `Sketcher::SketchObject`
2. **JSON schema** — add optional `attachment_offset` to Sketch operations
3. **Compiler** — after setting `AttachmentSupport`, set `sketch.AttachmentOffset` from JSON, then `recompute()` before adding geometry
4. **Regression** — re-run `test.FCStd` round-trip; verify hole distance = 16.766 mm and pocket centroid Y/Z = 7/19

Debug scripts:
- `output/debug_test_roundtrip.py`
- `output/debug_pocket_offset.py`
- `output/validate_test_roundtrip.py`

---

## Fix Applied (2026-06-28)

Parser now extracts `attachment_offset`; compiler restores `sketch.AttachmentOffset` before recompute.

**Validation on test.FCStd → rebuilt.FCStd — all PASS:**
- Hole distance: 16.766 mm (original and rebuilt)
- Pocket centroid: (-17.601, 7.000, 19.000) (original and rebuilt)
