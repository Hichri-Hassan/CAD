"""Search space definitions and grid expansion."""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

import yaml

from training.config import PROJECT_ROOT


@dataclass(frozen=True)
class StageDefinition:
    stage_id: str
    name: str
    description: str
    search: dict[str, list[Any]]
    selection_metric: str
    selection_direction: str
    depends_on: str | None = None

    @property
    def combinations(self) -> int:
        count = 1
        for values in self.search.values():
            count *= len(values)
        return count


@dataclass(frozen=True)
class HpoDefaults:
    seed: int
    dataset_version: str
    dataset_path: str
    model_version: str
    base_config: str
    fixed: dict[str, Any]
    stage_defaults: dict[str, Any]
    experiments_root: Path


def load_hpo_defaults(path: Path | None = None) -> HpoDefaults:
    config_path = path or PROJECT_ROOT / "training" / "configs" / "hpo_defaults.yaml"
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    paths = raw.get("paths", {})
    repro = raw.get("reproducibility", {})
    root = paths.get("experiments_root", "training/experiments")
    return HpoDefaults(
        seed=int(repro.get("seed", 42)),
        dataset_version=str(repro.get("dataset_version", "")),
        dataset_path=str(repro.get("dataset_path", "")),
        model_version=str(repro.get("model_version", "")),
        base_config=str(repro.get("base_config", "")),
        fixed=dict(raw.get("fixed", {})),
        stage_defaults=dict(raw.get("stage_defaults", {})),
        experiments_root=_resolve_path(str(root)),
    )


def load_stage_definitions(path: Path | None = None) -> list[StageDefinition]:
    config_path = path or PROJECT_ROOT / "training" / "configs" / "hpo_stages.yaml"
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    stages = []
    for stage_id, stage_raw in raw.get("stages", {}).items():
        stages.append(
            StageDefinition(
                stage_id=stage_id,
                name=str(stage_raw.get("name", stage_id)),
                description=str(stage_raw.get("description", "")).strip(),
                search={key: list(values) for key, values in stage_raw.get("search", {}).items()},
                selection_metric=str(stage_raw.get("selection_metric", "val_loss")),
                selection_direction=str(stage_raw.get("selection_direction", "min")),
                depends_on=stage_raw.get("depends_on"),
            )
        )
    return stages


def get_stage_definition(stage_id: str, stages: list[StageDefinition] | None = None) -> StageDefinition:
    stages = stages or load_stage_definitions()
    for stage in stages:
        if stage.stage_id == stage_id:
            return stage
    raise KeyError(f"Unknown HPO stage: {stage_id}")


def iter_search_grid(stage: StageDefinition) -> Iterator[dict[str, Any]]:
    """Yield every hyperparameter combination for a stage."""
    if not stage.search:
        yield {}
        return

    keys = list(stage.search.keys())
    value_lists = [stage.search[key] for key in keys]
    for combo in itertools.product(*value_lists):
        yield dict(zip(keys, combo))


def merge_hyperparameters(
    defaults: dict[str, Any],
    frozen: dict[str, Any],
    overrides: dict[str, Any],
) -> dict[str, Any]:
    """Merge default, frozen, and searched hyperparameter values."""
    merged = dict(defaults)
    merged.update(frozen)
    merged.update(overrides)
    return merged


def _resolve_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()
