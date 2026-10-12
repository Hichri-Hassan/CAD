# STAGE3 HPO Report (LoRA Alpha Search)

Generated: 2026-07-30T15:18:06.034328+00:00

## Comparison Table

| Experiment | Alpha | LoRA r | LR | Epochs | Train Loss | Val Loss | Time (s) | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| stage3/run_003 | 64 | 8 | 3e-04 | 8 | 0.0446 | 0.0054 | 86461.03239130974 | completed |
| stage3/run_001 | 16 | 8 | 3e-04 | 8 | 0.0562 | 0.0074 | 165582.1277501583 | completed |
| stage3/run_002 | 32 | 8 | 3e-04 | 8 | 0.0503 | 0.0080 | 86645.20358991623 | completed |

## Best Configuration

- **Experiment:** `stage3/run_003`
- **LoRA alpha:** 64
- **LoRA r:** 8
- **Learning rate:** 0.0003
- **Epochs:** 8
- **Validation loss:** 0.0054
- **Checkpoint:** `/Users/hassenhicheri/Desktop/CAD/training/experiments/stage3/run_003/checkpoints/adapter`

Selected because it achieved the lowest validation loss among all completed Stage 3 runs.
