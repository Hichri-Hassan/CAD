"""Experiment configuration and reproducibility records."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class FixedHyperparameters:
    weight_decay: float
    max_seq_length: int
    optimizer: str
    scheduler: str
    warmup_ratio: float
    per_device_train_batch_size: int
    per_device_eval_batch_size: int
    gradient_accumulation_steps: int
    logging_steps: int
    eval_steps: int
    save_steps: int
    target_modules: list[str]


@dataclass(frozen=True)
class ReproducibilityInfo:
    seed: int
    dataset_version: str
    dataset_path: str
    model_version: str
    base_config: str
    split_manifest_path: str | None = None
    split_strategy: str = "random"
    val_ratio: float = 0.1


@dataclass(frozen=True)
class SearchableHyperparameters:
    lora_r: int
    learning_rate: float
    num_epochs: int
    lora_dropout: float
    lora_alpha: int


@dataclass(frozen=True)
class RunConfig:
    """Complete configuration for one HPO experiment run."""

    stage: str
    run_id: str
    searchable: SearchableHyperparameters
    fixed: FixedHyperparameters
    reproducibility: ReproducibilityInfo
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def lora_config(self) -> dict[str, Any]:
        return {
            "r": self.searchable.lora_r,
            "lora_alpha": self.searchable.lora_alpha,
            "lora_dropout": self.searchable.lora_dropout,
            "target_modules": self.fixed.target_modules,
        }


@dataclass(frozen=True)
class ExperimentPlan:
    """A planned experiment before training starts."""

    stage: str
    run_id: str
    run_index: int
    config: RunConfig
    run_dir: str
    search_overrides: dict[str, Any]
    frozen_from: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "run_id": self.run_id,
            "run_index": self.run_index,
            "run_dir": self.run_dir,
            "search_overrides": self.search_overrides,
            "frozen_from": self.frozen_from,
            "config": self.config.to_dict(),
        }


@dataclass
class ExperimentResult:
    """Results collected after an experiment completes."""

    stage: str
    run_id: str
    run_dir: str
    config: RunConfig
    metrics: dict[str, Any]
    status: str = "planned"
    completed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "run_id": self.run_id,
            "run_dir": self.run_dir,
            "status": self.status,
            "completed_at": self.completed_at,
            "config": self.config.to_dict(),
            "metrics": self.metrics,
        }
