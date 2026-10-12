"""Load and format CAD Copilot training data for supervised fine-tuning."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import torch
from datasets import Dataset


def load_training_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            record = json.loads(stripped)
            if "input" not in record or "output" not in record:
                raise ValueError(f"Invalid record on line {line_number} of {path}")
            records.append(record)
    if not records:
        raise ValueError(f"No training records found in {path}")
    return records


def split_train_val(
    records: list[dict[str, Any]],
    *,
    seed: int,
    val_ratio: float = 0.1,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rng = random.Random(seed)
    indices = list(range(len(records)))
    rng.shuffle(indices)
    val_size = max(1, int(len(records) * val_ratio))
    val_indices = set(indices[:val_size])
    train_records = [records[i] for i in indices if i not in val_indices]
    val_records = [records[i] for i in indices if i in val_indices]
    return train_records, val_records


def split_train_val_from_manifest(
    records: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    from training.dataset_merge import geometry_group_key, split_records_by_geometry

    geometry_splits = manifest.get("geometry_splits")
    if not isinstance(geometry_splits, dict):
        raise ValueError("Split manifest is missing geometry_splits.")
    return split_records_by_geometry(records, geometry_splits)


def format_assistant_target(output: dict[str, Any]) -> str:
    return json.dumps(output, ensure_ascii=False, separators=(",", ":"))


def build_messages(
    user_input: str,
    assistant_output: dict[str, Any],
    *,
    system_prompt: str | None = None,
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_input})
    messages.append({"role": "assistant", "content": format_assistant_target(assistant_output)})
    return messages


def tokenize_supervised_example(
    example: dict[str, Any],
    tokenizer: Any,
    *,
    system_prompt: str | None,
    max_seq_length: int,
) -> dict[str, Any]:
    messages = build_messages(
        example["input"],
        example["output"],
        system_prompt=system_prompt,
    )

    if not hasattr(tokenizer, "apply_chat_template"):
        raise ValueError("Tokenizer does not support chat templates.")

    prompt_messages = messages[:-1]
    assistant_content = messages[-1]["content"]

    prompt_text = tokenizer.apply_chat_template(
        prompt_messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    full_text = prompt_text + assistant_content + (tokenizer.eos_token or "")

    prompt_tokens = tokenizer(
        prompt_text,
        truncation=True,
        max_length=max_seq_length,
        add_special_tokens=False,
    )
    full_tokens = tokenizer(
        full_text,
        truncation=True,
        max_length=max_seq_length,
        add_special_tokens=False,
    )

    labels = list(full_tokens["input_ids"])
    prompt_length = min(len(prompt_tokens["input_ids"]), len(labels))
    labels[:prompt_length] = [-100] * prompt_length

    return {
        "input_ids": full_tokens["input_ids"],
        "attention_mask": full_tokens["attention_mask"],
        "labels": labels,
    }


def build_hf_dataset(
    records: list[dict[str, Any]],
    tokenizer: Any,
    *,
    system_prompt: str | None,
    max_seq_length: int,
) -> Dataset:
    tokenized = [
        tokenize_supervised_example(
            record,
            tokenizer,
            system_prompt=system_prompt,
            max_seq_length=max_seq_length,
        )
        for record in records
    ]
    return Dataset.from_list(tokenized)


def load_system_prompt(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    content = path.read_text(encoding="utf-8").strip()
    return content or None


class CausalLMSFTCollator:
    """Pad tokenized SFT examples and mask padded label positions."""

    def __init__(self, tokenizer: Any) -> None:
        self.tokenizer = tokenizer

    def __call__(self, features: list[dict[str, Any]]) -> dict[str, torch.Tensor]:
        labels = [feature["labels"] for feature in features]
        batch = self.tokenizer.pad(
            {
                "input_ids": [feature["input_ids"] for feature in features],
                "attention_mask": [feature["attention_mask"] for feature in features],
            },
            padding=True,
            return_tensors="pt",
        )
        max_length = batch["input_ids"].shape[1]
        padded_labels = []
        for label in labels:
            padded = label + [-100] * (max_length - len(label))
            padded_labels.append(padded[:max_length])
        batch["labels"] = torch.tensor(padded_labels, dtype=torch.long)
        return batch
