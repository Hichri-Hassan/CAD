# Research Update — 29-06-2026

## Summary

Today was a major transition point for the CAD Copilot project. The work moved from isolated parser/compiler debugging toward the construction of a scalable CAD dataset pipeline.

The main achievements were:

- diagnosing and fixing a real geometric round-trip bug caused by missing `AttachmentOffset` data,
- validating that the fix is backward-compatible on previous test models,
- collecting and extracting more than 3,000 native `.FCStd` files,
- building the first stage of the dataset infrastructure with stable IDs, deduplication, and indexing.

---

## 1. Round-trip bug investigation

A new stress test was created using a FreeCAD model containing:

- one base Pad,
- one Pocket in the middle,
- two Hole features placed far apart visually.

After parsing and recompiling the model, the two holes appeared almost collapsed together in the rebuilt model. At first, the suspected cause was that the compiler might be interpreting sketch-local coordinates as global coordinates.

After inspecting `Document.xml`, `test.json`, and the compiler behavior, the actual issue was identified more precisely.

### Final diagnosis

The bug was **not** caused by local coordinates being treated as global coordinates.

Instead, the problem was that the JSON representation preserved the local sketch geometry but lost the sketch frame information, especially `AttachmentOffset`.

The parser correctly extracted the circle centers from `Document.xml`:

| Sketch | XML circle center | JSON center |
|---|---|---|
| Sketch002 / op_005 | `(-25.850, 27.721)` | `(-25.85, 27.721)` |
| Sketch003 / op_007 | `(-29.085, 28.570)` | `(-29.085, 28.57)` |

The issue was that the second hole sketch had a non-zero `AttachmentOffset`:

```text
Sketch003 AttachmentOffset = (20, -1, 0)
```

This offset was responsible for separating the two holes in the original model. Since the JSON did not store it, the compiler recreated both hole sketches around the same origin.

---

## 2. AttachmentOffset fix

The following changes were implemented by Cursor.

### Parser

Files modified:

- `parser/utils/xml_helpers.py`
- `parser/extractors/sketch.py`

Changes:

- added helpers for extracting placement information,
- added support for exporting non-identity `AttachmentOffset`,
- preserved local sketch geometry unchanged.

### JSON schema

Files modified:

- `Docs/03_JSON_Specification.md`
- `compiler/loader.py`

New optional Sketch field:

```json
"attachment_offset": {
  "position": [x, y, z],
  "rotation": [qx, qy, qz, qw]
}
```

### Compiler

File modified:

- `compiler/operations/sketch.py`

Change:

- the compiler now restores `sketch.AttachmentOffset` after setting `AttachmentSupport` / `MapMode` and before recomputation and geometry creation.

---

## 3. Validation results

The corrected pipeline was tested on the difficult `test.FCStd` model.

### Parsed offsets

| Sketch | AttachmentOffset |
|---|---|
| op_003 / Pocket sketch | `[0, 7, 19]` |
| op_007 / Hole 2 sketch | `[20, -1, 0]` |

### Round-trip validation

| Check | Original | Rebuilt |
|---|---|---|
| Hole distance | `16.766 mm` | `16.766 mm` |
| Hole 1 global position | `(-25.850, 0, 27.721)` | match |
| Hole 2 global position | `(-9.085, 0, 27.570)` | match |
| Pocket centroid | `(-17.601, 7.000, 19.000)` | match |

The rebuilt model visually matched the original. The two holes were no longer collapsed.

---

## 4. Regression testing on previous models

After the `AttachmentOffset` fix, the previous simpler test cases were rerun to ensure backward compatibility.

Models tested:

- `cube.FCStd`
- `hole.FCStd`

Both models passed.

### Regression results

| Model | Result |
|---|---|
| cube | PASS |
| hole | PASS |

Important observations:

- identity offsets are omitted from JSON as expected,
- the compiler defaults missing offsets to zero,
- Pad geometry remained correct,
- Hole diameter and depth remained correct,
- Chamfer and Fillet references still resolved correctly,
- final body bounding boxes and volumes matched.

Conclusion: the `AttachmentOffset` fix is backward-compatible.

---

## 5. Dataset strategy discussion

The project direction was refined.

Instead of trying to support every FreeCAD operation immediately, the strategy is now:

1. collect a large raw corpus of native `.FCStd` files,
2. keep all raw models, even unsupported ones,
3. build a dataset builder that classifies models by operations used,
4. train only on validated models using supported operations,
5. later, when new operations are supported, rerun the dataset builder and automatically unlock more models.

Current supported operations:

- Sketch
- Pad
- Pocket
- Hole
- Fillet
- Chamfer

The main idea is to separate:

```text
Raw dataset collection
        ↓
Dataset qualification
        ↓
Validated training dataset
```

This makes the dataset reusable and expandable over time.

---

## 6. GitHub data collection

A first external dataset source was downloaded using Git sparse checkout:

```text
FreeCAD/Examples → 100CadExercises
```

Then a larger source was downloaded:

```text
FreeCAD/FreeCAD-library
```

The FreeCAD Library contained thousands of native FreeCAD files.

A command confirmed the scale of the repository:

```bash
find . -name "*.FCStd" | wc -l
```

Initial count:

```text
2716 .FCStd files
```

Later, after recursive extraction and case-insensitive scanning, the extraction pipeline found:

```text
3201 .FCStd files
3199 unique models
2 duplicates
```

---

## 7. Dataset extraction pipeline

Cursor implemented the first stage of the dataset pipeline under the `dataset/` package.

### Modules

| Module | Role |
|---|---|
| `scanner.py` | recursively finds `.FCStd` files |
| `hasher.py` | computes SHA-256 hashes |
| `extract.py` | orchestrates scanning, deduplication, copying, and indexing |
| `index_writer.py` | writes `index.csv` and `duplicates.csv` |
| `models.py` | shared data structures |
| `cli.py` | command-line entry point |

### Command used

```bash
python3 -m dataset extract /path/to/repository \
  -o examples \
  --repository-name FreeCAD-library
```

### Extraction results

```text
Repository scanned : FreeCAD-library
FCStd files found  : 3201
Unique models      : 3199
Duplicate models   : 2
Copied             : 3199
Index generated    : examples/index.csv
Duplicates report  : examples/duplicates.csv
```

### Output structure

The extraction created:

- `000001.FCStd` to `003199.FCStd`
- `index.csv`
- `duplicates.csv`

Each copied file receives a stable sequential ID.

Example future mapping:

```text
000001.FCStd
000001.json
000001_rebuilt.FCStd
000001_report.json
000001_prompts.json
```

This ID-based naming avoids filename collisions and makes the dataset scalable.

---

## 8. Index design

The dataset index records the origin of every model.

Important fields include:

- `id`
- `original_filename`
- `repository_name`
- `original_relative_path`
- `copied_filename`
- `file_size_bytes`
- `sha256_hash`
- `is_canonical`

This is useful because the dataset files are renamed to stable IDs, but the original provenance is still preserved.

The SHA-256 hash is used to detect duplicate models, even when filenames or paths differ.

---

## 9. Current project status

The project now has:

- a working FreeCAD parser,
- a working compiler,
- support for Sketch, Pad, Pocket, Hole, Fillet, and Chamfer,
- correct handling of `AttachmentOffset`,
- validated round-trip tests on difficult and simple models,
- an extraction pipeline for raw `.FCStd` datasets,
- around 3,300 collected native FreeCAD models,
- stable dataset IDs,
- duplicate detection,
- provenance tracking through `index.csv`.

This marks a shift from a parser-only project to an end-to-end CAD dataset infrastructure project.

---

## 10. Next steps

The next major milestone should be the Dataset Builder.

Its job will be to process every collected `.FCStd` file:

```text
raw .FCStd
    ↓
open / inspect
    ↓
extract operations
    ↓
check supported operations
    ↓
parse to JSON
    ↓
compile back to FreeCAD
    ↓
validate geometry
    ↓
generate report
```

Expected outputs:

- `parsed_json/`
- `rebuilt_fcstd/`
- `reports/`
- operation histogram,
- supported vs unsupported model count,
- parser success rate,
- compiler success rate,
- round-trip success rate.

This will allow the project to identify which models are immediately usable for AI training and which operations should be implemented next.

---

## Key takeaway

Today's main result was not just fixing a bug or collecting files.

The important result is that the project now has the foundation for a scalable, reproducible CAD dataset pipeline.

The central architecture is now:

```text
Raw FCStd repositories
        ↓
Extraction + indexing
        ↓
Dataset Builder
        ↓
Validated JSON dataset
        ↓
AI training data
```

This is a strong foundation for the next stage of the CAD Copilot project.
