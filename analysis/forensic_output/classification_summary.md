# Forensic Dataset Classification Report

*Generated: 2026-06-30 20:01 UTC*

## Executive Summary

This report explains **why the current CAD Copilot parser succeeds on only 22.4%** of the collected FreeCAD-library dataset. The analysis inspects raw `Document.xml` structure for every `.FCStd` file without modifying the parser.

- **Total models:** 3,199
- **Parser success (≥1 operation extracted):** 717 (22.4%)
- **Parser failures:** 2,482 (77.6%)

### Key Finding

The low parser coverage is **primarily a dataset heterogeneity problem**, not a large-scale parser bug. Most files were never authored as single-body PartDesign documents matching the parser's assumptions.

## 1. Dataset Composition

| Document Category | Count | Percentage |
|---|---:|---:|
| Part Workbench Model | 2,232 | 69.8% |
| PartDesign Part | 659 | 20.6% |
| Unknown | 208 | 6.5% |
| Multi-body PartDesign | 98 | 3.1% |
| Assembly | 2 | 0.1% |

## 2. Distribution of FreeCAD Object Types

Complete inventory: `object_type_distribution.csv`. Top types:

| TypeId | Count |
|---|---:|
| `Sketcher::SketchObject` | 8,370 |
| `App::Plane` | 5,802 |
| `App::Line` | 5,802 |
| `PartDesign::Pad` | 2,617 |
| `PartDesign::Pocket` | 2,174 |
| `Part::FeaturePython` | 2,101 |
| `App::Origin` | 1,942 |
| `Part::Extrusion` | 1,832 |
| `App::FeaturePython` | 1,459 |
| `App::DocumentObjectGroup` | 1,350 |
| `Part::Feature` | 1,332 |
| `PartDesign::Body` | 1,261 |
| `Part::Cylinder` | 780 |
| `PartDesign::Fillet` | 777 |
| `Part::Part2DObjectPython` | 766 |
| `PartDesign::Groove` | 726 |
| `App::Part` | 681 |
| `Spreadsheet::Sheet` | 576 |
| `Part::MultiFuse` | 533 |
| `Part::Cut` | 507 |

## 3. Why the Parser Fails

| Failure Reason | Count | Percentage |
|---|---:|---:|
| Part Workbench instead of PartDesign | 2,218 | 69.3% |
| No PartDesign Body | 209 | 6.5% |
| Multiple PartDesign Bodies | 18 | 0.6% |
| Assembly structure | 15 | 0.5% |
| Unknown | 14 | 0.4% |
| PartDesign Body not named 'Body' | 8 | 0.3% |

## 4. Structural Metrics

| Metric | Value |
|---|---:|
| Files with any PartDesign::Body | 757 (23.7%) |
| Files with exactly one body (PartDesign Part category) | 659 (20.6%) |
| Files with body literally named `Body` | 735 (23.0%) |
| Files with multiple PartDesign bodies | 98 (3.1%) |
| Assembly-classified files (primary) | 2 (0.1%) |
| Files also tagged Assembly (incl. multi-body) | 83 (2.6%) |
| Part Workbench models (no PartDesign body) | 2,234 (69.8%) |
| Imported STEP/BREP style files | 102 (3.2%) |

## 5. Answering the Coverage Questions

### Are most failures caused by unsupported operations?

**No.** Only **0** files (0.0%) fail because of unsupported PartDesign features inside an otherwise valid body tree. The largest single cause is **No PartDesign Body** (209 files, 6.5%), followed by **Part Workbench instead of PartDesign** (2,218 files, 69.3%).

### Are many files not PartDesign documents?

**Yes.** **2,442** files (76.3%) contain no `PartDesign::Body` at all. These are predominantly Part workbench models built from `Part::Extrusion`, `Sketcher::SketchObject`, and grouped feature trees.

### Are many files assemblies?

**Some, but not the dominant failure mode.** **2** files (0.1%) are classified as assemblies. Multi-body PartDesign files add another **98** (3.1%).

### Does the parser fail because multiple bodies are present?

**Partially.** **18** files (0.6%) contain multiple `PartDesign::Body` objects. Additionally, **8** files (0.3%) have a PartDesign body that is not named `Body`, which the current parser does not read.

### Is the dataset heterogeneous?

**Yes.** The FreeCAD-library collection mixes PartDesign parametric models, Part workbench history trees, multi-body templates, architectural BIM objects, imported solids, and grouped sub-assemblies. The parser was designed for single-body PartDesign feature trees.

## 6. Parser Assumptions vs Dataset Reality

The current parser (`parser/fcstd_reader.py`) assumes:

1. A PartDesign object named exactly `Body` exists.
2. Features are stored in that body's `Group` property in order.
3. Feature types belong to a small supported subset (Sketch, Pad, Pocket, Hole, Fillet, Chamfer).

Forensic inspection shows:

- Only **735/3,199** files (23.0%) have a body named `Body`.
- Only **757/3,199** files (23.7%) contain any PartDesign body.
- Only **717/3,199** files (22.4%) yield extractable operations under these assumptions.

## 7. Recommendations

1. **Filter the training corpus** to single-body PartDesign files (`PartDesign Part` category) for initial model development — approximately **659** candidates.
2. **Extend body discovery** to enumerate all `PartDesign::Body` objects by type, not by name `Body`.
3. **Prioritize parser extensions** based on `unsupported_operations.csv`: Groove, Polar Pattern, Mirror, Revolution.
4. **Treat Part workbench files separately** — they require a different extraction pipeline, not PartDesign parsing.
5. **Do not expect 100% coverage** on FreeCAD-library without supporting multiple workbenches.

## 8. Output Files

- `document_classification.csv` — per-file category and parser status
- `failure_reason_distribution.csv` — aggregated failure reasons
- `object_type_distribution.csv` — complete TypeId inventory
- `body_statistics.csv` — per-body feature counts and depth
