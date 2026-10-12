"""Experiment directory management and artifact persistence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from training.hpo.experiment import ExperimentPlan, ExperimentResult, RunConfig
from training.hpo.metrics import empty_metrics
from training.hpo.search_space import HpoDefaults, StageDefinition


class ExperimentTracker:
    """Create and manage per-run experiment directories."""

    def __init__(self, experiments_root: Path) -> None:
        self.experiments_root = experiments_root.resolve()
        self.experiments_root.mkdir(parents=True, exist_ok=True)

    def stage_dir(self, stage_id: str) -> Path:
        return self.experiments_root / stage_id

    def run_dir(self, stage_id: str, run_id: str) -> Path:
        return self.stage_dir(stage_id) / run_id

    def initialize_run(self, plan: ExperimentPlan) -> Path:
        """Create run directory structure and write configuration artifacts."""
        directory = Path(plan.run_dir)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "logs").mkdir(exist_ok=True)
        (directory / "checkpoints").mkdir(exist_ok=True)
        (directory / "curves").mkdir(exist_ok=True)

        self._write_yaml(directory / "config.yaml", plan.config.to_dict())
        self._write_json(directory / "manifest.json", plan.to_dict())
        self._write_json(directory / "metrics.json", empty_metrics())
        self._write_json(
            directory / "status.json",
            {"status": "planned", "stage": plan.stage, "run_id": plan.run_id},
        )
        return directory

    def write_stage_manifest(self, stage_id: str, plans: list[ExperimentPlan], stage: StageDefinition) -> Path:
        directory = self.stage_dir(stage_id)
        directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "stage_id": stage_id,
            "name": stage.name,
            "description": stage.description,
            "depends_on": stage.depends_on,
            "selection_metric": stage.selection_metric,
            "selection_direction": stage.selection_direction,
            "search_space": stage.search,
            "run_count": len(plans),
            "runs": [
                {
                    "run_id": plan.run_id,
                    "run_dir": plan.run_dir,
                    "search_overrides": plan.search_overrides,
                    "frozen_from": plan.frozen_from,
                }
                for plan in plans
            ],
        }
        path = directory / "stage_manifest.json"
        self._write_json(path, payload)
        return path

    def write_master_manifest(
        self,
        all_plans: dict[str, list[ExperimentPlan]],
        defaults: HpoDefaults,
        stages: list[StageDefinition],
    ) -> Path:
        payload = {
            "strategy": "hierarchical_hpo",
            "dataset_version": defaults.dataset_version,
            "model_version": defaults.model_version,
            "seed": defaults.seed,
            "fixed_parameters": defaults.fixed,
            "stage_defaults": defaults.stage_defaults,
            "stages": {
                stage.stage_id: {
                    "name": stage.name,
                    "combinations": stage.combinations,
                    "depends_on": stage.depends_on,
                    "search": stage.search,
                }
                for stage in stages
            },
            "total_runs": sum(len(plans) for plans in all_plans.values()),
            "runs_by_stage": {stage_id: len(plans) for stage_id, plans in all_plans.items()},
        }
        path = self.experiments_root / "hpo_master_manifest.json"
        self._write_json(path, payload)
        return path

    def load_run_config(self, stage_id: str, run_id: str) -> RunConfig:
        path = self.run_dir(stage_id, run_id) / "config.yaml"
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        return self._run_config_from_dict(raw)

    def save_result(self, result: ExperimentResult) -> Path:
        directory = Path(result.run_dir)
        self._write_json(directory / "metrics.json", result.metrics)
        self._write_json(
            directory / "status.json",
            {
                "status": result.status,
                "stage": result.stage,
                "run_id": result.run_id,
                "completed_at": result.completed_at,
            },
        )
        self._write_json(directory / "result.json", result.to_dict())
        return directory / "result.json"

    def list_stage_results(self, stage_id: str) -> list[ExperimentResult]:
        stage_directory = self.stage_dir(stage_id)
        if not stage_directory.exists():
            return []

        results: list[ExperimentResult] = []
        for run_directory in sorted(stage_directory.glob("run_*")):
            result_path = run_directory / "result.json"
            metrics_path = run_directory / "metrics.json"
            config_path = run_directory / "config.yaml"
            status_path = run_directory / "status.json"
            if not config_path.exists():
                continue

            config = self._run_config_from_dict(yaml.safe_load(config_path.read_text(encoding="utf-8")))
            status = {"status": "planned"}
            if status_path.exists():
                status = json.loads(status_path.read_text(encoding="utf-8"))
            metrics = empty_metrics()
            if metrics_path.exists():
                metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            if result_path.exists():
                raw = json.loads(result_path.read_text(encoding="utf-8"))
                results.append(
                    ExperimentResult(
                        stage=raw["stage"],
                        run_id=raw["run_id"],
                        run_dir=raw["run_dir"],
                        config=config,
                        metrics=raw.get("metrics", metrics),
                        status=raw.get("status", status.get("status", "planned")),
                        completed_at=raw.get("completed_at"),
                    )
                )
            else:
                results.append(
                    ExperimentResult(
                        stage=stage_id,
                        run_id=run_directory.name,
                        run_dir=str(run_directory),
                        config=config,
                        metrics=metrics,
                        status=status.get("status", "planned"),
                    )
                )
        return results

    @staticmethod
    def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def _run_config_from_dict(raw: dict[str, Any]) -> RunConfig:
        from training.hpo.experiment import FixedHyperparameters, ReproducibilityInfo, SearchableHyperparameters

        reproducibility_raw = dict(raw.get("reproducibility", {}))
        reproducibility_defaults = {
            "split_manifest_path": None,
            "split_strategy": "random",
            "val_ratio": 0.1,
        }
        reproducibility = ReproducibilityInfo(
            **{**reproducibility_defaults, **reproducibility_raw}
        )

        return RunConfig(
            stage=raw["stage"],
            run_id=raw["run_id"],
            searchable=SearchableHyperparameters(**raw["searchable"]),
            fixed=FixedHyperparameters(**raw["fixed"]),
            reproducibility=reproducibility,
            created_at=raw.get("created_at", ""),
        )
