#!/usr/bin/env python3
"""Run a 100-step benchmark and collect detailed timing/memory metrics.

Also tests checkpoint save/reload/resume.
"""

from __future__ import annotations

import gc
import json
import os
import resource
import statistics
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import torch
from peft import PeftModel
from transformers import Trainer, TrainingArguments

from training.dataset import (
    CausalLMSFTCollator,
    build_hf_dataset,
    load_system_prompt,
    load_training_jsonl,
)
from training.dataset_merge import geometry_group_key, split_records_by_geometry
from training.lora_trainer import (
    apply_lora,
    count_trainable_parameters,
    load_model_and_tokenizer,
    prepare_model_for_training,
    resolve_device,
    resolve_report_to,
    resolve_training_batch_size,
    resolve_training_seq_length,
    set_seed,
)
from training.hpo.experiment import RunConfig
from training.hpo.tracking import ExperimentTracker

import yaml


class TimingCallback:
    """Records wall-clock time for each training step."""

    def __init__(self):
        self.step_times: list[float] = []
        self._step_start: float | None = None

    def on_step_begin(self, args, state, control, **kwargs):
        self._step_start = time.perf_counter()

    def on_step_end(self, args, state, control, **kwargs):
        if self._step_start is not None:
            self.step_times.append(time.perf_counter() - self._step_start)
            self._step_start = None

    def on_log(self, args, state, control, **kwargs):
        pass


from transformers import TrainerCallback


class TimingTrainerCallback(TrainerCallback):
    def __init__(self, timing: TimingCallback):
        self._timing = timing

    def on_step_begin(self, args, state, control, **kwargs):
        self._timing.on_step_begin(args, state, control, **kwargs)

    def on_step_end(self, args, state, control, **kwargs):
        self._timing.on_step_end(args, state, control, **kwargs)


def get_memory_info() -> dict[str, float]:
    ru = resource.getrusage(resource.RUSAGE_SELF)
    peak_mb = ru.ru_maxrss / (1024 * 1024) if sys.platform == "darwin" else ru.ru_maxrss / 1024
    info = {"peak_rss_mb": round(peak_mb, 1)}
    try:
        import psutil
        proc = psutil.Process()
        mem = proc.memory_info()
        info["rss_mb"] = round(mem.rss / (1024 ** 2), 1)
        swap = psutil.swap_memory()
        info["swap_used_mb"] = round(swap.used / (1024 ** 2), 1)
        info["swap_total_mb"] = round(swap.total / (1024 ** 2), 1)
    except ImportError:
        pass
    return info


def main() -> int:
    experiment_dir = PROJECT_ROOT / "training" / "experiments" / "hole_lora_benchmark" / "run_001"
    config_path = experiment_dir / "config.yaml"
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    config = ExperimentTracker._run_config_from_dict(raw)

    set_seed(config.reproducibility.seed)
    device = resolve_device()
    train_batch_size = resolve_training_batch_size(config, device)
    max_seq_length = resolve_training_seq_length(config, device)

    print(f"Device: {device}")
    print(f"Train batch size (effective on device): {train_batch_size}")
    print(f"Max seq length (effective on device): {max_seq_length}")
    print(f"Gradient accumulation: {config.fixed.gradient_accumulation_steps}")
    print(f"Effective batch size: {train_batch_size * config.fixed.gradient_accumulation_steps}")

    # Load dataset
    dataset_path = (PROJECT_ROOT / config.reproducibility.dataset_path).resolve()
    records = load_training_jsonl(dataset_path)

    manifest_path = (PROJECT_ROOT / config.reproducibility.split_manifest_path).resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    geometry_splits = manifest["geometry_splits"]

    train_records, val_records = split_records_by_geometry(records, geometry_splits)
    print(f"\nTrain examples: {len(train_records)}")
    print(f"Val examples:   {len(val_records)}")

    system_prompt = load_system_prompt(PROJECT_ROOT / "dataset_v1" / "system_prompt.txt")

    # Calculate optimizer steps per epoch
    steps_per_epoch = len(train_records) // (train_batch_size * config.fixed.gradient_accumulation_steps)
    total_steps_8_epochs = steps_per_epoch * 8
    print(f"\nOptimizer steps/epoch: {steps_per_epoch}")
    print(f"Total steps (8 epochs): {total_steps_8_epochs}")

    # Load model
    print("\nLoading model...")
    t0 = time.perf_counter()
    model, tokenizer = load_model_and_tokenizer(config)
    model = apply_lora(model, config)
    model = prepare_model_for_training(model)
    model_load_time = time.perf_counter() - t0
    print(f"Model loaded in {model_load_time:.1f}s")
    print(f"Trainable parameters: {count_trainable_parameters(model):,}")
    print(f"Device of first param: {next(model.parameters()).device}")

    # Verify MPS
    first_device = next(model.parameters()).device
    if first_device.type != "mps" and torch.backends.mps.is_available():
        print("WARNING: MPS available but model is on", first_device)

    train_dataset = build_hf_dataset(train_records, tokenizer, system_prompt=system_prompt, max_seq_length=max_seq_length)
    eval_dataset = build_hf_dataset(val_records[:20], tokenizer, system_prompt=system_prompt, max_seq_length=max_seq_length)

    output_dir = experiment_dir / "checkpoints" / "trainer"
    output_dir.mkdir(parents=True, exist_ok=True)

    max_steps = int(os.environ.get("BENCHMARK_STEPS", "20"))
    save_at = max(5, max_steps // 2)
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        learning_rate=config.searchable.learning_rate,
        per_device_train_batch_size=train_batch_size,
        per_device_eval_batch_size=1 if device.type == "mps" else config.fixed.per_device_eval_batch_size,
        gradient_accumulation_steps=config.fixed.gradient_accumulation_steps,
        weight_decay=config.fixed.weight_decay,
        warmup_ratio=config.fixed.warmup_ratio,
        lr_scheduler_type=config.fixed.scheduler,
        optim=config.fixed.optimizer,
        logging_steps=1,
        eval_strategy="no",
        save_strategy="steps",
        save_steps=save_at,
        save_total_limit=2,
        max_steps=max_steps,
        num_train_epochs=1,
        report_to=[],
        seed=config.reproducibility.seed,
        remove_unused_columns=False,
        label_names=["labels"],
        logging_dir=str(experiment_dir / "logs"),
        dataloader_pin_memory=device.type == "cuda",
        gradient_checkpointing=True,
        bf16=bool(torch.cuda.is_available() and torch.cuda.is_bf16_supported()),
        fp16=bool(torch.cuda.is_available() and not torch.cuda.is_bf16_supported()),
    )

    timing = TimingCallback()
    timing_cb = TimingTrainerCallback(timing)

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        processing_class=tokenizer,
        data_collator=CausalLMSFTCollator(tokenizer),
        callbacks=[timing_cb],
    )

    # Run benchmark
    print(f"\n{'='*60}")
    print(f"Starting 100-step benchmark...")
    print(f"{'='*60}")

    mem_before = get_memory_info()
    wall_start = time.perf_counter()
    train_result = trainer.train()
    wall_end = time.perf_counter()
    mem_after = get_memory_info()

    total_wall_time = wall_end - wall_start
    step_times = timing.step_times

    print(f"\nBenchmark completed in {total_wall_time:.1f}s")
    print(f"Steps recorded: {len(step_times)}")

    # Timing analysis
    warmup_skip = min(3, len(step_times) // 4)
    if len(step_times) >= 10:
        first_10 = step_times[:min(10, len(step_times))]
        last_50 = step_times[-(min(50, len(step_times))):]
        steady_state = step_times[warmup_skip:]
    else:
        first_10 = step_times
        last_50 = step_times
        steady_state = step_times

    avg_sec = statistics.mean(step_times) if step_times else 0
    median_sec = statistics.median(step_times) if step_times else 0
    first_10_avg = statistics.mean(first_10) if first_10 else 0
    last_50_avg = statistics.mean(last_50) if last_50 else 0
    steady_avg = statistics.mean(steady_state) if steady_state else 0

    effective_batch = train_batch_size * config.fixed.gradient_accumulation_steps
    examples_per_sec = effective_batch / steady_avg if steady_avg > 0 else 0

    print(f"\n{'='*60}")
    print("TIMING RESULTS")
    print(f"{'='*60}")
    print(f"Total wall-clock time:    {total_wall_time:.1f}s")
    print(f"Average sec/step:         {avg_sec:.3f}")
    print(f"Median sec/step:          {median_sec:.3f}")
    print(f"First 10 steps avg:       {first_10_avg:.3f}")
    print(f"Last 50 steps avg:        {last_50_avg:.3f}")
    print(f"Steady-state avg (>10):   {steady_avg:.3f}")
    print(f"Examples/sec:             {examples_per_sec:.2f}")

    # Check for speed degradation
    if len(step_times) >= 8:
        mid = len(step_times) // 2
        first_half = statistics.mean(step_times[warmup_skip:mid])
        second_half = statistics.mean(step_times[mid:])
        drift_pct = (second_half - first_half) / first_half * 100
        print(f"\nSpeed drift (1st vs 2nd half): {drift_pct:+.1f}%")
        if abs(drift_pct) > 15:
            print("WARNING: Significant speed drift detected!")

    print(f"\n{'='*60}")
    print("MEMORY")
    print(f"{'='*60}")
    print(f"Before training: {mem_before}")
    print(f"After training:  {mem_after}")
    if "peak_rss_mb" in mem_after:
        peak_gb = mem_after["peak_rss_mb"] / 1024
        print(f"Peak RSS:        {peak_gb:.1f} GB")

    print(f"\n{'='*60}")
    print("FULL TRAINING PROJECTION")
    print(f"{'='*60}")
    print(f"Train examples:         {len(train_records)}")
    print(f"Effective batch size:   {effective_batch}")
    print(f"Optimizer steps/epoch:  {steps_per_epoch}")
    print(f"Total steps (8 epochs): {total_steps_8_epochs}")
    print(f"Steady-state sec/step:  {steady_avg:.3f}")

    raw_train_sec = total_steps_8_epochs * steady_avg
    raw_train_hrs = raw_train_sec / 3600
    overhead_factor = 1.15
    realistic_sec = raw_train_sec * overhead_factor
    realistic_hrs = realistic_sec / 3600
    realistic_days = realistic_hrs / 24

    # Cross-reference with previous final experiment
    prev_time = 77701.3
    prev_steps = 400
    prev_sec_per_step = prev_time / prev_steps
    print(f"\nPrevious final experiment:   {prev_sec_per_step:.1f} sec/step ({prev_time:.0f}s / {prev_steps} steps)")
    print(f"Current benchmark:           {steady_avg:.1f} sec/step")

    print(f"\nRaw training estimate:       {raw_train_hrs:.1f} hours")
    print(f"Realistic estimate (+15%):   {realistic_hrs:.1f} hours ≈ {realistic_days:.1f} days")

    low_factor = 0.95
    high_factor = 1.25
    print(f"Estimated range:             {raw_train_sec * low_factor / 3600:.1f} – {raw_train_sec * high_factor / 3600:.1f} hours")

    # ===== CHECKPOINT/RESUME TEST =====
    print(f"\n{'='*60}")
    print("CHECKPOINT/RESUME TEST")
    print(f"{'='*60}")

    checkpoint_pass = False
    resume_pass = False

    # Find checkpoint saved at step 50
    ckpt_dirs = sorted(output_dir.glob("checkpoint-*"))
    if ckpt_dirs:
        ckpt_dir = ckpt_dirs[-1]
        print(f"Checkpoint found: {ckpt_dir.name}")
        checkpoint_pass = True

        # Check saved files
        adapter_files = list(ckpt_dir.glob("adapter_model*"))
        optimizer_files = list(ckpt_dir.glob("optimizer*"))
        scheduler_files = list(ckpt_dir.glob("scheduler*"))
        trainer_state = ckpt_dir / "trainer_state.json"

        print(f"  Adapter files:   {len(adapter_files) > 0} ({len(adapter_files)})")
        print(f"  Optimizer:       {len(optimizer_files) > 0}")
        print(f"  Scheduler:       {len(scheduler_files) > 0}")
        print(f"  Trainer state:   {trainer_state.exists()}")

        if trainer_state.exists():
            ts = json.loads(trainer_state.read_text(encoding="utf-8"))
            saved_step = ts.get("global_step", -1)
            print(f"  Saved step:      {saved_step}")

        # Resume test: load from checkpoint, run 5 more steps
        print("\nResuming from checkpoint for 5 steps...")
        try:
            del trainer
            del model
            gc.collect()
            if torch.backends.mps.is_available():
                torch.mps.empty_cache()

            model2, tokenizer2 = load_model_and_tokenizer(config)
            model2 = apply_lora(model2, config)
            model2 = prepare_model_for_training(model2)

            resume_args = TrainingArguments(
                output_dir=str(output_dir),
                learning_rate=config.searchable.learning_rate,
                per_device_train_batch_size=train_batch_size,
                per_device_eval_batch_size=1,
                gradient_accumulation_steps=config.fixed.gradient_accumulation_steps,
                weight_decay=config.fixed.weight_decay,
                warmup_ratio=config.fixed.warmup_ratio,
                lr_scheduler_type=config.fixed.scheduler,
                optim=config.fixed.optimizer,
                logging_steps=1,
                max_steps=saved_step + 5,
                num_train_epochs=1,
                save_strategy="no",
                eval_strategy="no",
                report_to=[],
                seed=config.reproducibility.seed,
                remove_unused_columns=False,
                label_names=["labels"],
                logging_dir=str(experiment_dir / "logs_resume"),
                dataloader_pin_memory=False,
                gradient_checkpointing=True,
                bf16=False,
                fp16=False,
            )

            resume_trainer = Trainer(
                model=model2,
                args=resume_args,
                train_dataset=train_dataset,
                eval_dataset=eval_dataset,
                processing_class=tokenizer2,
                data_collator=CausalLMSFTCollator(tokenizer2),
            )

            resume_result = resume_trainer.train(resume_from_checkpoint=str(ckpt_dir))
            resumed_step = resume_trainer.state.global_step
            print(f"  Resumed to step: {resumed_step}")
            expected_step = saved_step + 5
            if resumed_step == expected_step:
                print(f"  Step correct:    PASS ({resumed_step} == {expected_step})")
                resume_pass = True
            else:
                print(f"  Step mismatch:   FAIL ({resumed_step} != {expected_step})")
        except Exception as exc:
            print(f"  Resume FAILED: {exc}")
    else:
        print("No checkpoint found - FAIL")

    # ===== FINAL REPORT =====
    mps_pass = first_device.type == "mps"

    print(f"\n{'='*60}")
    print("FINAL BENCHMARK REPORT")
    print(f"{'='*60}")
    print(f"\n--- Dataset ---")
    print(f"Original CAD:       235 → {sum(1 for r in records if r.get('dataset_source') == 'cad_v1')}")
    print(f"Primitives:         500 → {sum(1 for r in records if r.get('dataset_source') == 'primitives_v1')}")
    print(f"Through-holes:      375 → {sum(1 for r in records if r.get('dataset_source') == 'through_hole_v1')}")
    print(f"Blind-holes:        340 → {sum(1 for r in records if r.get('dataset_source') == 'blind_hole_v1')}")
    print(f"Total (deduped):    {len(records)}")
    print(f"Train:              {len(train_records)}")
    print(f"Val:                {len(val_records)}")
    unique_geo = len({geometry_group_key(r) for r in records})
    print(f"Unique geometries:  {unique_geo}")
    print(f"Split manifest:     {manifest_path}")

    print(f"\n--- Benchmark ---")
    print(f"Steps completed:    {len(step_times)}")
    print(f"Total time:         {total_wall_time:.1f}s")
    print(f"Avg sec/step:       {avg_sec:.3f}")
    print(f"Median sec/step:    {median_sec:.3f}")
    print(f"Steady sec/step:    {steady_avg:.3f}")
    print(f"First 10 avg:       {first_10_avg:.3f}")
    print(f"Last 50 avg:        {last_50_avg:.3f}")
    print(f"Examples/sec:       {examples_per_sec:.2f}")
    print(f"Peak RSS:           {mem_after.get('peak_rss_mb', '?')} MB")
    print(f"Device:             {first_device}")

    print(f"\n--- Full Training Projection ---")
    print(f"Steps/epoch:        {steps_per_epoch}")
    print(f"Total steps (8ep):  {total_steps_8_epochs}")
    print(f"Steady sec/step:    {steady_avg:.3f}")
    print(f"Raw time/epoch:     {steps_per_epoch * steady_avg / 3600:.1f} hours")
    print(f"Raw total (8ep):    {raw_train_hrs:.1f} hours")
    print(f"Realistic total:    {realistic_hrs:.1f} hours ≈ {realistic_days:.1f} days")
    print(f"Range:              {raw_train_sec * low_factor / 3600:.1f} – {raw_train_sec * high_factor / 3600:.1f} hours")

    print(f"\n--- Reliability ---")
    print(f"Checkpoint create:  {'PASS' if checkpoint_pass else 'FAIL'}")
    print(f"Checkpoint reload:  {'PASS' if resume_pass else 'FAIL'}")
    print(f"Resume training:    {'PASS' if resume_pass else 'FAIL'}")
    print(f"MPS usage:          {'PASS' if mps_pass else 'FAIL'}")

    all_pass = checkpoint_pass and resume_pass and mps_pass
    print(f"\n{'='*60}")
    if all_pass and steady_avg > 0:
        print("RECOMMENDATION: SAFE TO START FULL TRAINING")
    else:
        reasons = []
        if not checkpoint_pass:
            reasons.append("checkpoint creation failed")
        if not resume_pass:
            reasons.append("checkpoint resume failed")
        if not mps_pass:
            reasons.append("not using MPS")
        print(f"RECOMMENDATION: DO NOT START YET — {', '.join(reasons)}")
    print(f"{'='*60}")

    # Save report JSON
    report = {
        "dataset": {
            "cad": sum(1 for r in records if r.get("dataset_source") == "cad_v1"),
            "primitives": sum(1 for r in records if r.get("dataset_source") == "primitives_v1"),
            "through_holes": sum(1 for r in records if r.get("dataset_source") == "through_hole_v1"),
            "blind_holes": sum(1 for r in records if r.get("dataset_source") == "blind_hole_v1"),
            "total": len(records),
            "train": len(train_records),
            "val": len(val_records),
            "unique_geometries": unique_geo,
        },
        "benchmark": {
            "steps": len(step_times),
            "total_wall_time_s": round(total_wall_time, 1),
            "avg_sec_per_step": round(avg_sec, 3),
            "median_sec_per_step": round(median_sec, 3),
            "steady_sec_per_step": round(steady_avg, 3),
            "first_10_avg": round(first_10_avg, 3),
            "last_50_avg": round(last_50_avg, 3),
            "examples_per_sec": round(examples_per_sec, 2),
            "peak_rss_mb": mem_after.get("peak_rss_mb"),
            "device": str(first_device),
        },
        "projection": {
            "steps_per_epoch": steps_per_epoch,
            "total_steps_8_epochs": total_steps_8_epochs,
            "raw_hours": round(raw_train_hrs, 1),
            "realistic_hours": round(realistic_hrs, 1),
            "realistic_days": round(realistic_days, 1),
        },
        "reliability": {
            "checkpoint_create": checkpoint_pass,
            "checkpoint_resume": resume_pass,
            "mps_usage": mps_pass,
        },
        "recommendation": "SAFE TO START FULL TRAINING" if all_pass else "DO NOT START YET",
    }
    report_path = experiment_dir / "benchmark_report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"\nReport saved to: {report_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
