"""Export supervised fine-tuning datasets from canonical CAD JSON files."""

from __future__ import annotations

import csv
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator


@dataclass(frozen=True)
class TrainingExample:
    """One prompt paired with a CAD program."""

    input: str
    operations: list[dict[str, Any]]
    model_id: str = ""
    prompt_index: int = 0


def load_canonical_document(path: Path) -> dict[str, Any]:
    """Load one canonical dataset JSON file."""
    return json.loads(path.read_text(encoding="utf-8"))


def extract_operations(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the CAD program from a canonical dataset document."""
    operations = document.get("operations")
    if not isinstance(operations, list) or not operations:
        raise ValueError("Canonical document is missing a non-empty 'operations' list.")
    return operations


def iter_training_examples(
    json_dir: Path,
    *,
    metadata_path: Path | None = None,
) -> Iterator[TrainingExample]:
    """Yield one training example per prompt without modifying source files."""
    json_dir = json_dir.resolve()
    documents = _load_documents(json_dir, metadata_path)

    for model_id, json_path in documents:
        document = load_canonical_document(json_path)
        operations = extract_operations(document)
        prompts = document.get("prompts", [])

        if not isinstance(prompts, list) or not prompts:
            raise ValueError(f"{json_path.name} is missing a non-empty 'prompts' list.")

        for prompt_index, prompt in enumerate(prompts):
            if not isinstance(prompt, str) or not prompt.strip():
                raise ValueError(f"{json_path.name} has an empty prompt at index {prompt_index}.")
            yield TrainingExample(
                input=prompt.strip(),
                operations=operations,
                model_id=model_id,
                prompt_index=prompt_index,
            )


def _load_documents(
    json_dir: Path,
    metadata_path: Path | None,
) -> list[tuple[str, Path]]:
    if metadata_path and metadata_path.exists():
        rows: list[tuple[str, Path]] = []
        with metadata_path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                json_filename = row.get("json_filename", "")
                model_id = row.get("model_id", "")
                if not json_filename:
                    continue
                json_path = json_dir / json_filename
                if not json_path.exists():
                    raise FileNotFoundError(f"Missing canonical JSON: {json_path}")
                rows.append((model_id, json_path))
        if rows:
            return rows

    return [
        (path.stem, path)
        for path in sorted(json_dir.glob("*.json"))
    ]


class TrainingFormatExporter(ABC):
    """Base class for training dataset export formats."""

    @abstractmethod
    def format_record(self, example: TrainingExample) -> dict[str, Any]:
        """Convert one training example to a serializable record."""

    def export(
        self,
        examples: list[TrainingExample],
        output_path: Path,
    ) -> int:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            for example in examples:
                record = self.format_record(example)
                handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
                handle.write("\n")
        return len(examples)


class SimpleJsonlExporter(TrainingFormatExporter):
    """Export input -> operations JSONL for supervised fine-tuning."""

    def format_record(self, example: TrainingExample) -> dict[str, Any]:
        return {
            "input": example.input,
            "output": {
                "operations": example.operations,
            },
        }


EXPORTERS: dict[str, type[TrainingFormatExporter]] = {
    "simple": SimpleJsonlExporter,
}


def load_system_prompt(path: Path) -> str:
    """Load the system prompt used for OpenAI fine-tuning exports."""
    if not path.exists():
        raise FileNotFoundError(f"System prompt file not found: {path}")
    content = path.read_text(encoding="utf-8")
    if not content.strip():
        raise ValueError(f"System prompt file is empty: {path}")
    return content


def iter_internal_training_examples(path: Path) -> Iterator[TrainingExample]:
    """Yield training examples from the internal training_data.jsonl format."""
    if not path.exists():
        raise FileNotFoundError(f"Training data file not found: {path}")

    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number} of {path}") from exc

            user_input = record.get("input")
            output = record.get("output", {})
            operations = output.get("operations") if isinstance(output, dict) else None

            if not isinstance(user_input, str) or not user_input.strip():
                raise ValueError(f"Missing or empty input on line {line_number} of {path}")
            if not isinstance(operations, list) or not operations:
                raise ValueError(f"Missing or empty operations on line {line_number} of {path}")

            yield TrainingExample(
                input=user_input.strip(),
                operations=operations,
            )


class OpenAIChatJsonlExporter(TrainingFormatExporter):
    """Export OpenAI supervised fine-tuning chat JSONL."""

    def __init__(self, system_prompt: str) -> None:
        if not system_prompt.strip():
            raise ValueError("System prompt must not be empty.")
        self.system_prompt = system_prompt

    def format_record(self, example: TrainingExample) -> dict[str, Any]:
        assistant_content = json.dumps(
            {"operations": example.operations},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return {
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": example.input},
                {"role": "assistant", "content": assistant_content},
            ],
        }


def export_openai_finetune_data(
    training_data_path: Path,
    output_path: Path,
    *,
    system_prompt_path: Path,
) -> dict[str, int]:
    """Convert internal training_data.jsonl to OpenAI chat fine-tuning JSONL."""
    system_prompt = load_system_prompt(system_prompt_path)
    examples = list(iter_internal_training_examples(training_data_path))
    exporter = OpenAIChatJsonlExporter(system_prompt)
    count = exporter.export(examples, output_path)
    return {"examples": count}


def export_training_data(
    json_dir: Path,
    output_path: Path,
    *,
    metadata_path: Path | None = None,
    format_name: str = "simple",
) -> dict[str, int]:
    """Export training examples from canonical JSON without modifying them."""
    exporter_cls = EXPORTERS.get(format_name)
    if exporter_cls is None:
        supported = ", ".join(sorted(EXPORTERS))
        raise ValueError(f"Unsupported export format '{format_name}'. Supported: {supported}")

    examples = list(iter_training_examples(json_dir, metadata_path=metadata_path))
    exporter = exporter_cls()
    count = exporter.export(examples, output_path)

    unique_models = len({example.model_id for example in examples})
    return {
        "examples": count,
        "models": unique_models,
        "prompts_per_model": count // unique_models if unique_models else 0,
    }
