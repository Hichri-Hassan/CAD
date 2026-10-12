#!/usr/bin/env python3
"""Generate OpenAI natural-language prompts for Dataset V1 training models."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dataset_v1.scripts.generate_prompts import generate_prompt_metadata  # noqa: E402
from dataset_v1.scripts.openai_client import OpenAIClient, OpenAIClientError  # noqa: E402

METADATA_FIELDS = (
    "model_id",
    "original_filename",
    "json_filename",
    "title",
    "prompt_source",
)


def load_train_metadata(train_dir: Path) -> list[dict[str, str]]:
    metadata_path = train_dir / "metadata.csv"
    with metadata_path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def enrich_model_json(json_path: Path, prompt_metadata: dict[str, object]) -> dict:
    document = json.loads(json_path.read_text(encoding="utf-8"))
    document["title"] = prompt_metadata["title"]
    document["description"] = prompt_metadata["description"]
    document["tags"] = prompt_metadata["tags"]
    document["prompts"] = prompt_metadata["prompts"]
    json_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return document


def generate_train_prompts(
    train_dir: Path,
    *,
    openai_model: str = "gpt-4o-mini",
    limit: int | None = None,
    delay_seconds: float = 0.5,
    progress: bool = True,
) -> list[dict[str, str]]:
    """Generate prompts for every model in the train split."""
    train_dir = train_dir.resolve()
    json_dir = train_dir / "json"
    all_rows = load_train_metadata(train_dir)
    rows = all_rows[:limit] if limit is not None else all_rows

    client = OpenAIClient(model=openai_model)
    updated_by_id: dict[str, dict[str, str]] = {
        row["model_id"]: dict(row) for row in all_rows
    }

    for index, row in enumerate(rows, start=1):
        model_id = row["model_id"]
        json_filename = row["json_filename"]
        json_path = json_dir / json_filename

        if progress:
            print(f"[{index}/{len(rows)}] Generating prompts for {model_id}...", flush=True)

        if not json_path.exists():
            raise FileNotFoundError(f"Missing training JSON: {json_path}")

        cad_json = json.loads(json_path.read_text(encoding="utf-8"))
        prompt_metadata = generate_prompt_metadata(cad_json, client=client, use_openai=True)
        document = enrich_model_json(json_path, prompt_metadata)

        updated_by_id[model_id] = {
            "model_id": model_id,
            "original_filename": row["original_filename"],
            "json_filename": json_filename,
            "title": document["title"],
            "prompt_source": "openai",
        }

        if progress:
            print(f"  -> {document['title']}")

        if index < len(rows) and delay_seconds > 0:
            time.sleep(delay_seconds)

    final_rows = [updated_by_id[row["model_id"]] for row in all_rows]
    metadata_path = train_dir / "metadata.csv"
    with metadata_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=METADATA_FIELDS)
        writer.writeheader()
        for row in final_rows:
            writer.writerow(
                {
                    "model_id": row["model_id"],
                    "original_filename": row["original_filename"],
                    "json_filename": row["json_filename"],
                    "title": row.get("title", ""),
                    "prompt_source": row.get("prompt_source", ""),
                }
            )

    return [updated_by_id[row["model_id"]] for row in rows]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate OpenAI prompts for Dataset V1 training models.",
    )
    parser.add_argument(
        "--train-dir",
        type=Path,
        default=PROJECT_ROOT / "dataset_v1" / "train",
        help="Training split directory.",
    )
    parser.add_argument(
        "--openai-model",
        default="gpt-4o-mini",
        help="OpenAI model name (default: gpt-4o-mini).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process only the first N training models.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between API calls in seconds (default: 0.5).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        rows = generate_train_prompts(
            args.train_dir,
            openai_model=args.openai_model,
            limit=args.limit,
            delay_seconds=args.delay,
        )
    except OpenAIClientError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print("----------------------------------------")
    print(f"Prompts generated : {len(rows)}")
    print(f"Updated JSON dir  : {args.train_dir / 'json'}")
    print(f"Updated metadata  : {args.train_dir / 'metadata.csv'}")
    print("----------------------------------------")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
