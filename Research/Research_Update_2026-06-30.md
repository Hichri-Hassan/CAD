# Research Update --- 2026-07-01

## Overview

Today's work marked the transition from parser development to **dataset
construction** for CAD Copilot. The focus shifted toward defining the
first official training dataset (V1), building an automated dataset
generation pipeline, and performing a forensic investigation of the
round-trip failures preventing complete CAD reconstruction.

------------------------------------------------------------------------

# 1. Defining the Scope of Dataset V1

A major architectural decision was made today.

Instead of attempting to support every FreeCAD model immediately, CAD
Copilot V1 will focus only on models that successfully complete the
entire pipeline:

``` text
.FCStd
    ↓
Parser
    ↓
JSON
    ↓
LLM
    ↓
Generated JSON
    ↓
Compiler
    ↓
.FCStd
```

This ensures that every training sample represents a fully executable
CAD model.

------------------------------------------------------------------------

# 2. V1 Dataset Construction

The first automated dataset generation pipeline was completed.

Initial expectations were to build V1 from the **134 fully parsed
models**.

However, introducing strict end-to-end validation revealed that only
**47 models** currently satisfy complete round-trip reconstruction.

  Stage                    Models
  ---------------------- --------
  Total dataset             3,199
  Successfully parsed         717
  Fully parsed                134
  Round-trip validated     **47**

These 47 models now constitute the first **gold-standard V1 dataset**.

------------------------------------------------------------------------

# 3. Automated Dataset Generation

A reusable pipeline was designed to automatically generate the training
dataset.

Workflow:

``` text
.FCStd
        ↓
Parser
        ↓
CAD JSON
        ↓
Summary Generation
        ↓
OpenAI API
        ↓
Prompt Generation
        ↓
Final Dataset JSON
```

Each CAD model will automatically receive:

-   Title
-   Description
-   Tags
-   Multiple natural-language prompts

while preserving the parser-generated CAD operations unchanged.

------------------------------------------------------------------------

# 4. Dataset Representation

The structure of every dataset example was finalized.

Each JSON file contains:

-   Metadata
-   Generated prompts
-   Parser-generated CAD operations

The parser output is never modified. All additional information is
generated automatically during dataset construction.

------------------------------------------------------------------------

# 5. Round-Trip Failure Investigation

A complete forensic analysis was performed on the **87 models** that are
fully parsed but fail during reconstruction.

The investigation revealed that the failures are concentrated around
only two major engineering problems.

## Failure Distribution

  Root Cause                                 Models
  ---------------------------------------- --------
  Unclosed sketch/profile                        62
  Invalid fillet/chamfer edge references         24
  Invalid operation parameters                    1

Rather than dozens of unrelated bugs, nearly all failures originate from
these recurring issues.

------------------------------------------------------------------------

# 6. Unclosed Sketches

The dominant reconstruction error is:

    Wire is not closed.

This affects **62 models (71.3%)**.

The current hypothesis is that reconstructed sketches are created
without sufficient constraint solving before Pad or Pocket operations.

Current failure sequence:

``` text
Sketch

↓

Tiny geometric gaps

↓

Profile not closed

↓

Pad / Pocket fails
```

This is now the highest-priority engineering issue.

------------------------------------------------------------------------

# 7. Topological Naming

The second major issue concerns fillet and chamfer operations.

These operations reference edges from the original CAD model.

After reconstruction, upstream geometry changes modify edge numbering,
making stored edge references invalid.

This is a topology-mapping problem rather than a parser extraction
problem.

------------------------------------------------------------------------

# 8. Prompt Generation Strategy

The final dataset generation strategy was defined.

Instead of manually writing prompts, every CAD model will be sent to the
OpenAI API.

The API will automatically generate:

-   engineering descriptions
-   multiple prompt variations
-   title
-   tags

These outputs will then be inserted directly into the dataset JSON.

This establishes a scalable dataset generation workflow for future
dataset versions.

------------------------------------------------------------------------

# 9. Literature Review

The SketchGraphs paper was reviewed.

The main conclusion is that its scope remains limited to **2D sketch
reasoning and constraint prediction**.

While valuable as a dataset contribution, it does not extend to complete
parametric CAD generation through executable feature histories.

This reinforces the long-term direction of CAD Copilot toward full CAD
history generation rather than sketch-only modeling.

------------------------------------------------------------------------

# Key Decisions

-   Freeze the architecture of Dataset V1.
-   Use only round-trip validated models.
-   Automate prompt generation using the OpenAI API.
-   Preserve parser output exactly as generated.
-   Prioritize compiler improvements before expanding parser coverage.
-   Focus next development effort on solving the "Wire is not closed"
    issue.

------------------------------------------------------------------------

# Next Steps

1.  Configure OpenAI API integration.
2.  Generate engineering-quality prompts for all V1 models.
3.  Validate prompt quality.
4.  Investigate sketch closure failures.
5.  Improve compiler reconstruction.
6.  Increase the number of round-trip validated models for Dataset V2.
