"""LoRA fine-tuning engine for a single HPO experiment."""

from __future__ import annotations

import json
import time
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch
import yaml
from peft import LoraConfig, TaskType, get_peft_model
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)

from training.config import PROJECT_ROOT, load_config
from training.dataset import (
    CausalLMSFTCollator,
    build_hf_dataset,
    load_system_prompt,
    load_training_jsonl,
    split_train_val,
    split_train_val_from_manifest,
)
from training.dataset_merge import geometry_group_key
from training.hpo.experiment import ExperimentResult, RunConfig
from training.hpo.metrics import ExperimentMetrics
from training.hpo.tracking import ExperimentTracker
from training.models.base import resolve_torch_dtype


DEFAULT_SYSTEM_PROMPT_PATH = PROJECT_ROOT / "dataset_v1" / "system_prompt.txt"


@dataclass
class TrainOptions:
    experiment_dir: Path
    max_steps: int | None = None
    dry_run: bool = False
    system_prompt_path: Path | None = DEFAULT_SYSTEM_PROMPT_PATH


def load_experiment_config(experiment_dir: Path) -> RunConfig:
    config_path = experiment_dir / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Experiment config not found: {config_path}")
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return ExperimentTracker._run_config_from_dict(raw)


def set_seed(seed: int) -> None:
    import random

    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def count_trainable_parameters(model: torch.nn.Module) -> int:
    return sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)


def resolve_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def resolve_training_batch_size(config: RunConfig, device: torch.device) -> int:
    batch_size = config.fixed.per_device_train_batch_size
    if device.type == "mps" and batch_size > 1:
        return 1
    return batch_size


def resolve_training_seq_length(config: RunConfig, device: torch.device) -> int:
    max_seq_length = config.fixed.max_seq_length
    if device.type == "mps" and max_seq_length > 2048:
        return 2048
    return max_seq_length


def prepare_model_for_training(model: Any) -> Any:
    if hasattr(model, "config"):
        model.config.use_cache = False
    if hasattr(model, "enable_input_require_grads"):
        model.enable_input_require_grads()
    if hasattr(model, "gradient_checkpointing_enable"):
        model.gradient_checkpointing_enable()
    return model


def load_model_and_tokenizer(config: RunConfig) -> tuple[Any, Any]:
    pipeline_config = load_config(PROJECT_ROOT / config.reproducibility.base_config)
    model_id = config.reproducibility.model_version
    tokenizer_kwargs: dict[str, Any] = {"trust_remote_code": pipeline_config.model.trust_remote_code}
    model_kwargs: dict[str, Any] = {
        "trust_remote_code": pipeline_config.model.trust_remote_code,
        "dtype": resolve_torch_dtype(),
    }
    if pipeline_config.paths.hf_cache is not None:
        cache_dir = str(pipeline_config.paths.hf_cache)
        tokenizer_kwargs["cache_dir"] = cache_dir
        model_kwargs["cache_dir"] = cache_dir

    tokenizer = AutoTokenizer.from_pretrained(model_id, **tokenizer_kwargs)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(model_id, **model_kwargs)
    device = resolve_device()
    if not torch.cuda.is_available():
        model = model.to(device)

    return model, tokenizer


def apply_lora(model: Any, config: RunConfig) -> Any:
    lora_config = LoraConfig(
        r=config.searchable.lora_r,
        lora_alpha=config.searchable.lora_alpha,
        lora_dropout=config.searchable.lora_dropout,
        target_modules=config.fixed.target_modules,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )
    return get_peft_model(model, lora_config)


def resolve_report_to(experiment_dir: Path) -> list[str]:
    try:
        import tensorboard  # noqa: F401
    except ImportError:
        return []
    return ["tensorboard"]


def resolve_train_val_split(
    records: list[dict[str, Any]],
    config: RunConfig,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    split_info: dict[str, Any] = {
        "split_strategy": config.reproducibility.split_strategy,
        "val_ratio": config.reproducibility.val_ratio,
        "seed": config.reproducibility.seed,
    }

    if config.reproducibility.split_strategy == "geometry_aware":
        manifest_path = config.reproducibility.split_manifest_path
        if not manifest_path:
            raise ValueError("geometry_aware split requires reproducibility.split_manifest_path")
        manifest_file = (PROJECT_ROOT / manifest_path).resolve()
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        train_records, val_records = split_train_val_from_manifest(records, manifest)
        split_info["split_manifest_path"] = str(manifest_file)
        split_info["train_examples"] = len(train_records)
        split_info["val_examples"] = len(val_records)
        split_info["train_geometries"] = len({geometry_group_key(record) for record in train_records})
        split_info["val_geometries"] = len({geometry_group_key(record) for record in val_records})
        return train_records, val_records, split_info

    train_records, val_records = split_train_val(
        records,
        seed=config.reproducibility.seed,
        val_ratio=config.reproducibility.val_ratio,
    )
    split_info["train_examples"] = len(train_records)
    split_info["val_examples"] = len(val_records)
    return train_records, val_records, split_info


def save_dataset_artifacts(
    experiment_dir: Path,
    *,
    dataset_path: Path,
    split_info: dict[str, Any],
    train_records: list[dict[str, Any]],
    val_records: list[dict[str, Any]],
) -> None:
    artifacts_dir = experiment_dir / "dataset"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "dataset_path": str(dataset_path),
        **split_info,
    }
    (artifacts_dir / "split_info.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (artifacts_dir / "train_examples.jsonl").write_text(
        "\n".join(json.dumps(record, ensure_ascii=False, separators=(",", ":")) for record in train_records) + "\n",
        encoding="utf-8",
    )
    (artifacts_dir / "val_examples.jsonl").write_text(
        "\n".join(json.dumps(record, ensure_ascii=False, separators=(",", ":")) for record in val_records) + "\n",
        encoding="utf-8",
    )


def save_training_curves(log_history: list[dict[str, Any]], experiment_dir: Path) -> None:
    curves_dir = experiment_dir / "curves"
    curves_dir.mkdir(parents=True, exist_ok=True)
    train_loss = [
        {"step": entry.get("step"), "loss": entry.get("loss")}
        for entry in log_history
        if entry.get("loss") is not None
    ]
    eval_loss = [
        {"step": entry.get("step"), "eval_loss": entry.get("eval_loss")}
        for entry in log_history
        if entry.get("eval_loss") is not None
    ]
    (curves_dir / "train_loss.json").write_text(json.dumps(train_loss, indent=2) + "\n", encoding="utf-8")
    (curves_dir / "eval_loss.json").write_text(json.dumps(eval_loss, indent=2) + "\n", encoding="utf-8")


def update_status(experiment_dir: Path, status: str, **extra: Any) -> None:
    payload = {
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **extra,
    }
    status_path = experiment_dir / "status.json"
    if status_path.exists():
        existing = json.loads(status_path.read_text(encoding="utf-8"))
        existing.update(payload)
        payload = existing
    (experiment_dir / "status.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_error_log(experiment_dir: Path, exc: BaseException) -> None:
    logs_dir = experiment_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / "error.log").write_text(traceback.format_exc(), encoding="utf-8")


def train_experiment(options: TrainOptions) -> ExperimentResult:
    experiment_dir = options.experiment_dir.resolve()
    config = load_experiment_config(experiment_dir)
    tracker = ExperimentTracker(experiment_dir.parent.parent)

    update_status(
        experiment_dir,
        "running",
        stage=config.stage,
        run_id=config.run_id,
        dry_run=options.dry_run,
    )

    set_seed(config.reproducibility.seed)
    start_time = time.time()
    device = resolve_device()
    train_batch_size = resolve_training_batch_size(config, device)
    max_seq_length = resolve_training_seq_length(config, device)

    dataset_path = (PROJECT_ROOT / config.reproducibility.dataset_path).resolve()
    records = load_training_jsonl(dataset_path)
    train_records, val_records, split_info = resolve_train_val_split(records, config)
    save_dataset_artifacts(
        experiment_dir,
        dataset_path=dataset_path,
        split_info=split_info,
        train_records=train_records,
        val_records=val_records,
    )
    system_prompt = load_system_prompt(options.system_prompt_path)

    model, tokenizer = load_model_and_tokenizer(config)
    model = apply_lora(model, config)
    model = prepare_model_for_training(model)
    trainable_parameters = count_trainable_parameters(model)

    train_dataset = build_hf_dataset(
        train_records,
        tokenizer,
        system_prompt=system_prompt,
        max_seq_length=max_seq_length,
    )
    eval_dataset = build_hf_dataset(
        val_records,
        tokenizer,
        system_prompt=system_prompt,
        max_seq_length=max_seq_length,
    )

    output_dir = experiment_dir / "checkpoints" / "trainer"
    output_dir.mkdir(parents=True, exist_ok=True)

    effective_max_steps = options.max_steps
    if options.dry_run and effective_max_steps is None:
        effective_max_steps = 5

    num_epochs = config.searchable.num_epochs
    training_args_kwargs: dict[str, Any] = {
        "output_dir": str(output_dir),
        "learning_rate": config.searchable.learning_rate,
        "per_device_train_batch_size": train_batch_size,
        "per_device_eval_batch_size": 1 if device.type == "mps" else config.fixed.per_device_eval_batch_size,
        "gradient_accumulation_steps": config.fixed.gradient_accumulation_steps,
        "weight_decay": config.fixed.weight_decay,
        "warmup_ratio": config.fixed.warmup_ratio,
        "lr_scheduler_type": config.fixed.scheduler,
        "optim": config.fixed.optimizer,
        "logging_steps": 1 if effective_max_steps else config.fixed.logging_steps,
        "eval_strategy": "steps",
        "eval_steps": max(1, min(config.fixed.eval_steps, effective_max_steps or config.fixed.eval_steps)),
        "save_strategy": "steps",
        "save_steps": max(1, min(config.fixed.save_steps, effective_max_steps or config.fixed.save_steps)),
        "save_total_limit": 2,
        "report_to": resolve_report_to(experiment_dir),
        "seed": config.reproducibility.seed,
        "remove_unused_columns": False,
        "label_names": ["labels"],
        "logging_dir": str(experiment_dir / "logs"),
        "dataloader_pin_memory": device.type == "cuda",
        "gradient_checkpointing": True,
        "bf16": bool(torch.cuda.is_available() and torch.cuda.is_bf16_supported()),
        "fp16": bool(torch.cuda.is_available() and not torch.cuda.is_bf16_supported()),
    }

    if effective_max_steps:
        training_args_kwargs["max_steps"] = effective_max_steps
        training_args_kwargs["num_train_epochs"] = 1
    else:
        training_args_kwargs["num_train_epochs"] = num_epochs

    training_args = TrainingArguments(**training_args_kwargs)

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        processing_class=tokenizer,
        data_collator=CausalLMSFTCollator(tokenizer),
    )

    train_result = trainer.train()
    eval_metrics = trainer.evaluate()

    adapter_dir = experiment_dir / "checkpoints" / "adapter"
    adapter_dir.mkdir(parents=True, exist_ok=True)
    trainer.model.save_pretrained(adapter_dir)
    tokenizer.save_pretrained(adapter_dir)

    elapsed = time.time() - start_time
    log_history = list(trainer.state.log_history)
    save_training_curves(log_history, experiment_dir)

    final_train_loss = train_result.training_loss
    final_val_loss = eval_metrics.get("eval_loss")

    metrics = ExperimentMetrics()
    metrics.core.train_loss = float(final_train_loss) if final_train_loss is not None else None
    metrics.core.val_loss = float(final_val_loss) if final_val_loss is not None else None
    metrics.core.training_time_seconds = elapsed
    metrics.core.trainable_parameters = trainable_parameters
    metrics.core.checkpoint_path = str(adapter_dir)

    result = ExperimentResult(
        stage=config.stage,
        run_id=config.run_id,
        run_dir=str(experiment_dir),
        config=config,
        metrics=metrics.to_dict(),
        status="completed",
        completed_at=datetime.now(timezone.utc).isoformat(),
    )
    tracker.save_result(result)
    update_status(experiment_dir, "completed", completed_at=result.completed_at, dry_run=options.dry_run)
    return result


def fail_experiment(experiment_dir: Path, config: RunConfig, exc: BaseException) -> ExperimentResult:
    write_error_log(experiment_dir, exc)
    metrics = ExperimentMetrics().to_dict()
    result = ExperimentResult(
        stage=config.stage,
        run_id=config.run_id,
        run_dir=str(experiment_dir),
        config=config,
        metrics=metrics,
        status="failed",
        completed_at=datetime.now(timezone.utc).isoformat(),
    )
    ExperimentTracker(experiment_dir.parent.parent).save_result(result)
    update_status(
        experiment_dir,
        "failed",
        error=str(exc),
        completed_at=result.completed_at,
    )
    return result
