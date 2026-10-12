"""Training pipeline configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "training" / "configs" / "qwen_3b.yaml"


@dataclass(frozen=True)
class ModelConfig:
    name: str
    family: str
    hf_model_id: str
    trust_remote_code: bool = False


@dataclass(frozen=True)
class PathConfig:
    checkpoints: Path
    outputs: Path
    dataset: Path
    hf_cache: Path | None = None


@dataclass(frozen=True)
class InferenceConfig:
    max_new_tokens: int = 128
    temperature: float = 0.7
    do_sample: bool = True


@dataclass(frozen=True)
class LoRAConfig:
    enabled: bool = False
    r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    target_modules: list[str] | None = None


@dataclass(frozen=True)
class QLoRAConfig:
    enabled: bool = False
    load_in_4bit: bool = True
    bnb_4bit_compute_dtype: str = "bfloat16"
    bnb_4bit_quant_type: str = "nf4"


@dataclass(frozen=True)
class TrainingConfig:
    method: str = "lora"
    lora: LoRAConfig = field(default_factory=LoRAConfig)
    qlora: QLoRAConfig = field(default_factory=QLoRAConfig)


@dataclass(frozen=True)
class PipelineConfig:
    model: ModelConfig
    paths: PathConfig
    inference: InferenceConfig
    training: TrainingConfig
    config_path: Path

    @property
    def hf_model_id(self) -> str:
        return self.model.hf_model_id


def _resolve_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def _optional_path(value: Any) -> Path | None:
    if value in (None, "", "null"):
        return None
    return _resolve_path(str(value))


def load_config(config_path: Path | str | None = None) -> PipelineConfig:
    """Load a YAML training pipeline configuration."""
    path = Path(config_path) if config_path is not None else DEFAULT_CONFIG_PATH
    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(f"Training config not found: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid training config: {path}")

    model_raw = raw.get("model", {})
    paths_raw = raw.get("paths", {})
    inference_raw = raw.get("inference", {})
    training_raw = raw.get("training", {})
    lora_raw = training_raw.get("lora", {})
    qlora_raw = training_raw.get("qlora", {})

    model = ModelConfig(
        name=str(model_raw.get("name", "")),
        family=str(model_raw.get("family", "")),
        hf_model_id=str(model_raw.get("hf_model_id", "")),
        trust_remote_code=bool(model_raw.get("trust_remote_code", False)),
    )
    if not model.hf_model_id:
        raise ValueError(f"Config {path} is missing model.hf_model_id")
    if not model.family:
        raise ValueError(f"Config {path} is missing model.family")

    paths = PathConfig(
        checkpoints=_resolve_path(str(paths_raw.get("checkpoints", "training/checkpoints"))),
        outputs=_resolve_path(str(paths_raw.get("outputs", "training/outputs"))),
        dataset=_resolve_path(str(paths_raw.get("dataset", "dataset_v1/train/training_data.jsonl"))),
        hf_cache=_optional_path(paths_raw.get("hf_cache")),
    )
    inference = InferenceConfig(
        max_new_tokens=int(inference_raw.get("max_new_tokens", 128)),
        temperature=float(inference_raw.get("temperature", 0.7)),
        do_sample=bool(inference_raw.get("do_sample", True)),
    )
    training = TrainingConfig(
        method=str(training_raw.get("method", "lora")),
        lora=LoRAConfig(
            enabled=bool(lora_raw.get("enabled", False)),
            r=int(lora_raw.get("r", 16)),
            lora_alpha=int(lora_raw.get("lora_alpha", 32)),
            lora_dropout=float(lora_raw.get("lora_dropout", 0.05)),
            target_modules=lora_raw.get("target_modules"),
        ),
        qlora=QLoRAConfig(
            enabled=bool(qlora_raw.get("enabled", False)),
            load_in_4bit=bool(qlora_raw.get("load_in_4bit", True)),
            bnb_4bit_compute_dtype=str(qlora_raw.get("bnb_4bit_compute_dtype", "bfloat16")),
            bnb_4bit_quant_type=str(qlora_raw.get("bnb_4bit_quant_type", "nf4")),
        ),
    )

    return PipelineConfig(
        model=model,
        paths=paths,
        inference=inference,
        training=training,
        config_path=path,
    )
