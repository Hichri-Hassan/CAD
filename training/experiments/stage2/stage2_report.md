# STAGE2 HPO Report (Epoch Search)

Generated: 2026-07-25T09:07:18.700078+00:00

## Comparison Table

| Experiment | Epochs | LoRA r | LR | Train Loss | Val Loss | Time (s) | Trainable Params | Status |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| stage2/run_008 | 8 | 8 | 3e-04 | 0.0503 | 0.0080 | 149141.01036071777 | 14966784 | completed |
| stage2/run_007 | 7 | 8 | 3e-04 | 0.0558 | 0.0088 | 26542.520218849182 | 14966784 | completed |
| stage2/run_006 | 6 | 8 | 3e-04 | 0.0619 | 0.0088 | 30738.894055366516 | 14966784 | completed |
| stage2/run_005 | 5 | 8 | 3e-04 | 0.0710 | 0.0119 | 47142.548162698746 | 14966784 | completed |
| stage2/run_004 | 4 | 8 | 3e-04 | 0.0826 | 0.0183 | 25302.22772884369 | 14966784 | completed |
| stage2/run_003 | 3 | 8 | 3e-04 | 0.1025 | 0.0269 | 9700.149733781815 | 14966784 | completed |
| stage2/run_002 | 2 | 8 | 3e-04 | 0.1373 | 0.0623 | 3837.4459149837494 | 14966784 | completed |
| stage2/run_001 | 1 | 8 | 3e-04 | 0.1892 | 0.1256 | 1734.406399011612 | 14966784 | completed |

## Best Configuration

- **Experiment:** `stage2/run_008`
- **Epochs:** 8
- **LoRA r:** 8
- **Learning rate:** 0.0003
- **LoRA alpha:** 32
- **LoRA dropout:** 0.05
- **Validation loss:** 0.0080
- **Checkpoint:** `/Users/hassenhicheri/Desktop/CAD/training/experiments/stage2/run_008/checkpoints/adapter`

Selected because it achieved the lowest validation loss among all completed Stage 2 runs.
