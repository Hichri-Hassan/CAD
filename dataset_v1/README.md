# CAD Copilot Dataset V1 (Frozen)

The first official training dataset for CAD Copilot.

## Scope

Dataset V1 contains models that satisfy **all** of the following criteria:

1. Parser status is `valid` (fully parsed, no unsupported features).
2. The model is completely representable by the current JSON specification.
3. The model passes parser → JSON → compiler round-trip validation.

Partially parsed models are **excluded**.

### Selection funnel

From the FreeCAD-library extraction (~3,199 models):

| Stage | Count |
|---|---:|
| Fully parsed (parser `valid`) | 134 |
| Round-trip validated (V1 members) | 47 |

The remaining 87 fully-parsed models fail compilation. See `roundtrip_failure_analysis.md` for the forensic breakdown.

## Directory Structure

```
dataset_v1/
├── train/                   # Training split (40 models)
│   ├── models/              # Original .FCStd files
│   ├── json/                # Canonical JSON dataset (ground truth)
│   ├── training_data.jsonl  # Primary supervised fine-tuning export (Qwen)
│   ├── openai_finetune.jsonl # Archival OpenAI chat export
│   └── metadata.csv
├── system_prompt.txt        # Archival system prompt for OpenAI export
├── test/                    # Held-out test split (7 models)
│   ├── models/
│   ├── json/
│   └── metadata.csv
├── models/                  # Full V1 JSON corpus (47 models)
├── metadata.csv             # Index of all V1 models
├── split_manifest.json      # Deterministic split record (seed=42)
├── roundtrip_failure_analysis.md
└── scripts/
    ├── create_split.py      # Regenerate train/test split
    ├── generate_dataset.py  # Main pipeline entry point
    ├── roundtrip_validator.py
    ├── summary_generator.py
    ├── openai_client.py
    └── generate_prompts.py
```

## Train/Test Split

| Split | Models | Seed |
|---|---:|---|
| Train | 40 | 42 |
| Test | 7 | 42 |

Each split's `metadata.csv` contains:

- `model_id`
- `original_filename`
- `json_filename`

Regenerate the split:

```bash
python3 dataset_v1/scripts/create_split.py
```

## OpenAI API Configuration

Prompt generation uses the OpenAI API. **Do not hardcode the API key.**

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Set your key in `.env`:

```
OPENAI_API_KEY=sk-...
```

3. The `.env` file is listed in `.gitignore` and must not be committed.

Code loads the key via `python-dotenv` and reads it with `os.getenv("OPENAI_API_KEY")`. If the key is missing, a clear error explains that it must be defined in `.env`.

Install dependencies:

```bash
pip install -r requirements.txt
```

### Generate training prompts (OpenAI)

After setting `OPENAI_API_KEY` in `.env`, generate natural-language descriptions for all training models:

```bash
python3 dataset_v1/scripts/generate_train_prompts.py
```

This updates `train/json/*.json` with `title`, `description`, `tags`, and 5 `prompts` per model, and enriches `train/metadata.csv`.

### Export supervised fine-tuning data

The canonical JSON files in `train/json/` remain the ground-truth dataset and should not be modified for training exports.

Generate the **primary** training file used by the local Qwen pipeline:

```bash
python3 dataset_v1/scripts/export_training_data.py
```

This writes `dataset_v1/train/training_data.jsonl` (~200 examples: 40 models × 5 prompts). Each line contains:

```json
{"input":"...","output":{"operations":[...]}}
```

### Local model training (Qwen)

The active V1 training pipeline lives in `training/` and uses `train/training_data.jsonl`.

See `training/README.md` for setup, model download, and verification.

### Archival OpenAI export

The OpenAI chat export is retained for reference but is no longer the primary training format:

```bash
python3 dataset_v1/scripts/export_openai_dataset.py
```

## Dataset Format

Each file in `models/` follows this structure:

```json
{
  "model_id": "model_0001",
  "title": "...",
  "description": "...",
  "tags": ["..."],
  "prompts": ["...", "...", "...", "...", "..."],
  "metadata": { "...parser metadata..." },
  "operations": [ "...parser operations unchanged..." ]
}
```

The `operations` and `metadata` sections are copied verbatim from the parser output.

## Generate Dataset V1

### Prerequisites

- Python 3.10+
- FreeCAD installed (`freecadcmd` available, or set `FREECAD_CMD`)
- OpenAI API key in `.env` as `OPENAI_API_KEY` (unless using fallback mode)

### Full pipeline

```bash
cd /path/to/CAD
cp .env.example .env   # then edit .env with your key

python dataset_v1/scripts/generate_dataset.py
```

### Fallback mode (no OpenAI)

```bash
python dataset_v1/scripts/generate_dataset.py --skip-prompts
```

### Options

| Flag | Description |
|---|---|
| `--examples PATH` | Source `.FCStd` directory (default: `examples/`) |
| `--output PATH` | Output directory (default: `dataset_v1/`) |
| `--skip-prompts` | Use deterministic fallback prompts |
| `--openai-model NAME` | OpenAI model (default: `gpt-4o-mini`) |
| `--limit N` | Process only the first N candidates |

## Pipeline

```
.FCStd
   ↓
Parser (valid + no unsupported features)
   ↓
Round-trip validator (JSON + compiler)
   ↓
Summary generator
   ↓
OpenAI API (or fallback)
   ↓
Final enriched JSON
```

## Prompt Styles

Each model receives five prompts in varied styles (short, conversational, geometry-focused, dimension-focused, alternative wording). Prompts describe **visible geometry**, not CAD construction operations.

Regenerate training prompts after changing the prompt template:

```bash
python3 dataset_v1/scripts/generate_train_prompts.py
```

## Reusability

This layout is designed for future dataset versions (V2, V3). To build V2:

- Adjust candidate selection criteria in `generate_dataset.py`
- Change output directory (e.g. `dataset_v2/`)
- Reuse the same scripts with minimal modifications

## Security

The OpenAI API key is read from the `.env` file via `python-dotenv` and accessed with `os.getenv("OPENAI_API_KEY")`. It is never hardcoded or committed to the repository.
