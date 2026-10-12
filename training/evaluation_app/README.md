# CAD Copilot Evaluation Dashboard

Local Streamlit app for qualitative comparison of CAD JSON generations against ground truth.

## Features

- **Compare view**: example list, side-by-side JSON with syntax highlighting, operation diff table, per-example stats, error classification
- **Through holes**: browse generated through-hole feature models with dimensions, volume/bbox checks, and 3D preview
- **CAD viewer**: interactive Plotly mesh from STL (or PNG if exported)
- **Dataset exploration**: operation frequency and prompt/operation scatter charts
- **Playground**: ad-hoc prompt → generate → compile (does not modify the test set)
- **Ambiguity mode**: N generations with different seeds, shown side by side
- **Export**: markdown report and metrics JSON
- **Screenshots**: attach and store GT/prediction images per example

## Setup

```bash
pip install -r requirements-eval.txt
```

For generation features, the LoRA adapter must exist at:

`training/experiments/primitives_lora/run_001/checkpoints/adapter`

The sidebar can switch to `baseline_lora` or the previous `final/run_001` adapter.

FreeCAD is optional but recommended for compilation and mesh export.

## Run

```bash
./training/evaluation_app/run.sh
```

Or:

```bash
PYTHONPATH=. streamlit run training/evaluation_app/app.py
```

## Data sources

The app reads:

- Ground truth: `dataset_v1/test/json/`
- Saved generations: `training/evaluation/generations/`
- Eval metrics cache: `training/evaluation/generation_eval_results.json`

Re-run batch evaluation to refresh generations:

```bash
python training/scripts/evaluate_generation.py \
  --adapter training/experiments/primitives_lora/run_001/checkpoints/adapter
```

## Keyboard shortcuts

Use the example list buttons or filter search. Navigation shortcuts (`j`/`k`) are shown in the sidebar; full hotkey support can be extended via Streamlit components.
