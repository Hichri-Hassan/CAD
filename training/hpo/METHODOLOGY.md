# Hierarchical LoRA Hyperparameter Optimization — Methodology

This document describes the research-informed HPO strategy used for CAD Copilot V1.

## Problem context

| Property | Value |
|---|---|
| Training models | 40 |
| Prompt → CAD examples | 200 |
| Task | Structured JSON generation (`operations` array) |
| Base model | `Qwen/Qwen2.5-3B-Instruct` |
| Adaptation | LoRA |

Small, highly specialized datasets amplify the effect of **capacity** (LoRA rank) and **learning rate**, while making **overfitting** (epochs, dropout) a secondary concern. **LoRA alpha** primarily scales adapter magnitude relative to rank and is therefore tuned last.

## Strategy: hierarchical search

Rather than a full grid over all hyperparameters (which grows multiplicatively), we optimize in three stages:

### Stage 1 — Primary (9 runs)

| Parameter | Range | Rationale |
|---|---|---|
| `lora_r` | 8, 16, 32 | Controls adapter capacity; small datasets often need moderate rank |
| `learning_rate` | 1e-4, 2e-4, 3e-4 | Dominates convergence on instruction-style JSON tasks |

All other searchable parameters remain at defaults.

### Stage 2 — Secondary (12 runs)

Freeze the best Stage 1 configuration, then search:

| Parameter | Range | Rationale |
|---|---|---|
| `num_epochs` | 2, 3, 5, 8 | 200 examples risk overfitting with too many epochs |
| `lora_dropout` | 0.0, 0.05, 0.1 | Regularization for small specialized data |

### Stage 3 — Fine adjustment (3 runs)

Freeze the best Stage 1 + Stage 2 configuration, then search:

| Parameter | Range | Rationale |
|---|---|---|
| `lora_alpha` | 16, 32, 64 | Lower impact once rank and LR are fixed |

**Total planned experiments: 24** (9 + 12 + 3)

## Fixed parameters

Held constant across all stages unless future evidence suggests otherwise:

- `weight_decay`
- `max_seq_length`
- `optimizer` (`adamw_torch`)
- `scheduler` (`cosine`)
- `target_modules` (all attention + MLP projections)
- batch size and gradient accumulation

## Selection criterion

Each stage selects the best run by **minimum validation loss** (`val_loss`). The metrics framework supports plugging in CAD-specific scores later (JSON validity, compilation success, etc.).

## Reproducibility

Every run records:

- random seed
- full hyperparameter configuration
- dataset version (`dataset_v1_train_200`)
- model version (`Qwen/Qwen2.5-3B-Instruct`)
- LoRA configuration and checkpoint path

## Usage

```bash
# Preview search strategy
python3 training/scripts/plan_hpo.py --summary-only

# Prepare all experiment directories (no training)
python3 training/scripts/plan_hpo.py

# Inspect experiment status after training (future)
python3 training/scripts/summarize_hpo.py
```

## Extensibility

- Add hyperparameters by extending `training/configs/hpo_stages.yaml`
- Add CAD metrics by implementing `CADMetricsEvaluator` in `training/hpo/metrics.py`
- Add new stages without rewriting the optimizer
