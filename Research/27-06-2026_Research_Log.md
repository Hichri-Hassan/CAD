# Research Log

**Date:** 27 June 2026  
**Research Session:** #2

---

# Objective

## What am I trying to answer today?

Validate whether the proposed CAD architecture is actually feasible by implementing the first version of both the parser and the compiler, and determine whether a complete round-trip from a FreeCAD model to JSON and back to a FreeCAD model is possible.

---

# Initial Hypothesis

The JSON representation should contain enough information to completely reconstruct a CAD model. If the parser and compiler succeed on simple models, then the overall architecture of the project is validated and future work will mainly consist of extending the supported CAD operations.

---

# Research

## Project architecture

Today the project architecture was finalized.

The following documentation was completed:

- System Architecture
- Parser Specification
- JSON Specification
- Compiler Specification
- AI Model

These documents now define the first complete version of the CAD AI architecture.

---

## Parser

Parser V0 was implemented.

Supported operations:

- Sketch
- Pad
- Pocket
- Fillet
- Chamfer

Important architectural decisions:

- Preserve the original FreeCAD coordinate system.
- Never modify the geometry extracted from FreeCAD.
- Preserve FreeCAD face and edge selectors (Face4, Edge6, Edge7...).
- Represent holes as Sketch → Pocket.
- Support Point as a valid sketch entity.
- Ignore advanced Hole parameters (threading, countersink, drill angle...) for V1.

---

## Compiler

Compiler V0 was implemented.

Pipeline:

JSON

↓

FreeCAD Python API

↓

FCStd

The compiler executes each JSON operation sequentially inside FreeCAD and saves a new `.FCStd` document.

---

## Experiments

### Experiment 1 — Cube

Pipeline:

Original FCStd

↓

Parser

↓

CAD JSON

↓

Compiler

↓

Generated FCStd

Result:

The compiler successfully reconstructed:

- the first Sketch,
- the Pad,
- the second Sketch.

However, an important implementation issue was discovered.

The second sketch (the circle) was correctly recreated but was generated in the global coordinate system instead of being attached to the Pad face (Face4).

As a consequence:

- the circle appears outside the cube,
- the Pocket cannot remove material,
- the generated CAD model is therefore geometrically incorrect.

This strongly suggests that the compiler currently does not correctly resolve sketch supports when attaching sketches onto existing faces.

The issue appears to be a compiler implementation problem rather than a limitation of the JSON architecture.

---

### Experiment 2 — Hole model

The second model could not be compiled successfully.

The parser correctly converted the original Hole feature into a Sketch → Pocket sequence.

However, because the compiler currently cannot correctly attach sketches to existing faces, the Pocket operation cannot be executed correctly.

This experiment confirms that the remaining issues are concentrated inside the compiler rather than in the parser.

---

## Literature Review

Read the SketchGraphs paper.

Main observations:

- SketchGraphs focuses exclusively on 2D sketches.
- The dataset contains more than 15 million sketches extracted from Onshape.
- The complete 3D CAD history is intentionally discarded.
- Sketches are represented as geometric primitives connected through constraint graphs.

Interesting ideas discovered:

- Constraint graph representation for future versions.
- AI-assisted sketch autocompletion.
- Automatic constraint suggestion.
- Human designers tend to build sketches around early primitives, which become anchors for later constraints.

These ideas could become future improvements but are outside the scope of V1.

---

# Findings

## Major discovery #1 — First complete pipeline

For the first time, the project contains a complete pipeline:

FCStd

↓

Parser

↓

CAD JSON

↓

Compiler

↓

FCStd

This validates the overall architecture of the project.

---

## Major discovery #2 — Parser philosophy finalized

The parser should faithfully reproduce the CAD construction history.

It must never modify the original geometry extracted from FreeCAD.

---

## Major discovery #3 — Compiler implementation bug

The compiler successfully recreates sketches and PartDesign features.

However, sketches created on existing faces are currently generated in global coordinates instead of being attached to their support face.

Because of this:

- circles are generated outside the solid,
- Pocket operations cannot remove material,
- the generated model differs from the original one.

The architecture itself remains valid.

Only the sketch attachment implementation needs to be corrected.

---

## Major discovery #4 — SketchGraphs limitation

SketchGraphs models only sketch construction.

Our project instead aims to reconstruct the complete parametric CAD history, including every feature operation.

---

# Conclusions

Today's work validates the proposed architecture.

The project has now moved beyond the design phase.

The remaining work is no longer architectural.

It is primarily implementation and debugging of the compiler.

Current validated pipeline:

FCStd

↓

Parser

↓

CAD JSON

↓

Compiler

↓

FCStd

---

# Decisions

- Keep the current JSON architecture.
- Preserve FreeCAD coordinates exactly.
- Preserve original sketch geometry.
- Keep FreeCAD selectors (Face4, Edge7...).
- Keep Sketch → Pocket representation for holes.
- Officially support Point as a sketch entity.
- Postpone graph-based constraint representations and AI autocompletion to future versions.

---

# Next Session

1. Debug sketch attachment onto existing faces.
2. Fix Pocket generation.
3. Validate the cube round-trip completely.
4. Validate the hole model.
5. Compare generated and original feature trees.
6. Continue reading CAD AI literature (DeepCAD, Text2CAD, related work).

---

# Personal Thoughts

Today feels like one of the biggest milestones since starting the project.

For the first time, there is a functioning parser, JSON representation and compiler capable of reconstructing a CAD model.

Even though the generated model is not yet identical to the original one, the remaining issues are implementation details rather than flaws in the architecture itself.

The project now feels like a real engineering project rather than just a research idea.
