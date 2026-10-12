"""Load test examples, ground truth, and saved generations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dataset_v1.scripts.training_export import iter_training_examples, load_canonical_document
from training.evaluation_app.config import AppPaths, default_paths
from training.evaluation_app.metrics import ExampleAnalysis, analyze_example, validate_payload_schema
from training.scripts.evaluate_generation import extract_json_object


@dataclass
class EvalExample:
    model_id: str
    prompt: str
    prompt_index: int
    reference_ops: list[dict[str, Any]]
    reference_document: dict[str, Any]
    generated_ops: list[dict[str, Any]] | None
    generated_raw: str | None
    generated_payload: dict[str, Any] | None
    json_valid: bool
    schema_valid: bool
    compilation_success: bool | None
    generation_status: str
    analysis: ExampleAnalysis

    @property
    def filename(self) -> str:
        return f"{self.model_id}.json"


def _load_saved_generation(generations_dir: Path, model_id: str) -> tuple[str | None, dict[str, Any] | None]:
    json_path = generations_dir / f"{model_id}.json"
    txt_path = generations_dir / f"{model_id}.txt"
    raw_text = txt_path.read_text(encoding="utf-8") if txt_path.exists() else None
    payload: dict[str, Any] | None = None
    if json_path.exists():
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    elif raw_text:
        payload = extract_json_object(raw_text)
    return raw_text, payload


def _load_results_index(results_path: Path) -> dict[str, dict[str, Any]]:
    if not results_path.exists():
        return {}
    data = json.loads(results_path.read_text(encoding="utf-8"))
    return {row["model_id"]: row for row in data.get("examples", [])}


def load_eval_examples(
    paths: AppPaths | None = None,
    *,
    prompt_index: int | None = 0,
) -> list[EvalExample]:
    paths = paths or default_paths()
    results_index = _load_results_index(paths.results_json)
    examples: list[EvalExample] = []

    for item in iter_training_examples(paths.test_json_dir, metadata_path=paths.metadata):
        if prompt_index is not None and item.prompt_index != prompt_index:
            continue

        json_path = paths.test_json_dir / f"{item.model_id}.json"
        document = load_canonical_document(json_path)
        raw_text, payload = _load_saved_generation(paths.generations_dir, item.model_id)
        result_row = results_index.get(item.model_id, {})

        generated_ops = payload.get("operations") if isinstance(payload, dict) else None
        json_valid = payload is not None
        schema_valid = validate_payload_schema(payload) if payload else False
        compilation_success = result_row.get("compilation_success")
        generation_status = "generated" if raw_text else "not_generated"

        analysis = analyze_example(
            model_id=item.model_id,
            prompt=item.input,
            reference_ops=item.operations,
            generated_ops=generated_ops if isinstance(generated_ops, list) else None,
            json_valid=json_valid,
            schema_valid=schema_valid,
            compilation_success=compilation_success,
            generation_status=generation_status,
        )

        examples.append(
            EvalExample(
                model_id=item.model_id,
                prompt=item.input,
                prompt_index=item.prompt_index,
                reference_ops=item.operations,
                reference_document=document,
                generated_ops=generated_ops if isinstance(generated_ops, list) else None,
                generated_raw=raw_text,
                generated_payload=payload,
                json_valid=json_valid,
                schema_valid=schema_valid,
                compilation_success=compilation_success,
                generation_status=generation_status,
                analysis=analysis,
            )
        )

    examples.sort(key=lambda ex: ex.model_id)
    return examples


def load_all_prompt_variants(paths: AppPaths | None = None) -> list[EvalExample]:
    """Load every prompt index for dataset exploration."""
    paths = paths or default_paths()
    all_examples: list[EvalExample] = []
    prompt_indices = {
        ex.prompt_index
        for ex in iter_training_examples(paths.test_json_dir, metadata_path=paths.metadata)
    }
    for prompt_index in sorted(prompt_indices):
        all_examples.extend(load_eval_examples(paths, prompt_index=prompt_index))
    return all_examples


def dataset_stats(examples: list[EvalExample]) -> dict[str, Any]:
    from collections import Counter

    op_counter: Counter[str] = Counter()
    prompt_lengths: list[int] = []
    op_counts: list[int] = []

    for example in examples:
        prompt_lengths.append(len(example.prompt))
        op_counts.append(len(example.reference_ops))
        for op in example.reference_ops:
            op_counter[str(op.get("type", "?"))] += 1

    return {
        "example_count": len(examples),
        "unique_models": len({ex.model_id for ex in examples}),
        "operation_frequency": dict(op_counter),
        "avg_prompt_length": sum(prompt_lengths) / len(prompt_lengths) if prompt_lengths else 0,
        "avg_operation_count": sum(op_counts) / len(op_counts) if op_counts else 0,
        "prompt_lengths": prompt_lengths,
        "operation_counts": op_counts,
    }
