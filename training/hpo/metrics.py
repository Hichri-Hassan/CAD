"""Metrics collection and extensible CAD evaluation hooks."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any, Callable


@dataclass
class CoreTrainingMetrics:
    """Standard metrics recorded for every HPO experiment."""

    train_loss: float | None = None
    val_loss: float | None = None
    training_time_seconds: float | None = None
    trainable_parameters: int | None = None
    checkpoint_path: str | None = None


@dataclass
class CADEvaluationMetrics:
    """Reserved CAD-specific metrics (plug-in evaluators implement these later)."""

    json_validity: float | None = None
    compilation_success: float | None = None
    operation_accuracy: float | None = None
    geometry_similarity: float | None = None


@dataclass
class ExperimentMetrics:
    """Unified metrics container for an experiment report."""

    core: CoreTrainingMetrics = field(default_factory=CoreTrainingMetrics)
    cad: CADEvaluationMetrics = field(default_factory=CADEvaluationMetrics)
    custom: dict[str, float | None] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "core": asdict(self.core),
            "cad": asdict(self.cad),
            "custom": self.custom,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExperimentMetrics:
        core_raw = data.get("core", {})
        cad_raw = data.get("cad", {})
        return cls(
            core=CoreTrainingMetrics(**{k: core_raw.get(k) for k in CoreTrainingMetrics.__dataclass_fields__}),
            cad=CADEvaluationMetrics(**{k: cad_raw.get(k) for k in CADEvaluationMetrics.__dataclass_fields__}),
            custom=dict(data.get("custom", {})),
        )

    def selection_value(self, metric_name: str) -> float | None:
        """Return a scalar used for hierarchical stage selection."""
        if metric_name in CoreTrainingMetrics.__dataclass_fields__:
            return getattr(self.core, metric_name)
        if metric_name in CADEvaluationMetrics.__dataclass_fields__:
            return getattr(self.cad, metric_name)
        return self.custom.get(metric_name)


class CADMetricsEvaluator(ABC):
    """Interface for future CAD-specific evaluation during HPO."""

    @abstractmethod
    def evaluate(self, *, checkpoint_path: str, eval_dataset_path: str) -> CADEvaluationMetrics:
        """Compute CAD metrics for a trained checkpoint."""


class PlaceholderCADMetricsEvaluator(CADMetricsEvaluator):
    """No-op evaluator until compiler-integrated metrics are implemented."""

    def evaluate(self, *, checkpoint_path: str, eval_dataset_path: str) -> CADEvaluationMetrics:
        return CADEvaluationMetrics()


MetricFn = Callable[[], float | None]


class MetricRegistry:
    """Registry for optional custom metrics without changing the HPO pipeline."""

    def __init__(self) -> None:
        self._metrics: dict[str, MetricFn] = {}

    def register(self, name: str, fn: MetricFn) -> None:
        self._metrics[name] = fn

    def collect_custom(self) -> dict[str, float | None]:
        return {name: fn() for name, fn in self._metrics.items()}


def empty_metrics() -> dict[str, Any]:
    """Return a template metrics file for a newly planned experiment."""
    return ExperimentMetrics().to_dict()
