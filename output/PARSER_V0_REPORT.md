# Parser V0 Report (Final Architecture)

## Summary of Changes

This update finalizes the Parser V0 architecture and aligns all documentation with the implementation.

| Decision | Status |
|---|---|
| `Point` as supported sketch entity | Added to JSON spec and parser (already implemented) |
| Preserve original sketch geometry | Documented and enforced — parser never rewrites entities |
| Sketch → Pocket for holes | Unchanged — `PartDesign::Hole` converted to `Pocket` |
| Ignore advanced Hole parameters | Documented — threads, countersinks, etc. dropped in V0 |
| Diagnostics outside CAD JSON | Unchanged — CLI only |

### Documentation updated

- `Docs/02_Parser_Specification.md` — removed standalone Hole operation; added Point entity, geometry preservation rule, Hole→Pocket conversion, ignored advanced Hole params
- `Docs/03_JSON_Specification.md` — removed Hole operation type; added Point entity (§7.5); updated face selector examples to use `Face4`
- `Docs/05_Compiler_Specification.md` — replaced Hole section with Pocket-based holes; added Point to sketch entities
- `Docs/01_System_Architecture.md` — V1 scope updated to Sketch→Pocket for holes
- `Docs/06_AI_Model.md` — feature accuracy list updated

### Inconsistencies fixed

- **Hole operation type** was still listed in parser, JSON, architecture, and AI model docs despite being removed from the implementation. All references now use Sketch → Pocket.
- **Face selector examples** used semantic `"top"` in JSON spec while the parser preserves FreeCAD names like `Face4`. Examples updated to match implementation.
- **Point entity** was exported by the parser but missing from the JSON spec. Now formally specified.

---

## Regenerated Test Outputs

### `cube.json` — valid, 4 operations

```text
Sketch (Rectangle on XZ)
  → Pad (32 mm)
  → Sketch (Circle r=6.92 on Face4)
  → Pocket (depth 10 mm)
```

Note: circle radius 6.92 mm is preserved from FreeCAD sketch geometry (Hole diameter parameter 6.0 mm is not used).

### `hole.json` — valid, 6 operations

```text
Sketch (Rectangle on XZ)
  → Pad (10 mm)
  → Sketch (Point on Face4)
  → Pocket (depth 16 mm)
  → Chamfer (1 mm, Edge7)
  → Fillet (1 mm, Edge6)
```

---

## Remaining Notes

- **Chamfer/Fillet edge references** resolve to the converted Pocket operation ID, not the original FreeCAD Hole object name. This is consistent with the operation sequence in the CAD JSON.
- **Point-based holes** require compiler support to interpret a `Point` entity plus `Pocket` as a circular cut. This is documented in the compiler specification as future compiler work, not parser work.
