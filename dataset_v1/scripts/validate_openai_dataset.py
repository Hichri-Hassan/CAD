#!/usr/bin/env python3
"""Validate OpenAI chat fine-tuning JSONL datasets."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dataset_v1.scripts.training_export import iter_internal_training_examples  # noqa: E402

EXPECTED_ROLES = ("system", "user", "assistant")


@dataclass
class ValidationResult:
    valid_count: int = 0
    invalid_count: int = 0
    issues: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.invalid_count == 0 and not self.issues


def validate_openai_dataset(
    dataset_path: Path,
    *,
    expected_count: int | None = None,
) -> ValidationResult:
    """Validate an OpenAI fine-tuning JSONL file."""
    result = ValidationResult()

    if not dataset_path.exists():
        result.invalid_count = 1
        result.issues.append(f"Dataset file not found: {dataset_path}")
        return result

    lines = [line.strip() for line in dataset_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    actual_count = len(lines)

    if expected_count is not None and actual_count != expected_count:
        result.issues.append(
            f"Expected {expected_count} conversations, found {actual_count}."
        )

    for line_number, line in enumerate(lines, start=1):
        prefix = f"Line {line_number}"
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            result.invalid_count += 1
            result.issues.append(f"{prefix}: invalid JSON ({exc.msg}).")
            continue

        messages = record.get("messages")
        if not isinstance(messages, list):
            result.invalid_count += 1
            result.issues.append(f"{prefix}: missing 'messages' list.")
            continue

        if len(messages) != 3:
            result.invalid_count += 1
            result.issues.append(
                f"{prefix}: expected 3 messages, found {len(messages)}."
            )
            continue

        roles = [message.get("role") for message in messages if isinstance(message, dict)]
        if roles != list(EXPECTED_ROLES):
            result.invalid_count += 1
            result.issues.append(
                f"{prefix}: message roles must be {list(EXPECTED_ROLES)}, found {roles}."
            )
            continue

        system_content = messages[0].get("content")
        user_content = messages[1].get("content")
        assistant_content = messages[2].get("content")

        if not isinstance(system_content, str) or not system_content.strip():
            result.invalid_count += 1
            result.issues.append(f"{prefix}: empty system message.")
            continue

        if not isinstance(user_content, str) or not user_content.strip():
            result.invalid_count += 1
            result.issues.append(f"{prefix}: empty user prompt.")
            continue

        if not isinstance(assistant_content, str) or not assistant_content.strip():
            result.invalid_count += 1
            result.issues.append(f"{prefix}: empty assistant message.")
            continue

        if assistant_content.lstrip().startswith("```"):
            result.invalid_count += 1
            result.issues.append(f"{prefix}: assistant output is wrapped in Markdown.")
            continue

        try:
            assistant_json = json.loads(assistant_content)
        except json.JSONDecodeError as exc:
            result.invalid_count += 1
            result.issues.append(f"{prefix}: assistant output is not valid JSON ({exc.msg}).")
            continue

        if not isinstance(assistant_json, dict):
            result.invalid_count += 1
            result.issues.append(f"{prefix}: assistant JSON must be an object.")
            continue

        operations = assistant_json.get("operations")
        if not isinstance(operations, list) or not operations:
            result.invalid_count += 1
            result.issues.append(f"{prefix}: assistant JSON missing non-empty 'operations' field.")
            continue

        extra_keys = set(assistant_json.keys()) - {"operations"}
        if extra_keys:
            result.invalid_count += 1
            result.issues.append(
                f"{prefix}: assistant JSON contains unexpected fields: {sorted(extra_keys)}."
            )
            continue

        result.valid_count += 1

    if expected_count is not None and actual_count == expected_count and result.invalid_count == 0:
        # Count check already added to issues if failed; don't double-count invalid
        pass

    return result


def infer_expected_count(source_training_data: Path | None) -> int | None:
    if source_training_data is None or not source_training_data.exists():
        return None
    return sum(1 for _ in iter_internal_training_examples(source_training_data))


def print_validation_summary(
    result: ValidationResult,
    *,
    dataset_path: Path,
    expected_count: int | None,
) -> None:
    total = result.valid_count + result.invalid_count
    print("OpenAI dataset validation")
    print("-------------------------")
    print(f"File              : {dataset_path}")
    print(f"Conversations     : {total}")
    if expected_count is not None:
        print(f"Expected count    : {expected_count}")
    print(f"Valid             : {result.valid_count}")
    print(f"Invalid           : {result.invalid_count}")

    if result.issues:
        print("\nIssues:")
        for issue in result.issues:
            print(f"  - {issue}")
    elif result.passed:
        print("\nValidation passed.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate OpenAI fine-tuning JSONL datasets.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=PROJECT_ROOT / "dataset_v1" / "train" / "openai_finetune.jsonl",
        help="OpenAI fine-tuning JSONL file to validate.",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=PROJECT_ROOT / "dataset_v1" / "train" / "training_data.jsonl",
        help="Internal training_data.jsonl used to infer expected conversation count.",
    )
    parser.add_argument(
        "--expected",
        type=int,
        default=None,
        help="Expected number of conversations (defaults to source file count).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    expected_count = args.expected
    if expected_count is None:
        expected_count = infer_expected_count(args.source)

    result = validate_openai_dataset(args.dataset, expected_count=expected_count)
    print_validation_summary(result, dataset_path=args.dataset, expected_count=expected_count)
    return 0 if result.passed and (
        expected_count is None or result.valid_count + result.invalid_count == expected_count
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
