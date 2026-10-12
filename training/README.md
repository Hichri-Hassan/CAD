# Local model training pipeline for CAD Copilot V1.

This directory contains the **local / open-source fine-tuning infrastructure** for CAD Copilot.

The V1 target model is:

**`Qwen/Qwen2.5-3B-Instruct`**

## Primary training dataset

```
dataset_v1/train/training_data.jsonl
```

Each line contains:

```json
{"input":"...", "output":{"operations":[...]}}
```

The OpenAI export in `dataset_v1/train/openai_finetune.jsonl` is kept for archival purposes only.

## Directory layout

```
training/
├── configs/
│   └── qwen_3b.yaml          # Model and path configuration
├── models/
│   ├── base.py               # Model loader interface
│   └── qwen.py               # Qwen family loader
├── scripts/
│   ├── download_model.py     # Download + verify HF model/tokenizer
│   └── verify_model.py       # Simple inference smoke test
├── checkpoints/              # Future LoRA / QLoRA checkpoints
└── outputs/                  # Future training outputs
```

## Setup

Install training dependencies:

```bash
pip install -r requirements-training.txt
```

Install PyTorch for your platform if needed:

https://pytorch.org/get-started/locally/

The Qwen2.5-3B-Instruct weights require roughly **5 GB** of free disk space in the Hugging Face cache (default: `~/.cache/huggingface`).

To use a custom cache location, set `paths.hf_cache` in `training/configs/qwen_3b.yaml`.

## Download model

Downloads and caches the model and tokenizer via Hugging Face Transformers:

```bash
python3 training/scripts/download_model.py
```

## Verify inference

Runs a simple prompt through the loaded model:

```bash
python3 training/scripts/verify_model.py
```

Example:

```
Prompt: Say hello.
Response: ...
```

## Configuration

All paths and model settings live in:

```
training/configs/qwen_3b.yaml
```

To switch models later (e.g. Qwen 7B, Llama, Mistral), add a new config file and implement or reuse a model-family loader under `training/models/`.

LoRA / QLoRA settings are reserved in the config but **not implemented yet**.

## Hierarchical hyperparameter optimization

CAD Copilot V1 uses a **staged HPO strategy** (not brute-force grid search) tuned for a small specialized dataset (40 models, 200 examples).

See `training/hpo/METHODOLOGY.md` for research justification.

```bash
# Preview the search plan (24 total runs across 3 stages)
python3 training/scripts/plan_hpo.py --summary-only

# Prepare experiment directories (no training)
python3 training/scripts/plan_hpo.py

# Check experiment status (after training, in a future step)
python3 training/scripts/summarize_hpo.py
```

Experiment artifacts are stored under `training/experiments/`:

```
training/experiments/
├── hpo_master_manifest.json
├── stage1/run_001/ ... run_009/
├── stage2/run_001/ ... run_012/
└── stage3/run_001/ ... run_003/
```

### Train one LoRA experiment

```bash
python3 training/scripts/train_lora.py \
  --experiment training/experiments/stage1/run_001 \
  --dry-run
```

### Run Stage 1 HPO (full search + report)

```bash
python3 training/scripts/run_hpo_stage.py \
  --stage-dir training/experiments/stage1 \
  --report
```

Generate report only (after training completes):

```bash
python3 training/scripts/report_stage.py --stage stage1
```

## Not implemented yet

- Stage 2 / Stage 3 execution
- QLoRA fine-tuning
- Evaluation
- Compiler integration
