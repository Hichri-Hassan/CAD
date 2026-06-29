# 01 — System Architecture

## 1. Purpose

This document defines the global architecture of the CAD Copilot project.

The project aims to build a pipeline that transforms a natural language request into a parametric CAD model using a structured intermediate JSON representation.

## 2. High-Level Pipeline

```text
User Prompt
    ↓
AI Model
    ↓
CAD JSON
    ↓
JSON Validator
    ↓
Compiler
    ↓
FreeCAD API
    ↓
.FCStd / .STEP
```

## 3. Core Components

### 3.1 AI Model

The AI model receives a natural language prompt and generates a CAD JSON file.

Input:

```text
Create a rectangular plate with a centered hole.
```

Output:

```json
{
  "metadata": {
    "unit": "mm",
    "version": "1.0"
  },
  "operations": []
}
```

The AI model does not directly generate FreeCAD Python code.

### 3.2 CAD JSON

The CAD JSON is the central intermediate representation of the project.

It describes the design intent and construction history of a CAD model.

It should be:

- software-independent;
- easy to validate;
- easy to generate with an LLM;
- easy to compile into FreeCAD operations.

### 3.3 Validator

The validator checks whether the CAD JSON is valid before execution.

It verifies:

- required fields;
- supported operation types;
- valid units;
- positive dimensions;
- valid references between operations;
- correct construction order.

Invalid JSON must not be sent to the compiler.

### 3.4 Compiler

The compiler converts CAD JSON into FreeCAD API calls.

Input:

```text
CAD JSON
```

Output:

```text
FreeCAD model + STEP export
```

The compiler should not make design decisions. It only executes the JSON.

### 3.5 FreeCAD

FreeCAD is used as the geometry engine.

It is responsible for:

- creating sketches;
- applying pads, pockets, holes, fillets, and chamfers;
- saving `.FCStd`;
- exporting `.STEP`.

### 3.6 Parser

The parser is used to build the dataset.

It converts existing `.FCStd` files into CAD JSON.

```text
.FCStd
    ↓
Parser
    ↓
CAD JSON
```

The parser is not used during normal user inference. It is mainly used offline for dataset creation.

### 3.7 Dataset Builder

The dataset builder transforms parsed CAD JSON files into training examples.

```text
CAD JSON
    ↓
Prompt Generation
    ↓
Training Dataset
```

One CAD JSON can be associated with multiple natural language prompts for data augmentation.

## 4. Offline Dataset Pipeline

```text
Existing .FCStd files
    ↓
Parser
    ↓
CAD JSON
    ↓
Prompt Generator
    ↓
Prompt / JSON pairs
    ↓
Training Dataset
```

## 5. Runtime Inference Pipeline

```text
User Prompt
    ↓
AI Model
    ↓
CAD JSON
    ↓
Validator
    ↓
Compiler
    ↓
FreeCAD
    ↓
.FCStd / .STEP
```

## 6. Design Principles

### 6.1 JSON over DSL

The project uses JSON instead of a custom DSL because JSON is easier to validate, parse, store, and generate using LLMs.

### 6.2 Design Intent over FreeCAD Internals

The JSON must represent the CAD design intent, not FreeCAD-specific implementation details.

Good:

```json
{
  "type": "Pad",
  "length": 20
}
```

Bad:

```json
{
  "FreeCADObjectName": "Pad001",
  "Visibility": true
}
```

### 6.3 Separation of Responsibilities

Each component has one clear role:

| Component | Role |
|---|---|
| AI Model | Generate CAD JSON |
| Validator | Check JSON correctness |
| Compiler | Execute JSON in FreeCAD |
| Parser | Extract JSON from existing `.FCStd` files |
| Dataset Builder | Build training examples |

## 7. V1 Scope

The first version supports only simple parametric CAD operations:

- Sketch
- Pad
- Pocket
- Hole
- Fillet
- Chamfer

Both `Pocket` and `Hole` are first-class CAD operations.

Assemblies, simulations, rendering, materials, complex surfaces, and advanced constraints are out of scope for V1.

## 8. Final Goal

The final system should allow a user to write:

```text
Create a 100 x 50 x 10 mm plate with a centered through hole and rounded edges.
```

And obtain:

- a valid CAD JSON;
- a valid FreeCAD model;
- an editable `.FCStd` file;
- an exportable `.STEP` file.
