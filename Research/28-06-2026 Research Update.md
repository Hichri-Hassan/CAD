# 28-06-2026 --- Research Update

## Objective

Continue validating the parser → JSON → compiler pipeline by
investigating the incorrect reconstruction of `Hole` operations and
ensuring faithful round-trip reconstruction of FreeCAD models.

------------------------------------------------------------------------

## Initial Investigation

Although the parser was successfully producing native `Hole` operations
in the JSON representation, manual inspection of the compiled FreeCAD
models revealed that the reconstructed holes appeared to be created on
the wrong face of the Pad.

At first, the issue seemed to originate from the new `Hole` compiler
implementation. However, a deeper investigation showed that the compiler
was already creating genuine `PartDesign::Hole` objects with the correct
parameters (diameter, depth, profile, etc.).

This shifted the focus from the Hole operation itself to the
reconstruction of the underlying geometry.

------------------------------------------------------------------------

## Root Cause Analysis

A detailed comparison between the original and compiled FreeCAD models
revealed two independent issues.

### 1. Incorrect datum plane attachment

The base sketch was attached differently from the original FreeCAD
model. Although the final solid had the correct dimensions, the
resulting Pad inherited an unnecessary 90° rotation, which contributed
to topology differences.

The attachment mechanism was updated to reproduce the original FreeCAD
behaviour by attaching sketches through the Body Origin.

### 2. Topology preservation

The most important discovery of the day was that identical geometry does
**not** necessarily imply identical topology.

Originally, rectangle entities were reconstructed independently from
their original creation order. Even though the resulting Pad looked
geometrically identical, OpenCascade generated a different internal
topology, causing face indices to change.

As a consequence:

-   `Face4` in the original model corresponded to the top face.
-   `Face4` in the compiled model corresponded to a different physical
    face.

Since  operations reference faces by index, every feature
attached to `Face4` (Hole, Chamfer, Fillet, etc.) was applied to the
wrong location.

------------------------------------------------------------------------

## Solution

Instead of trying to remap face indices manually, the compiler was
modified to reproduce the original construction process as faithfully as
possible.

The following changes were implemented:

-   Base sketches are attached through `(Origin, Plane)` exactly as in
    the original model.
-   The parser no longer collapses rectangles into a high-level
    `Rectangle` entity.
-   Sketch geometry is emitted in the exact order found in FreeCAD's
    `GeometryList`.
-   The compiler reconstructs sketch entities using this original
    ordering.

As a result, OpenCascade naturally reconstructs the same topology and
therefore produces the same face numbering as the source model.

------------------------------------------------------------------------

## Validation

The updated pipeline was manually verified by comparing the original and
reconstructed FreeCAD models.

The following properties now match:

-   Feature tree structure
-   Pad topology
-   Face numbering
-   Sketch attachments
-   Hole placement
-   Hole orientation
-   Chamfer and Fillet references (tested models)

Visual inspection also confirmed that holes are now generated on the
correct physical faces.

------------------------------------------------------------------------

## Main Outcome

Today's work transformed the compiler from a geometry-preserving system
into a significantly more faithful reconstruction pipeline.

The key insight is that preserving CAD topology requires reproducing the
original construction history, not only the final geometry. Maintaining
the original sketch construction order proved essential for preserving
downstream feature references.

This represents a major architectural improvement for the project, as
future CAD operations relying on face references (Hole, Pocket, Chamfer,
Fillet, etc.) can now be reconstructed much more reliably.

------------------------------------------------------------------------

## Remaining Work

-   Apply parsed sketch constraints during compilation.
-   Support advanced Hole parameters (threads, countersinks, etc.).
-   Evaluate topology preservation on a larger and more diverse
    collection of FreeCAD models.
-   Continue expanding parser/compiler support for additional PartDesign
    operations.
