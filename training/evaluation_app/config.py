"""Default paths and settings for the evaluation dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_ADAPTER = PROJECT_ROOT / "training/experiments/primitives_lora/run_001/checkpoints/adapter"

ADAPTER_PRESETS = {
    "primitives_lora (CAD + primitives)": PROJECT_ROOT
    / "training/experiments/primitives_lora/run_001/checkpoints/adapter",
    "baseline_lora (CAD only)": PROJECT_ROOT
    / "training/experiments/baseline_lora/run_001/checkpoints/adapter",
    "previous LoRA (final/run_001)": PROJECT_ROOT
    / "training/experiments/final/run_001/checkpoints/adapter",
}
DEFAULT_CONFIG = PROJECT_ROOT / "training/configs/qwen_3b.yaml"
DEFAULT_SYSTEM_PROMPT = PROJECT_ROOT / "dataset_v1/system_prompt.txt"
DEFAULT_TEST_JSON_DIR = PROJECT_ROOT / "dataset_v1/test/json"
DEFAULT_METADATA = PROJECT_ROOT / "dataset_v1/test/metadata.csv"
DEFAULT_EVAL_DIR = PROJECT_ROOT / "training/evaluation"
DEFAULT_SCREENSHOTS_DIR = DEFAULT_EVAL_DIR / "screenshots"
DEFAULT_EXPORT_DIR = DEFAULT_EVAL_DIR / "exports"
DEFAULT_FEATURES_DIR = PROJECT_ROOT / "output" / "features"


@dataclass(frozen=True)
class AppPaths:
    project_root: Path
    adapter: Path
    config: Path
    system_prompt: Path
    test_json_dir: Path
    metadata: Path
    eval_dir: Path
    screenshots_dir: Path
    export_dir: Path
    features_dir: Path

    @property
    def feature_stl_cache_dir(self) -> Path:
        return self.eval_dir / "features_cache" / "stl"

    @property
    def generations_dir(self) -> Path:
        return self.eval_dir / "generations"

    @property
    def generated_models_dir(self) -> Path:
        return self.eval_dir / "models" / "generated"

    @property
    def reference_models_dir(self) -> Path:
        return self.eval_dir / "models" / "reference"

    @property
    def results_json(self) -> Path:
        return self.eval_dir / "generation_eval_results.json"


def default_paths() -> AppPaths:
    return AppPaths(
        project_root=PROJECT_ROOT,
        adapter=DEFAULT_ADAPTER,
        config=DEFAULT_CONFIG,
        system_prompt=DEFAULT_SYSTEM_PROMPT,
        test_json_dir=DEFAULT_TEST_JSON_DIR,
        metadata=DEFAULT_METADATA,
        eval_dir=DEFAULT_EVAL_DIR,
        screenshots_dir=DEFAULT_SCREENSHOTS_DIR,
        export_dir=DEFAULT_EXPORT_DIR,
        features_dir=DEFAULT_FEATURES_DIR,
    )
