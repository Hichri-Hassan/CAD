# primitives_lora Experiment Report

Fresh LoRA trained on original CAD dataset plus primitive dataset.

## Dataset

- **Dataset path:** `dataset_v1/train/comparison/merged_training_data.jsonl`
- **Dataset version:** `cad_v1_plus_primitives_700`
- **Split strategy:** `geometry_aware`
- **Validation ratio:** `0.1`
- **Split manifest:** `dataset_v1/train/comparison/comparison_split_manifest.json`
- **Train examples:** 630
- **Validation examples:** 70

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
- **Completed at:** 2026-08-08T09:24:13.952612+00:00
- **Final train loss:** 0.023883797717483307
- **Final validation loss:** 0.09310957044363022
- **Training time (s):** 250464.5512933731
- **Trainable parameters:** 14966784
- **Adapter checkpoint:** `/Users/hassenhicheri/Desktop/CAD/training/experiments/primitives_lora/run_001/checkpoints/adapter`

## Artifacts

- Config: `/Users/hassenhicheri/Desktop/CAD/training/experiments/primitives_lora/run_001/config.yaml`
- Result JSON: `/Users/hassenhicheri/Desktop/CAD/training/experiments/primitives_lora/run_001/result.json`
- Train loss curve: `/Users/hassenhicheri/Desktop/CAD/training/experiments/primitives_lora/run_001/curves/train_loss.json`
- Validation loss curve: `/Users/hassenhicheri/Desktop/CAD/training/experiments/primitives_lora/run_001/curves/eval_loss.json`
- TensorBoard logs: `/Users/hassenhicheri/Desktop/CAD/training/experiments/primitives_lora/run_001/logs`
- Dataset split info: `/Users/hassenhicheri/Desktop/CAD/training/experiments/primitives_lora/run_001/dataset/split_info.json`

## Evaluation

Compare against the previous adapter with:

```bash
python3 training/scripts/evaluate_generation.py \
  --adapter /Users/hassenhicheri/Desktop/CAD/training/experiments/primitives_lora/run_001/checkpoints/adapter
```

Previous production adapter:

```bash
python3 training/scripts/evaluate_generation.py \
  --adapter training/experiments/final/run_001/checkpoints/adapter
```
