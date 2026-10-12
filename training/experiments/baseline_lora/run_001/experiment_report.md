# baseline_lora Experiment Report

Fresh LoRA trained only on the original CAD dataset.

## Dataset

- **Dataset path:** `dataset_v1/train/comparison/baseline_training_data.jsonl`
- **Dataset version:** `baseline_cad_v1_200`
- **Split strategy:** `geometry_aware`
- **Validation ratio:** `0.1`
- **Split manifest:** `dataset_v1/train/comparison/comparison_split_manifest.json`
- **Train examples:** 185
- **Validation examples:** 15

### Global dataset statistics

- Baseline CAD examples: 200
- Primitive examples: 500
- Merged examples: 700
- Duplicates removed during merge: 0

## Hyperparameters

| Parameter | Value |
|---|---|
| Base model | `Qwen/Qwen2.5-3B-Instruct` |
| LoRA rank | 8 |
| LoRA alpha | 64 |
| LoRA dropout | 0.05 |
| Learning rate | 0.0003 |
| Epochs | 8 |
| Optimizer | adamw_torch |
| Scheduler | cosine |
| Warmup ratio | 0.1 |
| Weight decay | 0.01 |
| Train batch size | 2 |
| Eval batch size | 2 |
| Gradient accumulation | 4 |
| Max sequence length | 4096 |
| Random seed | 42 |

## Training results

- **Status:** completed
- **Completed at:** 2026-08-05T11:24:35.389843+00:00
- **Final train loss:** 0.0424972239911477
- **Final validation loss:** 0.31098058819770813
- **Training time (s):** 181219.2602701187
- **Trainable parameters:** 14966784
- **Adapter checkpoint:** `/Users/hassenhicheri/Desktop/CAD/training/experiments/baseline_lora/run_001/checkpoints/adapter`

## Artifacts

- Config: `/Users/hassenhicheri/Desktop/CAD/training/experiments/baseline_lora/run_001/config.yaml`
- Result JSON: `/Users/hassenhicheri/Desktop/CAD/training/experiments/baseline_lora/run_001/result.json`
- Train loss curve: `/Users/hassenhicheri/Desktop/CAD/training/experiments/baseline_lora/run_001/curves/train_loss.json`
- Validation loss curve: `/Users/hassenhicheri/Desktop/CAD/training/experiments/baseline_lora/run_001/curves/eval_loss.json`
- TensorBoard logs: `/Users/hassenhicheri/Desktop/CAD/training/experiments/baseline_lora/run_001/logs`
- Dataset split info: `/Users/hassenhicheri/Desktop/CAD/training/experiments/baseline_lora/run_001/dataset/split_info.json`

## Evaluation

Compare against the previous adapter with:

```bash
python3 training/scripts/evaluate_generation.py \
  --adapter /Users/hassenhicheri/Desktop/CAD/training/experiments/baseline_lora/run_001/checkpoints/adapter
```

Previous production adapter:

```bash
python3 training/scripts/evaluate_generation.py \
  --adapter training/experiments/final/run_001/checkpoints/adapter
```
