#!/usr/bin/env python3
"""Generate CAD Copilot Dataset V1 from validated FreeCAD models."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from parser.document_parser import parse_fcstd  # noqa: E402

from dataset_v1.scripts.generate_prompts import generate_prompt_metadata  # noqa: E402
from dataset_v1.scripts.openai_client import OpenAIClient  # noqa: E402
from dataset_v1.scripts.roundtrip_validator import (  # noqa: E402
    RoundTripResult,
    is_fully_parsed,
    validate_roundtrip,
)


@dataclass
class DatasetRecord:
    model_id: str
    source_fcstd: str
    dataset_id: str
    repository: str
    original_relative_path: str
    operation_count: int
    title: str
    tags: str
    roundtrip_passed: bool
    prompt_source: str


def load_index_metadata(examples_dir: Path) -> dict[str, dict[str, str]]:
    index_path = examples_dir / "index.csv"
    metadata: dict[str, dict[str, str]] = {}
    if not index_path.exists():
        return metadata

    with index_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            copied = row.get("copied_filename", "")
            if not copied:
                continue
            if copied not in metadata or row.get("is_canonical", "true") == "true":
                metadata[copied] = {
                    "dataset_id": row.get("id", ""),
                    "repository": row.get("repository_name", ""),
                    "original_relative_path": row.get("original_relative_path", ""),
                    "original_filename": row.get("original_filename", ""),
                }
    return metadata


def discover_fcstd_files(examples_dir: Path) -> list[Path]:
    return sorted(examples_dir.glob("*.FCStd"))


def select_v1_candidates(
    examples_dir: Path,
    *,
    candidate_list: Path | None = None,
) -> list[Path]:
    """Return FCStd paths that are fully parsed according to parser status."""
    if candidate_list and candidate_list.exists():
        names = [
            line.strip()
            for line in candidate_list.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        return [examples_dir / name for name in names if (examples_dir / name).exists()]

    selected: list[Path] = []
    for path in discover_fcstd_files(examples_dir):
        result = parse_fcstd(path)
        if is_fully_parsed(result):
            selected.append(path)
    return selected


def build_model_document(
    model_id: str,
    cad_json: dict,
    prompt_metadata: dict,
) -> dict:
    """Assemble the final dataset JSON document."""
    return {
        "model_id": model_id,
        "title": prompt_metadata["title"],
        "description": prompt_metadata["description"],
        "tags": prompt_metadata["tags"],
        "prompts": prompt_metadata["prompts"],
        "metadata": cad_json["metadata"],
        "operations": cad_json["operations"],
    }


def write_metadata_csv(path: Path, records: list[DatasetRecord]) -> None:
    fields = [
        "model_id",
        "source_fcstd",
        "dataset_id",
        "repository",
        "original_relative_path",
        "operation_count",
        "title",
        "tags",
        "roundtrip_passed",
        "prompt_source",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "model_id": record.model_id,
                    "source_fcstd": record.source_fcstd,
                    "dataset_id": record.dataset_id,
                    "repository": record.repository,
                    "original_relative_path": record.original_relative_path,
                    "operation_count": record.operation_count,
                    "title": record.title,
                    "tags": record.tags,
                    "roundtrip_passed": str(record.roundtrip_passed).lower(),
                    "prompt_source": record.prompt_source,
                }
            )


def write_selection_report(path: Path, results: list[tuple[Path, RoundTripResult]]) -> None:
    """Write round-trip screening results for all fully-parsed candidates."""
    fields = [
        "source_fcstd",
        "parse_status",
        "operation_count",
        "roundtrip_passed",
        "error",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for fcstd_path, result in results:
            writer.writerow(
                {
                    "source_fcstd": fcstd_path.name,
                    "parse_status": result.parse_status,
                    "operation_count": result.operation_count,
                    "roundtrip_passed": str(result.passed).lower(),
                    "error": result.error,
                }
            )


def generate_dataset(
    examples_dir: Path,
    output_dir: Path,
    *,
    skip_prompts: bool = False,
    openai_model: str = "gpt-4o-mini",
    limit: int | None = None,
    progress: bool = True,
) -> None:
    """Build Dataset V1 from fully validated round-trip models."""
    examples_dir = examples_dir.resolve()
    output_dir = output_dir.resolve()
    models_dir = output_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    candidates = select_v1_candidates(examples_dir)
    if limit is not None:
        candidates = candidates[:limit]

    if progress:
        print(f"Found {len(candidates)} fully-parsed candidate models.")

    index_meta = load_index_metadata(examples_dir)
    client = None if skip_prompts else OpenAIClient(model=openai_model)

    records: list[DatasetRecord] = []
    screening: list[tuple[Path, RoundTripResult]] = []
    accepted = 0
    rejected = 0

    for index, fcstd_path in enumerate(candidates, start=1):
        meta = index_meta.get(fcstd_path.name, {})

        if progress:
            print(f"[{index}/{len(candidates)}] Validating {fcstd_path.name}...", flush=True)

        roundtrip: RoundTripResult = validate_roundtrip(fcstd_path)
        screening.append((fcstd_path, roundtrip))

        if not roundtrip.passed:
            rejected += 1
            if progress:
                print(f"  REJECTED: {roundtrip.error[:160]}")
            continue

        result = parse_fcstd(fcstd_path)
        cad_json = result.cad_json

        prompt_source = "fallback"
        if skip_prompts:
            prompt_metadata = generate_prompt_metadata(cad_json, use_openai=False)
        else:
            prompt_metadata = generate_prompt_metadata(cad_json, client=client, use_openai=True)
            prompt_source = "openai"

        accepted += 1
        final_model_id = f"model_{accepted:04d}"
        document = build_model_document(final_model_id, cad_json, prompt_metadata)

        output_path = models_dir / f"{final_model_id}.json"
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(document, handle, indent=2)
            handle.write("\n")

        records.append(
            DatasetRecord(
                model_id=final_model_id,
                source_fcstd=fcstd_path.name,
                dataset_id=meta.get("dataset_id", ""),
                repository=meta.get("repository", ""),
                original_relative_path=meta.get("original_relative_path", ""),
                operation_count=roundtrip.operation_count,
                title=prompt_metadata["title"],
                tags=";".join(prompt_metadata["tags"]),
                roundtrip_passed=True,
                prompt_source=prompt_source,
            )
        )

        if progress:
            print(f"  ACCEPTED -> {output_path.name}")

    write_metadata_csv(output_dir / "metadata.csv", records)
    write_selection_report(output_dir / "selection_report.csv", screening)

    if progress:
        print("----------------------------------------")
        print(f"Fully-parsed candidates : {len(candidates)}")
        print(f"Round-trip accepted     : {accepted}")
        print(f"Round-trip rejected     : {rejected}")
        print(f"Output directory     : {output_dir}")
        print(f"Models written       : {models_dir}")
        print(f"Metadata             : {output_dir / 'metadata.csv'}")
        print("----------------------------------------")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate CAD Copilot Dataset V1.",
    )
    parser.add_argument(
        "--examples",
        type=Path,
        default=PROJECT_ROOT / "examples",
        help="Directory containing extracted .FCStd files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "dataset_v1",
        help="Dataset V1 output directory.",
    )
    parser.add_argument(
        "--skip-prompts",
        action="store_true",
        help="Skip OpenAI prompt generation and use deterministic fallback prompts.",
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
        help="Process only the first N candidate models.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    generate_dataset(
        examples_dir=args.examples,
        output_dir=args.output,
        skip_prompts=args.skip_prompts,
        openai_model=args.openai_model,
        limit=args.limit,
        progress=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
