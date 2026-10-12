#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

echo "=== Training baseline_lora ==="
python3 training/scripts/train_lora.py \
  --experiment training/experiments/baseline_lora/run_001

python3 training/scripts/report_comparison_experiment.py \
  --experiment-dir training/experiments/baseline_lora/run_001

echo "=== Training primitives_lora ==="
python3 training/scripts/train_lora.py \
  --experiment training/experiments/primitives_lora/run_001

python3 training/scripts/report_comparison_experiment.py \
  --experiment-dir training/experiments/primitives_lora/run_001

echo "=== Comparison training complete ==="
