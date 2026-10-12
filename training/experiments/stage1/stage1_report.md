# STAGE1 HPO Report

Generated: 2026-07-05T11:02:41.565364+00:00

## Comparison Table

| Experiment | LoRA r | LR | Train Loss | Val Loss | Time (s) | Trainable Params | Status |
|---|---:|---:|---:|---:|---:|---:|---|
| stage1/run_003 | 8 | 3e-04 | 0.1025 | 0.0269 | 12614.5115 | 14,966,784 | completed |
| stage1/run_006 | 16 | 3e-04 | 0.1054 | 0.0284 | 10640.6368 | 29,933,568 | completed |
| stage1/run_009 | 32 | 3e-04 | 0.1062 | 0.0297 | 70421.7490 | 59,867,136 | completed |
| stage1/run_002 | 8 | 2e-04 | 0.1158 | 0.0396 | 24142.0775 | 14,966,784 | completed |
| stage1/run_005 | 16 | 2e-04 | 0.1184 | 0.0441 | 12946.9650 | 29,933,568 | completed |
| stage1/run_008 | 32 | 2e-04 | 0.1200 | 0.0459 | 16761.7331 | 59,867,136 | completed |
| stage1/run_001 | 8 | 1e-04 | 0.1451 | 0.0749 | 40569.5753 | 14,966,784 | completed |
| stage1/run_004 | 16 | 1e-04 | 0.1473 | 0.0772 | 64706.3095 | 29,933,568 | completed |
| stage1/run_007 | 32 | 1e-04 | 0.1505 | 0.0812 | 72703.3815 | 59,867,136 | completed |

## Best Configuration

- **Experiment:** `stage1/run_003`
- **LoRA rank:** 8
- **Learning rate:** 0.0003
- **Validation loss:** 0.02685403823852539
- **Checkpoint:** `/Users/hassenhicheri/Desktop/CAD/training/experiments/stage1/run_003/checkpoints/adapter`

Selected because `stage1/run_003` achieved the lowest validation loss (0.0269) among all completed stage1 runs using metric `val_loss`.
