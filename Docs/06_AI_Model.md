# 06 — AI Model

## 1. Purpose

This document defines the role of the AI model in the CAD Copilot project.

The model converts natural language prompts into CAD JSON.

```text
User Prompt
    ↓
AI Model
    ↓
CAD JSON
```

## 2. Model Objective

The model should learn to generate valid CAD JSON from user descriptions.

Example input:

```text
Create a 100 x 50 x 10 mm rectangular plate with a centered through hole.
```

Expected output:

```json
{
  "metadata": {
    "version": "1.0",
    "unit": "mm"
  },
  "operations": []
}
```

## 3. Training Format

The training dataset should consist of prompt / target pairs.

Recommended format:

```json
{
  "prompt": "Create a rectangular plate with a centered hole.",
  "target": {
    "metadata": {
      "version": "1.0",
      "unit": "mm"
    },
    "operations": []
  }
}
```

A JSONL file may be used:

```json
{"prompt": "...", "target": {...}}
{"prompt": "...", "target": {...}}
```

## 4. Data Augmentation

One CAD JSON can have multiple natural language prompts.

Example:

```text
Prompt 1: Create a rectangular plate with a centered hole.
Prompt 2: Design a flat base plate with one circular cut-out in the middle.
Prompt 3: Generate a 100 x 50 x 10 mm plate with a through hole at the center.
```

All prompts point to the same target JSON.

This improves robustness because users can describe the same part in different ways.

## 5. Dataset Sources

The AI model should be trained on examples generated from:

- parsed `.FCStd` files;
- public FreeCAD libraries;
- GitHub repositories;
- procedurally generated parts;
- manually designed examples.

## 6. Validation During Training

The target JSON must always be valid according to the JSON specification.

Invalid examples should not be used for training.

## 7. Model Output Requirements

The model output must:

- be valid JSON;
- follow the CAD JSON specification;
- contain metadata;
- contain ordered operations;
- use supported operation types;
- avoid FreeCAD-specific internals.

## 8. Inference Pipeline

At runtime:

```text
User Prompt
    ↓
AI Model
    ↓
Raw JSON Output
    ↓
JSON Validator
    ↓
Compiler
```

If the JSON is invalid, the system should either:

- ask the model to repair it;
- return a clear error;
- request clarification from the user.

## 9. Evaluation Metrics

The model should be evaluated on:

### 9.1 JSON Validity

Percentage of outputs that are valid JSON.

### 9.2 Schema Validity

Percentage of outputs that follow the CAD JSON schema.

### 9.3 Compilation Success

Percentage of outputs that compile successfully in FreeCAD.

### 9.4 Geometry Accuracy

How close the generated CAD model is to the intended model.

### 9.5 Feature Accuracy

Whether the correct operations are generated:

- Sketch
- Pad
- Pocket
- Hole
- Fillet
- Chamfer

## 10. Initial Model Strategy

For V1, the project may start with prompting an existing LLM instead of training a model from scratch.

Possible stages:

1. Prompt engineering with a strong existing LLM.
2. Dataset creation.
3. Fine-tuning or supervised training.
4. Evaluation on unseen prompts.
5. Integration with compiler.

## 11. Long-Term Goals

Future versions may support:

- richer CAD prompts;
- multi-step user interaction;
- correction loops;
- visual feedback;
- automatic JSON repair;
- larger operation vocabulary;
- complex assemblies.
