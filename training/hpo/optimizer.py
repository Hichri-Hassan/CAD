"""Hierarchical hyperparameter optimization orchestration."""

from __future__ import annotations

from typing import Any

from training.hpo.experiment import (
    ExperimentPlan,
    ExperimentResult,
    FixedHyperparameters,
    ReproducibilityInfo,
    RunConfig,
    SearchableHyperparameters,
)
from training.hpo.metrics import ExperimentMetrics
from training.hpo.search_space import (
    HpoDefaults,
    StageDefinition,
    get_stage_definition,
    iter_search_grid,
    load_hpo_defaults,
    load_stage_definitions,
    merge_hyperparameters,
)
from training.hpo.tracking import ExperimentTracker


class HierarchicalOptimizer:
    """Research-informed staged HPO for LoRA fine-tuning."""

    def __init__(
        self,
        defaults: HpoDefaults | None = None,
        stages: list[StageDefinition] | None = None,
        tracker: ExperimentTracker | None = None,
    ) -> None:
        self.defaults = defaults or load_hpo_defaults()
        self.stages = stages or load_stage_definitions()
        self.tracker = tracker or ExperimentTracker(self.defaults.experiments_root)

    def plan_stage(
        self,
        stage_id: str,
        *,
        frozen_hyperparameters: dict[str, Any] | None = None,
    ) -> list[ExperimentPlan]:
        """Generate every experiment plan for one optimization stage."""
        stage = get_stage_definition(stage_id, self.stages)
        frozen = frozen_hyperparameters or {}
        plans: list[ExperimentPlan] = []

        for run_index, overrides in enumerate(iter_search_grid(stage), start=1):
            run_id = f"run_{run_index:03d}"
            hyperparams = merge_hyperparameters(self.defaults.stage_defaults, frozen, overrides)
            config = self._build_run_config(stage_id, run_id, hyperparams)
            run_dir = str(self.tracker.stage_dir(stage_id) / run_id)
            plans.append(
                ExperimentPlan(
                    stage=stage_id,
                    run_id=run_id,
                    run_index=run_index,
                    config=config,
                    run_dir=run_dir,
                    search_overrides=overrides,
                    frozen_from=frozen,
                )
            )
        return plans

    def plan_all_stages(
        self,
        *,
        stage1_best: dict[str, Any] | None = None,
        stage2_best: dict[str, Any] | None = None,
    ) -> dict[str, list[ExperimentPlan]]:
        """Plan all stages; later stages use provided best configs or defaults."""
        stage1 = self.plan_stage("stage1")
        frozen_after_stage1 = stage1_best or self._placeholder_best("stage1", stage1)
        stage2 = self.plan_stage("stage2", frozen_hyperparameters=frozen_after_stage1)
        frozen_after_stage2 = stage2_best or self._placeholder_best(
            "stage2",
            stage2,
            extra_frozen=frozen_after_stage1,
        )
        stage3 = self.plan_stage("stage3", frozen_hyperparameters=frozen_after_stage2)
        return {"stage1": stage1, "stage2": stage2, "stage3": stage3}

    def select_best(
        self,
        stage_id: str,
        results: list[ExperimentResult],
        *,
        metric: str | None = None,
    ) -> ExperimentResult:
        """Select the best experiment from a completed stage."""
        stage = get_stage_definition(stage_id, self.stages)
        metric_name = metric or stage.selection_metric
        completed = [result for result in results if result.status == "completed"]
        if not completed:
            raise ValueError(f"No completed experiments found for {stage_id}.")

        def score(result: ExperimentResult) -> float:
            metrics = ExperimentMetrics.from_dict(result.metrics)
            value = metrics.selection_value(metric_name)
            if value is None:
                raise ValueError(
                    f"Experiment {result.run_id} is missing selection metric '{metric_name}'."
                )
            return value

        reverse = stage.selection_direction == "max"
        return sorted(completed, key=score, reverse=reverse)[0]

    def best_hyperparameters(self, result: ExperimentResult) -> dict[str, Any]:
        """Extract searchable hyperparameters from a winning experiment."""
        searchable = result.config.searchable
        return {
            "lora_r": searchable.lora_r,
            "learning_rate": searchable.learning_rate,
            "num_epochs": searchable.num_epochs,
            "lora_dropout": searchable.lora_dropout,
            "lora_alpha": searchable.lora_alpha,
        }

    def prepare_experiments(
        self,
        *,
        stage1_best: dict[str, Any] | None = None,
        stage2_best: dict[str, Any] | None = None,
    ) -> dict[str, list[ExperimentPlan]]:
        """Write experiment directories and manifests for all planned stages."""
        all_plans = self.plan_all_stages(stage1_best=stage1_best, stage2_best=stage2_best)
        for stage_id, plans in all_plans.items():
            self.tracker.write_stage_manifest(stage_id, plans, stage=get_stage_definition(stage_id, self.stages))
            for plan in plans:
                self.tracker.initialize_run(plan)
        self.tracker.write_master_manifest(all_plans, self.defaults, self.stages)
        return all_plans

    def _build_run_config(self, stage_id: str, run_id: str, hyperparams: dict[str, Any]) -> RunConfig:
        fixed_raw = self.defaults.fixed
        return RunConfig(
            stage=stage_id,
            run_id=run_id,
            searchable=SearchableHyperparameters(
                lora_r=int(hyperparams["lora_r"]),
                learning_rate=float(hyperparams["learning_rate"]),
                num_epochs=int(hyperparams["num_epochs"]),
                lora_dropout=float(hyperparams["lora_dropout"]),
                lora_alpha=int(hyperparams["lora_alpha"]),
            ),
            fixed=FixedHyperparameters(
                weight_decay=float(fixed_raw["weight_decay"]),
                max_seq_length=int(fixed_raw["max_seq_length"]),
                optimizer=str(fixed_raw["optimizer"]),
                scheduler=str(fixed_raw["scheduler"]),
                warmup_ratio=float(fixed_raw["warmup_ratio"]),
                per_device_train_batch_size=int(fixed_raw["per_device_train_batch_size"]),
                per_device_eval_batch_size=int(fixed_raw["per_device_eval_batch_size"]),
                gradient_accumulation_steps=int(fixed_raw["gradient_accumulation_steps"]),
                logging_steps=int(fixed_raw["logging_steps"]),
                eval_steps=int(fixed_raw["eval_steps"]),
                save_steps=int(fixed_raw["save_steps"]),
                target_modules=list(fixed_raw["target_modules"]),
            ),
            reproducibility=ReproducibilityInfo(
                seed=self.defaults.seed,
                dataset_version=self.defaults.dataset_version,
                dataset_path=self.defaults.dataset_path,
                model_version=self.defaults.model_version,
                base_config=self.defaults.base_config,
            ),
        )

    def _placeholder_best(
        self,
        stage_id: str,
        plans: list[ExperimentPlan],
        *,
        extra_frozen: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Use stage defaults for planning when prior stage results are not yet available."""
        if not plans:
            return dict(self.defaults.stage_defaults)
        merged = dict(self.defaults.stage_defaults)
        if extra_frozen:
            merged.update(extra_frozen)
        stage = get_stage_definition(stage_id, self.stages)
        for key in stage.search:
            merged.setdefault(key, self.defaults.stage_defaults.get(key))
        return merged

    def summary(self) -> dict[str, Any]:
        """Return a concise description of the planned search."""
        return {
            "strategy": "hierarchical",
            "stages": [
                {
                    "stage_id": stage.stage_id,
                    "name": stage.name,
                    "combinations": stage.combinations,
                    "search": stage.search,
                    "depends_on": stage.depends_on,
                    "selection_metric": stage.selection_metric,
                }
                for stage in self.stages
            ],
            "total_combinations": sum(stage.combinations for stage in self.stages),
            "fixed_parameters": list(self.defaults.fixed.keys()),
            "defaults": self.defaults.stage_defaults,
        }
