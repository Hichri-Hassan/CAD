# LoRA Comparison Experiments

This folder contains **fresh LoRA adapters** trained from the base model `Qwen/Qwen2.5-3B-Instruct` for a controlled dataset comparison.

| Experiment | Dataset | Purpose |
|---|---|---|
| `baseline_lora/run_001` | Original CAD dataset (200 examples) | Replicate the original training setup from scratch |
| `primitives_lora/run_001` | CAD + primitives (700 examples) | Measure the effect of adding primitive shapes |

The previous production adapter at `training/experiments/final/run_001/checkpoints/adapter` is **not modified**.

## Prerequisites

```bash
pip install -r requirements-training.txt
python3 training/scripts/download_model.py
python3 scripts/generate_primitive_prompts.py
```

## 1. Prepare datasets

Creates:

- `dataset_v1/train/comparison/baseline_training_data.jsonl`
- `dataset_v1/train/comparison/merged_training_data.jsonl`
- `dataset_v1/train/comparison/comparison_split_manifest.json`
- `dataset_v1/train/comparison/dataset_statistics.json`

```bash
python3 training/scripts/prepare_comparison_datasets.py
```

Validation uses a **geometry-aware split**:

- all prompt variants of the same CAD model or primitive shape stay in the same split
- both experiments share the same manifest, so held-out geometries are consistent

## 2. Plan experiments

```bash
python3 training/scripts/plan_comparison_experiments.py
```

This creates:

- `training/experiments/baseline_lora/run_001/`
- `training/experiments/primitives_lora/run_001/`

Hyperparameters are copied from `training/best_configs/final_best.yaml`.

## 3. Train

Train both experiments:

```bash
python3 training/scripts/run_comparison_experiments.py --train --report
```

Or train individually:

```bash
python3 training/scripts/train_lora.py \
  --experiment training/experiments/baseline_lora/run_001

python3 training/scripts/train_lora.py \
  --experiment training/experiments/primitives_lora/run_001
```

Smoke test:

```bash
python3 training/scripts/run_comparison_experiments.py \
  --prepare-data --plan --train --dry-run
```

## 4. Evaluate

Held-out test set (`dataset_v1/test/json/`, 7 models):

```bash
python3 training/scripts/evaluate_generation.py \
  --adapter training/experiments/baseline_lora/run_001/checkpoints/adapter

python3 training/scripts/evaluate_generation.py \
  --adapter training/experiments/primitives_lora/run_001/checkpoints/adapter

python3 training/scripts/evaluate_generation.py \
  --adapter training/experiments/final/run_001/checkpoints/adapter
```

Interactive dashboard:

```bash
PYTHONPATH=. streamlit run training/evaluation_app/app.py
```

## Artifacts per experiment

```
training/experiments/<stage>/run_001/
├── config.yaml
├── manifest.json
├── result.json
├── metrics.json
├── experiment_report.md
├── dataset/
│   ├── split_info.json
│   ├── train_examples.jsonl
│   └── val_examples.jsonl
├── curves/
│   ├── train_loss.json
│   └── eval_loss.json
├── logs/                  # TensorBoard if installed
└── checkpoints/
    ├── adapter/           # final LoRA adapter
    └── trainer/
```

## Reproducibility

- Random seed: `42`
- Split manifest: `dataset_v1/train/comparison/comparison_split_manifest.json`
- Base model: `Qwen/Qwen2.5-3B-Instruct`
- No previous LoRA checkpoint is loaded during training

## One-shot workflow

```bash
python3 training/scripts/run_comparison_experiments.py \
  --prepare-data --plan --train --report
```
