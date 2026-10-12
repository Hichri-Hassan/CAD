#!/usr/bin/env python3
"""Evaluate CAD generation quality for thesis reporting."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch
import yaml
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from compiler.freecad_launcher import find_freecadcmd, run_in_freecad
from compiler.loader import load_cad_json
from dataset_v1.scripts.training_export import iter_training_examples
from training.config import load_config
from training.dataset import load_system_prompt
from training.lora_trainer import resolve_device
from training.models.base import move_inputs_to_device, resolve_torch_dtype


SUPPORTED_OPERATIONS = {"Sketch", "Pad", "Pocket", "Hole", "Fillet", "Chamfer"}


@dataclass
class ExampleResult:
    model_id: str
    prompt: str
    json_valid: bool
    schema_valid: bool
    operation_type_accuracy: float | None
    exact_operations_match: bool
    compilation_success: bool | None
    generated_operations_count: int | None
    reference_operations_count: int
    error: str | None = None


@dataclass
class EvaluationSummary:
    evaluated_at: str
    adapter_path: str
    test_models: int
    examples: int
    json_validity_rate: float
    schema_validity_rate: float
    mean_operation_type_accuracy: float | None
    exact_operations_match_rate: float
    compilation_success_rate: float | None
    freecad_available: bool


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate CAD generation quality.")
    parser.add_argument(
        "--adapter",
        type=Path,
        required=True,
        help="Path to LoRA adapter directory.",
    )
    parser.add_argument(
        "--test-json-dir",
        type=Path,
        default=PROJECT_ROOT / "dataset_v1" / "test" / "json",
        help="Held-out test canonical JSON directory.",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=PROJECT_ROOT / "dataset_v1" / "test" / "metadata.csv",
        help="Optional test metadata CSV.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "training" / "configs" / "qwen_3b.yaml",
        help="Base model pipeline config.",
    )
    parser.add_argument(
        "--system-prompt",
        type=Path,
        default=PROJECT_ROOT / "dataset_v1" / "system_prompt.txt",
        help="System prompt used during fine-tuning.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "training" / "evaluation",
        help="Directory for evaluation artifacts.",
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=4096,
        help="Maximum generated tokens per example.",
    )
    parser.add_argument(
        "--prompt-index",
        type=int,
        default=0,
        help="Use the Nth prompt per test model (default: first prompt).",
    )
    parser.add_argument(
        "--skip-compilation",
        action="store_true",
        help="Skip FreeCAD compilation checks.",
    )
    return parser


def extract_json_object(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    if start < 0:
        return None

    depth = 0
    for index, char in enumerate(text[start:], start=start):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                candidate = text[start : index + 1]
                try:
                    parsed = json.loads(candidate)
                except json.JSONDecodeError:
                    return None
                return parsed if isinstance(parsed, dict) else None
    return None


def validate_training_schema(payload: dict[str, Any]) -> bool:
    operations = payload.get("operations")
    if not isinstance(operations, list) or not operations:
        return False
    seen_ids: set[str] = set()
    for operation in operations:
        if not isinstance(operation, dict):
            return False
        op_id = operation.get("id")
        op_type = operation.get("type")
        if not isinstance(op_id, str) or not op_id or not isinstance(op_type, str):
            return False
        if op_type not in SUPPORTED_OPERATIONS:
            return False
        if op_id in seen_ids:
            return False
        seen_ids.add(op_id)
    return True


def operation_type_accuracy(
    generated: list[dict[str, Any]] | None,
    reference: list[dict[str, Any]],
) -> float | None:
    if generated is None:
        return None
    if not reference:
        return 1.0 if not generated else 0.0
    matches = 0
    total = max(len(reference), len(generated))
    for index in range(total):
        if index >= len(reference) or index >= len(generated):
            continue
        if generated[index].get("type") == reference[index].get("type"):
            matches += 1
    return matches / total


def exact_operations_match(
    generated: list[dict[str, Any]] | None,
    reference: list[dict[str, Any]],
) -> bool:
    if generated is None:
        return False
    return generated == reference


def wrap_for_compiler(payload: dict[str, Any]) -> dict[str, Any]:
    operations = payload.get("operations", [])
    return {
        "metadata": {
            "version": "1.0",
            "unit": "mm",
            "source_format": "generated",
            "parser_version": "eval",
        },
        "operations": operations,
    }


def try_compile(payload: dict[str, Any]) -> bool:
    wrapped = wrap_for_compiler(payload)
    with tempfile.TemporaryDirectory() as tmp:
        json_path = Path(tmp) / "generated.json"
        fcstd_path = Path(tmp) / "generated.FCStd"
        json_path.write_text(json.dumps(wrapped, indent=2), encoding="utf-8")
        try:
            load_cad_json(json_path)
        except ValueError:
            return False

        freecadcmd = find_freecadcmd()
        if freecadcmd is None:
            return False

        script_path = PROJECT_ROOT / "compiler" / "freecad_main.py"
        result = run_in_freecad(
            script_path,
            [str(json_path.resolve()), "-o", str(fcstd_path.resolve())],
        )
        return result.returncode == 0 and fcstd_path.exists()


def load_adapter_bundle(adapter_path: Path, config_path: Path):
    pipeline_config = load_config(config_path)
    model_id = pipeline_config.model.hf_model_id
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

    base_model = AutoModelForCausalLM.from_pretrained(model_id, **model_kwargs)
    model = PeftModel.from_pretrained(base_model, str(adapter_path))
    device = resolve_device()
    model = model.to(device)
    model.eval()
    return model, tokenizer, device, pipeline_config


def generate_operations(
    model,
    tokenizer,
    device,
    *,
    prompt: str,
    system_prompt: str,
    max_new_tokens: int,
    temperature: float,
    do_sample: bool,
) -> str:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]
    chat_text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = tokenizer(chat_text, return_tensors="pt")
    inputs = move_inputs_to_device(inputs, device)

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            do_sample=do_sample,
            pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
        )

    generated_ids = output_ids[0, inputs["input_ids"].shape[-1] :]
    return tokenizer.decode(generated_ids, skip_special_tokens=True).strip()


def iter_test_examples(
    test_json_dir: Path,
    metadata_path: Path | None,
    *,
    prompt_index: int,
) -> list[tuple[str, str, list[dict[str, Any]]]]:
    examples: list[tuple[str, str, list[dict[str, Any]]]] = []
    for example in iter_training_examples(test_json_dir, metadata_path=metadata_path):
        if example.prompt_index != prompt_index:
            continue
        examples.append((example.model_id, example.input, example.operations))
    return examples


def write_markdown_report(
    path: Path,
    summary: EvaluationSummary,
    results: list[ExampleResult],
) -> None:
    mean_op_line = (
        f"- **Mean operation-type accuracy:** {summary.mean_operation_type_accuracy:.1%}"
        if summary.mean_operation_type_accuracy is not None
        else "- **Mean operation-type accuracy:** —"
    )
    lines = [
        "# CAD Copilot Generation Evaluation",
        "",
        f"Generated: {summary.evaluated_at}",
        "",
        "## Summary",
        "",
        f"- **Adapter:** `{summary.adapter_path}`",
        f"- **Test models:** {summary.test_models}",
        f"- **Examples evaluated:** {summary.examples}",
        f"- **JSON validity:** {summary.json_validity_rate:.1%}",
        f"- **Schema validity:** {summary.schema_validity_rate:.1%}",
        mean_op_line,
        f"- **Exact operations match:** {summary.exact_operations_match_rate:.1%}",
    ]
    if summary.compilation_success_rate is not None:
        lines.append(f"- **Compilation success:** {summary.compilation_success_rate:.1%}")
    else:
        lines.append("- **Compilation success:** not measured (FreeCAD unavailable or skipped)")

    lines.extend(
        [
            "",
            "## Per-example Results",
            "",
            "| Model | JSON | Schema | Op-type acc | Exact match | Compile | Ops (gen/ref) |",
            "|---|---|---:|---:|---:|---:|---|",
        ]
    )
    for row in results:
        compile_cell = (
            "yes"
            if row.compilation_success is True
            else "no"
            if row.compilation_success is False
            else "—"
        )
        op_acc = f"{row.operation_type_accuracy:.1%}" if row.operation_type_accuracy is not None else "—"
        lines.append(
            f"| {row.model_id} | {'yes' if row.json_valid else 'no'} | "
            f"{'yes' if row.schema_valid else 'no'} | {op_acc} | "
            f"{'yes' if row.exact_operations_match else 'no'} | {compile_cell} | "
            f"{row.generated_operations_count or 0}/{row.reference_operations_count} |"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    adapter_path = args.adapter.resolve()
    if not adapter_path.exists():
        raise FileNotFoundError(f"Adapter not found: {adapter_path}")

    test_examples = iter_test_examples(
        args.test_json_dir.resolve(),
        args.metadata.resolve() if args.metadata.exists() else None,
        prompt_index=args.prompt_index,
    )
    if not test_examples:
        raise RuntimeError("No test examples found.")

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    generations_dir = output_dir / "generations"
    generations_dir.mkdir(parents=True, exist_ok=True)

    system_prompt = load_system_prompt(args.system_prompt)
    model, tokenizer, device, pipeline_config = load_adapter_bundle(adapter_path, args.config)

    freecad_available = find_freecadcmd() is not None and not args.skip_compilation
    results: list[ExampleResult] = []

    for model_id, prompt, reference_ops in test_examples:
        error = None
        raw_text = ""
        parsed: dict[str, Any] | None = None
        try:
            raw_text = generate_operations(
                model,
                tokenizer,
                device,
                prompt=prompt,
                system_prompt=system_prompt,
                max_new_tokens=args.max_new_tokens,
                temperature=pipeline_config.inference.temperature,
                do_sample=pipeline_config.inference.do_sample,
            )
            parsed = extract_json_object(raw_text)
        except Exception as exc:  # noqa: BLE001
            error = str(exc)

        (generations_dir / f"{model_id}.txt").write_text(raw_text, encoding="utf-8")
        if parsed is not None:
            (generations_dir / f"{model_id}.json").write_text(
                json.dumps(parsed, indent=2),
                encoding="utf-8",
            )

        json_valid = parsed is not None
        schema_valid = bool(parsed and validate_training_schema(parsed))
        generated_ops = parsed.get("operations") if parsed else None
        op_acc = operation_type_accuracy(generated_ops, reference_ops)
        exact_match = exact_operations_match(generated_ops, reference_ops)
        compile_ok: bool | None = None
        if freecad_available and schema_valid and parsed is not None:
            compile_ok = try_compile(parsed)

        results.append(
            ExampleResult(
                model_id=model_id,
                prompt=prompt,
                json_valid=json_valid,
                schema_valid=schema_valid,
                operation_type_accuracy=op_acc,
                exact_operations_match=exact_match,
                compilation_success=compile_ok,
                generated_operations_count=len(generated_ops) if isinstance(generated_ops, list) else None,
                reference_operations_count=len(reference_ops),
                error=error,
            )
        )

    json_valid_rate = sum(1 for r in results if r.json_valid) / len(results)
    schema_valid_rate = sum(1 for r in results if r.schema_valid) / len(results)
    op_accs = [r.operation_type_accuracy for r in results if r.operation_type_accuracy is not None]
    mean_op_acc = sum(op_accs) / len(op_accs) if op_accs else None
    exact_match_rate = sum(1 for r in results if r.exact_operations_match) / len(results)
    compile_results = [r.compilation_success for r in results if r.compilation_success is not None]
    compile_rate = sum(1 for ok in compile_results if ok) / len(compile_results) if compile_results else None

    summary = EvaluationSummary(
        evaluated_at=datetime.now(timezone.utc).isoformat(),
        adapter_path=str(adapter_path),
        test_models=len({r.model_id for r in results}),
        examples=len(results),
        json_validity_rate=json_valid_rate,
        schema_validity_rate=schema_valid_rate,
        mean_operation_type_accuracy=mean_op_acc,
        exact_operations_match_rate=exact_match_rate,
        compilation_success_rate=compile_rate,
        freecad_available=freecad_available,
    )

    results_path = output_dir / "generation_eval_results.json"
    results_path.write_text(
        json.dumps(
            {
                "summary": asdict(summary),
                "examples": [asdict(r) for r in results],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    write_markdown_report(output_dir / "generation_eval_report.md", summary, results)

    thesis_path = output_dir / "thesis_eval_summary.yaml"
    thesis_path.write_text(
        yaml.safe_dump(
            {
                "title": "CAD Copilot Final Model — Generation Quality",
                "adapter": str(adapter_path),
                "held_out_test_models": summary.test_models,
                "metrics": {
                    "json_validity": round(summary.json_validity_rate, 4),
                    "schema_validity": round(summary.schema_validity_rate, 4),
                    "operation_type_accuracy": round(mean_op_acc, 4) if mean_op_acc is not None else None,
                    "exact_operations_match": round(summary.exact_operations_match_rate, 4),
                    "compilation_success": round(compile_rate, 4) if compile_rate is not None else None,
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    print(json.dumps(asdict(summary), indent=2))
    print(f"Report: {output_dir / 'generation_eval_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
